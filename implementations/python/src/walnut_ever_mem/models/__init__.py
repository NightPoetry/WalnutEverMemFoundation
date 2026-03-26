"""Core domain models for WalnutEverMem."""

from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role of message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class PointerType(str, Enum):
    """Type of pointer representation."""

    EMBEDDING = "embedding"
    SUMMARY = "summary"


class ChatRecord(BaseModel):
    """A single chat record in the memory stream.

    This is the fundamental unit of storage - a sequential record
    of interactions, stored exactly as they occurred.
    """

    id: int | None = None
    session_id: str = Field(..., description="Session identifier for context isolation")
    role: MessageRole = Field(..., description="Who sent this message")
    content: str = Field(..., description="The message content")
    embedding: np.ndarray | None = Field(
        default=None,
        description="Optional embedding vector for the content",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "arbitrary_types_allowed": True,
    }

    def to_db_dict(self) -> dict[str, Any]:
        """Convert to database insert format."""
        return {
            "session_id": self.session_id,
            "role": self.role.value,
            "content": self.content,
            "embedding": self.embedding.tolist() if self.embedding is not None else None,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "ChatRecord":
        """Create from database row."""
        embedding = row.get("embedding")
        if embedding is not None:
            embedding = np.array(embedding)

        return cls(
            id=row["id"],
            session_id=row["session_id"],
            role=MessageRole(row["role"]),
            content=row["content"],
            embedding=embedding,
            created_at=row["created_at"],
            metadata=row.get("metadata") or {},
        )


class Pointer(BaseModel):
    """A pointer from one record to another.

    Pointers form the emergent tree structure. When retrieval finds
    a target, a pointer is created at the source position pointing
    to the target, enabling O(1) jumps in future retrievals.
    """

    id: int | None = None
    source_id: int = Field(..., description="Record where this pointer lives")
    target_id: int = Field(..., description="Record this pointer points to")
    embedding: np.ndarray = Field(..., description="Embedding for pointer matching")
    pointer_type: PointerType = Field(
        default=PointerType.EMBEDDING,
        description="Type of pointer representation",
    )
    summary: str | None = Field(
        default=None,
        description="Summary text for summary-type pointers",
    )
    relevance_score: float | None = Field(
        default=None,
        description="Relevance score when pointer was created",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = Field(default=0, description="Number of times accessed")
    last_accessed: datetime | None = Field(
        default=None,
        description="Last access timestamp",
    )

    model_config = {
        "arbitrary_types_allowed": True,
    }

    def to_db_dict(self) -> dict[str, Any]:
        """Convert to database insert format."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "embedding": self.embedding.tolist(),
            "pointer_type": self.pointer_type.value,
            "summary": self.summary,
            "relevance_score": self.relevance_score,
            "created_at": self.created_at,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "Pointer":
        """Create from database row."""
        embedding = row.get("embedding")
        if embedding is not None:
            embedding = np.array(embedding)

        return cls(
            id=row["id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            embedding=embedding,
            pointer_type=PointerType(row["pointer_type"]),
            summary=row.get("summary"),
            relevance_score=row.get("relevance_score"),
            created_at=row["created_at"],
            access_count=row.get("access_count", 0),
            last_accessed=row.get("last_accessed"),
        )


class SearchResult(BaseModel):
    """Result of a memory search operation."""

    record: ChatRecord = Field(..., description="The found record")
    score: float = Field(..., description="Relevance score")
    via_pointer: bool = Field(
        default=False,
        description="Whether found via pointer jump",
    )
    pointer_source_id: int | None = Field(
        default=None,
        description="Source record ID if found via pointer",
    )


class RetrievalContext(BaseModel):
    """Context for a retrieval operation.

    This represents the workspace memory that guides the search.
    The content and embedding are used for pairwise comparison
    with stored records.
    """

    query: str = Field(..., description="The original query")
    embedding: np.ndarray = Field(..., description="Query embedding for comparison")
    session_id: str = Field(..., description="Session to search within")
    max_results: int = Field(default=10, description="Maximum results to return")
    min_similarity: float = Field(
        default=0.7,
        description="Minimum similarity threshold",
    )

    model_config = {
        "arbitrary_types_allowed": True,
    }
