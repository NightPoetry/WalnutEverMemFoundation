import { WalnutConfig, EmbeddingProvider, ChatRecord, Pointer, SearchResult, RetrievalResult, PointerType } from '../models';
import { MemoryRepository } from '../repository';

export function cosineSimilarity(a: number[], b: number[]): number {
  if (a.length !== b.length) return 0;
  
  let dotProduct = 0;
  let normA = 0;
  let normB = 0;
  
  for (let i = 0; i < a.length; i++) {
    dotProduct += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  
  if (normA === 0 || normB === 0) return 0;
  return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}

export class RetrievalService {
  constructor(
    private repo: MemoryRepository,
    private config: WalnutConfig,
    private embeddingProvider?: EmbeddingProvider
  ) {}

  async retrieve(
    query: string,
    sessionId: string,
    queryEmbedding?: number[],
    maxResults: number = 10,
    minSimilarity?: number
  ): Promise<RetrievalResult> {
    let embedding = queryEmbedding;
    
    if (!embedding && this.embeddingProvider) {
      embedding = await this.embeddingProvider.embed(query);
    }
    
    if (!embedding) {
      throw new Error('Either queryEmbedding or embeddingProvider must be provided');
    }
    
    const threshold = minSimilarity ?? this.config.retrieval.similarityThreshold;
    
    return this.executeRetrieval(query, embedding, sessionId, maxResults, threshold);
  }

  private async executeRetrieval(
    query: string,
    queryEmbedding: number[],
    sessionId: string,
    maxResults: number,
    minSimilarity: number
  ): Promise<RetrievalResult> {
    const results: SearchResult[] = [];
    let recordsScanned = 0;
    let pointerJumps = 0;
    let pointersCreated = 0;

    const startingRecord = await this.repo.records.getLatest(sessionId);
    if (!startingRecord) {
      return { results: [], pointersCreated, recordsScanned, pointerJumps };
    }

    let currentId: number | undefined = startingRecord.id;
    const visitedIds = new Set<number>();

    console.log(
      `[MemoryScan] Starting scan for session ${sessionId}, ` +
      `query: '${query.substring(0, 50)}...' (embedding dim: ${queryEmbedding.length})`
    );

    while (currentId !== undefined && results.length < maxResults) {
      if (visitedIds.has(currentId)) {
        console.warn(`[MemoryScan] Cycle detected at record ${currentId}, stopping`);
        break;
      }
      visitedIds.add(currentId);

      const currentRecord = await this.repo.records.getById(currentId);
      if (!currentRecord) break;

      recordsScanned++;

      // Pairwise similarity comparison: query ↔ record
      const similarity = this.computeSimilarity(queryEmbedding, currentRecord);
      
      if (similarity >= minSimilarity) {
        console.debug(
          `[MemoryScan] Match found at record ${currentId}: ` +
          `similarity=${similarity.toFixed(3)} (threshold: ${minSimilarity})`
        );
        results.push({
          record: currentRecord,
          score: similarity,
          viaPointer: false,
        });

        // Create pointer for future fast jumps (memoization)
        if (startingRecord.id !== currentRecord.id) {
          const pointer = await this.createPointer(
            startingRecord.id!,
            currentRecord.id!,
            queryEmbedding,
            similarity
          );
          if (pointer) {
            pointersCreated++;
            console.log(
              `[MemoryScan] Created pointer: ${startingRecord.id} -> ${currentRecord.id} ` +
              `(relevance: ${similarity.toFixed(3)})`
            );
          }
        }
      }

      // Check existing pointers at current position (O(1) jumps)
      const pointers = await this.repo.pointers.getPointersAtSource(currentId);
      for (const pointer of pointers) {
        const pointerSimilarity = cosineSimilarity(queryEmbedding, pointer.embedding);
        
        if (pointerSimilarity >= minSimilarity) {
          const targetRecord = await this.repo.records.getById(pointer.targetId);
          if (targetRecord && !visitedIds.has(targetRecord.id!)) {
            console.debug(
              `[MemoryScan] Pointer jump: ${currentId} -> ${pointer.targetId} ` +
              `(similarity: ${pointerSimilarity.toFixed(3)})`
            );
            results.push({
              record: targetRecord,
              score: pointerSimilarity,
              viaPointer: true,
              pointerSourceId: currentId,
            });
            pointerJumps++;
            
            await this.repo.pointers.incrementAccessCount(pointer.id!);
          }
        }
      }

      // Move to previous record (sequential scan)
      const prevRecords = await this.repo.records.getBySession(sessionId, 1, currentId);
      currentId = prevRecords[0]?.id;
    }

    results.sort((a, b) => b.score - a.score);
    const topResults = results.slice(0, maxResults);

    console.log(
      `[MemoryScan] Complete: scanned=${recordsScanned}, found=${topResults.length}, ` +
      `pointer_jumps=${pointerJumps}, pointers_created=${pointersCreated}`
    );

    return { results: topResults, pointersCreated, recordsScanned, pointerJumps };
  }

  private computeSimilarity(queryEmbedding: number[], record: ChatRecord): number {
    if (record.embedding) {
      return cosineSimilarity(queryEmbedding, record.embedding);
    }
    return 0;
  }

  private async createPointer(
    sourceId: number,
    targetId: number,
    queryEmbedding: number[],
    relevanceScore: number
  ): Promise<Pointer | null> {
    const pointer: Pointer = {
      sourceId,
      targetId,
      embedding: queryEmbedding,
      pointerType: PointerType.EMBEDDING,
      relevanceScore,
      createdAt: new Date(),
      accessCount: 0,
    };

    return this.repo.pointers.create(pointer);
  }
}

export class MemoryService {
  private retrieval: RetrievalService;

  constructor(
    private repo: MemoryRepository,
    private config: WalnutConfig,
    embeddingProvider?: EmbeddingProvider
  ) {
    this.retrieval = new RetrievalService(repo, config, embeddingProvider);
  }

  async remember(
    sessionId: string,
    role: string,
    content: string,
    metadata?: Record<string, unknown>
  ): Promise<ChatRecord> {
    let embedding: number[] | undefined;
    
    if (this['embeddingProvider']) {
      embedding = await this['embeddingProvider'].embed(content);
    }

    return this.repo.appendRecord(sessionId, role, content, embedding, metadata);
  }

  async recall(
    query: string,
    sessionId: string,
    maxResults: number = 10
  ): Promise<SearchResult[]> {
    const result = await this.retrieval.retrieve(query, sessionId, undefined, maxResults);
    return result.results;
  }

  async getContext(sessionId: string, limit: number = 50): Promise<ChatRecord[]> {
    return this.repo.getSessionContext(sessionId, undefined, limit);
  }
}
