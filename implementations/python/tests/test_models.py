"""Tests for core models."""

import numpy as np
import pytest

from walnut_ever_mem.models import (
    ChatRecord,
    MessageRole,
    Pointer,
    PointerType,
    RetrievalContext,
    SearchResult,
)


def test_chat_record_creation():
    """Test ChatRecord model creation."""
    record = ChatRecord(
        session_id="test-session",
        role=MessageRole.USER,
        content="Hello, world!",
    )
    assert record.session_id == "test-session"
    assert record.role == MessageRole.USER
    assert record.content == "Hello, world!"
    assert record.embedding is None


def test_chat_record_with_embedding():
    """Test ChatRecord with embedding."""
    embedding = np.random.rand(1536).astype(np.float32)
    record = ChatRecord(
        session_id="test-session",
        role=MessageRole.ASSISTANT,
        content="Response",
        embedding=embedding,
    )
    assert record.embedding is not None
    assert record.embedding.shape == (1536,)


def test_chat_record_to_db_dict():
    """Test conversion to database format."""
    embedding = np.array([0.1, 0.2, 0.3])
    record = ChatRecord(
        id=1,
        session_id="test",
        role=MessageRole.USER,
        content="Test",
        embedding=embedding,
        metadata={"key": "value"},
    )
    db_dict = record.to_db_dict()
    assert db_dict["session_id"] == "test"
    assert db_dict["role"] == "user"
    assert db_dict["embedding"] == [0.1, 0.2, 0.3]
    assert db_dict["metadata"] == {"key": "value"}


def test_chat_record_from_db_row():
    """Test creation from database row."""
    row = {
        "id": 1,
        "session_id": "test",
        "role": "assistant",
        "content": "Response",
        "embedding": [0.1, 0.2, 0.3],
        "created_at": "2024-01-01T00:00:00",
        "metadata": {"foo": "bar"},
    }
    record = ChatRecord.from_db_row(row)
    assert record.id == 1
    assert record.role == MessageRole.ASSISTANT
    assert record.embedding is not None
    assert np.allclose(record.embedding, [0.1, 0.2, 0.3])


def test_pointer_creation():
    """Test Pointer model creation."""
    embedding = np.random.rand(1536).astype(np.float32)
    pointer = Pointer(
        source_id=1,
        target_id=5,
        embedding=embedding,
    )
    assert pointer.source_id == 1
    assert pointer.target_id == 5
    assert pointer.pointer_type == PointerType.EMBEDDING
    assert pointer.access_count == 0


def test_pointer_to_db_dict():
    """Test Pointer conversion to database format."""
    embedding = np.array([0.1, 0.2, 0.3])
    pointer = Pointer(
        id=1,
        source_id=1,
        target_id=2,
        embedding=embedding,
        relevance_score=0.85,
    )
    db_dict = pointer.to_db_dict()
    assert db_dict["source_id"] == 1
    assert db_dict["target_id"] == 2
    assert db_dict["embedding"] == [0.1, 0.2, 0.3]
    assert db_dict["relevance_score"] == 0.85


def test_retrieval_context():
    """Test RetrievalContext model."""
    embedding = np.random.rand(1536).astype(np.float32)
    context = RetrievalContext(
        query="test query",
        embedding=embedding,
        session_id="test-session",
    )
    assert context.query == "test query"
    assert context.max_results == 10
    assert context.min_similarity == 0.7


def test_search_result():
    """Test SearchResult model."""
    record = ChatRecord(
        session_id="test",
        role=MessageRole.USER,
        content="Test content",
    )
    result = SearchResult(
        record=record,
        score=0.85,
        via_pointer=True,
        pointer_source_id=10,
    )
    assert result.record == record
    assert result.score == 0.85
    assert result.via_pointer is True
    assert result.pointer_source_id == 10
