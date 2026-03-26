export enum MessageRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system',
}

export enum PointerType {
  EMBEDDING = 'embedding',
  SUMMARY = 'summary',
}

export interface ChatRecord {
  id?: number;
  sessionId: string;
  role: MessageRole;
  content: string;
  embedding?: number[];
  createdAt: Date;
  metadata: Record<string, unknown>;
}

export interface Pointer {
  id?: number;
  sourceId: number;
  targetId: number;
  embedding: number[];
  pointerType: PointerType;
  summary?: string;
  relevanceScore?: number;
  createdAt: Date;
  accessCount: number;
  lastAccessed?: Date;
}

export interface SearchResult {
  record: ChatRecord;
  score: number;
  viaPointer: boolean;
  pointerSourceId?: number;
}

export interface RetrievalContext {
  query: string;
  embedding: number[];
  sessionId: string;
  maxResults: number;
  minSimilarity: number;
}

export interface RetrievalResult {
  results: SearchResult[];
  pointersCreated: number;
  recordsScanned: number;
  pointerJumps: number;
}

export interface EmbeddingProvider {
  embed(text: string): Promise<number[]>;
  readonly dimension: number;
}

export function createChatRecord(data: {
  sessionId: string;
  role: MessageRole | string;
  content: string;
  embedding?: number[];
  metadata?: Record<string, unknown>;
}): ChatRecord {
  return {
    sessionId: data.sessionId,
    role: typeof data.role === 'string' ? data.role as MessageRole : data.role,
    content: data.content,
    embedding: data.embedding,
    createdAt: new Date(),
    metadata: data.metadata ?? {},
  };
}

export function createPointer(data: {
  sourceId: number;
  targetId: number;
  embedding: number[];
  pointerType?: PointerType;
  summary?: string;
  relevanceScore?: number;
}): Pointer {
  return {
    sourceId: data.sourceId,
    targetId: data.targetId,
    embedding: data.embedding,
    pointerType: data.pointerType ?? PointerType.EMBEDDING,
    summary: data.summary,
    relevanceScore: data.relevanceScore,
    createdAt: new Date(),
    accessCount: 0,
  };
}
