"""Retrieval service - the core of the memory system."""

import logging
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from walnut_ever_mem.config import WalnutConfig
from walnut_ever_mem.models import ChatRecord, Pointer, RetrievalContext, SearchResult
from walnut_ever_mem.repository import MemoryRepository

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    async def embed(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        ...

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        ...


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""

    results: list[SearchResult]
    pointers_created: int = 0
    records_scanned: int = 0
    pointer_jumps: int = 0


class RetrievalService:
    """Core retrieval service implementing the memoization-based search.

    The retrieval algorithm:
    1. Start from the most recent record
    2. At each node:
       a. Check the record content against query
       b. Check all pointers at this node
       c. If pointer matches, jump to target
       d. Continue backward sequentially
    3. When a target is found, create a pointer at the starting position

    This implements memoization: successful retrievals create shortcuts
    for future queries, forming an emergent tree structure.
    """

    def __init__(
        self,
        repo: MemoryRepository,
        config: WalnutConfig,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.repo = repo
        self.config = config
        self.embedding_provider = embedding_provider

    async def retrieve(
        self,
        query: str,
        session_id: str,
        query_embedding: np.ndarray | None = None,
        max_results: int = 10,
        min_similarity: float | None = None,
    ) -> RetrievalResult:
        """Retrieve relevant memories for a query.

        Args:
            query: The search query text
            session_id: Session to search within
            query_embedding: Pre-computed query embedding (optional)
            max_results: Maximum results to return
            min_similarity: Minimum similarity threshold

        Returns:
            RetrievalResult with found records and statistics
        """
        if query_embedding is None and self.embedding_provider is not None:
            query_embedding = await self.embedding_provider.embed(query)

        if query_embedding is None:
            raise ValueError("Either query_embedding or embedding_provider must be provided")

        min_sim = min_similarity or self.config.retrieval.similarity_threshold

        context = RetrievalContext(
            query=query,
            embedding=query_embedding,
            session_id=session_id,
            max_results=max_results,
            min_similarity=min_sim,
        )

        return await self._execute_retrieval(context)

    async def _execute_retrieval(self, context: RetrievalContext) -> RetrievalResult:
        """Execute the retrieval algorithm.
        
        This implements the memory scanning algorithm with:
        1. Pairwise similarity comparison (query vs each record)
        2. Pointer creation for future fast jumps
        3. On-demand retrieval (no pre-computed indexes)
        """
        results: list[SearchResult] = []
        records_scanned = 0
        pointer_jumps = 0
        pointers_created = 0

        starting_record = await self.repo.records.get_latest(context.session_id)
        if starting_record is None:
            return RetrievalResult(results=results)

        current_id = starting_record.id
        visited_ids: set[int] = set()

        logger.info(
            f"Starting memory scan for session {context.session_id}, "
            f"query: '{context.query[:50]}...' (embedding dim: {len(context.embedding)})"
        )

        while current_id is not None and len(results) < context.max_results:
            if current_id in visited_ids:
                logger.warning(f"Cycle detected at record {current_id}, stopping")
                break
            visited_ids.add(current_id)

            current_record = await self.repo.records.get_by_id(current_id)
            if current_record is None:
                break

            records_scanned += 1

            # Pairwise similarity comparison: query ↔ record
            similarity = self._compute_similarity(context, current_record)
            
            if similarity >= context.min_similarity:
                logger.debug(
                    f"Match found at record {current_id}: similarity={similarity:.3f} "
                    f"(threshold: {context.min_similarity})"
                )
                results.append(SearchResult(
                    record=current_record,
                    score=similarity,
                    via_pointer=False,
                ))

                # Create pointer for future fast jumps (memoization)
                if starting_record.id != current_record.id:
                    pointer = await self._create_pointer(
                        source_id=starting_record.id,
                        target_id=current_record.id,
                        query_embedding=context.embedding,
                        relevance_score=similarity,
                    )
                    if pointer:
                        pointers_created += 1
                        logger.info(
                            f"Created pointer {pointer.id}: {starting_record.id} -> {current_record.id} "
                            f"(relevance: {similarity:.3f})"
                        )

            # Check existing pointers at current position (O(1) jumps)
            pointers = await self.repo.pointers.get_pointers_at_source(current_id)

            for pointer in pointers:
                pointer_similarity = cosine_similarity(context.embedding, pointer.embedding)

                if pointer_similarity >= context.min_similarity:
                    target_record = await self.repo.records.get_by_id(pointer.target_id)
                    if target_record and target_record.id not in visited_ids:
                        logger.debug(
                            f"Pointer jump: {current_id} -> {pointer.target_id} "
                            f"(similarity: {pointer_similarity:.3f})"
                        )
                        results.append(SearchResult(
                            record=target_record,
                            score=pointer_similarity,
                            via_pointer=True,
                            pointer_source_id=current_id,
                        ))
                        pointer_jumps += 1

                        await self.repo.pointers.increment_access_count(pointer.id)

            # Move to previous record (sequential scan)
            prev_records = await self.repo.records.get_by_session(
                context.session_id,
                limit=1,
                before_id=current_id,
            )
            current_id = prev_records[0].id if prev_records else None

        results.sort(key=lambda r: r.score, reverse=True)
        results = results[:context.max_results]

        logger.info(
            f"Memory scan complete: scanned={records_scanned}, "
            f"found={len(results)}, pointer_jumps={pointer_jumps}, "
            f"pointers_created={pointers_created}"
        )

        return RetrievalResult(
            results=results,
            pointers_created=pointers_created,
            records_scanned=records_scanned,
            pointer_jumps=pointer_jumps,
        )

    def _compute_similarity(
        self,
        context: RetrievalContext,
        record: ChatRecord,
    ) -> float:
        """Compute similarity between query and record."""
        if record.embedding is not None:
            return cosine_similarity(context.embedding, record.embedding)

        return 0.0

    async def _create_pointer(
        self,
        source_id: int,
        target_id: int,
        query_embedding: np.ndarray,
        relevance_score: float,
    ) -> Pointer | None:
        """Create a pointer from source to target."""
        existing = await self.repo.pointers.find_similar_pointers(
            source_id=source_id,
            query_embedding=query_embedding,
            threshold=0.95,
            limit=1,
        )

        if existing:
            return None

        pointer = Pointer(
            source_id=source_id,
            target_id=target_id,
            embedding=query_embedding,
            relevance_score=relevance_score,
        )

        return await self.repo.pointers.create(pointer)

    async def retrieve_with_content_similarity(
        self,
        context: RetrievalContext,
        record: ChatRecord,
    ) -> float:
        """Compute content-based similarity when embeddings are unavailable.

        This is a fallback for records without embeddings.
        Could be enhanced with BM25 or other text similarity measures.
        """
        query_words = set(context.query.lower().split())
        content_words = set(record.content.lower().split())

        if not query_words or not content_words:
            return 0.0

        intersection = query_words & content_words
        union = query_words | content_words

        return len(intersection) / len(union) if union else 0.0


class MemoryService:
    """High-level memory service combining storage and retrieval."""

    def __init__(
        self,
        repo: MemoryRepository,
        config: WalnutConfig,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.repo = repo
        self.config = config
        self.retrieval = RetrievalService(repo, config, embedding_provider)
        self._embedding_provider = embedding_provider

    async def remember(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> ChatRecord:
        """Store a new memory.

        Args:
            session_id: Session identifier
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata

        Returns:
            The created ChatRecord
        """
        embedding = None
        if self._embedding_provider:
            embedding = await self._embedding_provider.embed(content)

        return await self.repo.append_record(
            session_id=session_id,
            role=role,
            content=content,
            embedding=embedding,
            metadata=metadata,
        )

    async def recall(
        self,
        query: str,
        session_id: str,
        max_results: int = 10,
    ) -> list[SearchResult]:
        """Recall relevant memories.

        Args:
            query: Search query
            session_id: Session to search
            max_results: Maximum results

        Returns:
            List of SearchResult objects
        """
        result = await self.retrieval.retrieve(
            query=query,
            session_id=session_id,
            max_results=max_results,
        )
        return result.results

    async def get_context(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[ChatRecord]:
        """Get recent context for a session.

        Args:
            session_id: Session identifier
            limit: Maximum records to return

        Returns:
            List of ChatRecords in reverse chronological order
        """
        return await self.repo.get_session_context(session_id, limit=limit)
