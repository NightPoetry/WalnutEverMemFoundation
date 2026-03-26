"""Repository layer for database operations - supports SQLite and PostgreSQL."""

import json
import sqlite3
from datetime import datetime
from typing import Any, Protocol

import numpy as np

from walnut_ever_mem.config import WalnutConfig
from walnut_ever_mem.models import ChatRecord, MessageRole, Pointer, PointerType


class Connection(Protocol):
    """Protocol for database connections."""

    async def execute(self, query: str, *args) -> Any:
        ...

    async def fetch(self, query: str, *args) -> list:
        ...

    async def fetchrow(self, query: str, *args) -> Any:
        ...

    async def fetchval(self, query: str, *args) -> Any:
        ...


def _embedding_to_blob(embedding: np.ndarray) -> bytes:
    """Convert numpy array to blob for SQLite storage."""
    return embedding.astype(np.float32).tobytes()


def _blob_to_embedding(blob: bytes) -> np.ndarray:
    """Convert blob to numpy array from SQLite storage."""
    return np.frombuffer(blob, dtype=np.float32)


def _embedding_to_list(embedding: np.ndarray) -> list:
    """Convert numpy array to list for PostgreSQL."""
    return embedding.tolist()


def _list_to_embedding(lst: list) -> np.ndarray:
    """Convert list to numpy array from PostgreSQL."""
    return np.array(lst, dtype=np.float32)


class ChatRecordRepository:
    """Repository for chat record operations."""

    def __init__(self, conn: Any, backend: str = "sqlite"):
        self.conn = conn
        self.backend = backend

    async def create(self, record: ChatRecord) -> ChatRecord:
        """Insert a new chat record and return with ID."""
        if self.backend == "sqlite":
            return await self._create_sqlite(record)
        return await self._create_postgresql(record)

    async def _create_sqlite(self, record: ChatRecord) -> ChatRecord:
        """Create record in SQLite."""
        embedding_blob = _embedding_to_blob(record.embedding) if record.embedding is not None else None
        metadata_json = json.dumps(record.metadata) if record.metadata else None

        cursor = await self.conn.execute(
            """
            INSERT INTO chat_records (session_id, role, content, embedding, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record.session_id,
                record.role.value,
                record.content,
                embedding_blob,
                record.created_at.isoformat(),
                metadata_json,
            ),
        )
        record_id = cursor.lastrowid
        record.id = record_id
        return record

    async def _create_postgresql(self, record: ChatRecord) -> ChatRecord:
        """Create record in PostgreSQL."""
        row = await self.conn.fetchrow(
            """
            INSERT INTO chat_records (session_id, role, content, embedding, created_at, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            record.session_id,
            record.role.value,
            record.content,
            _embedding_to_list(record.embedding) if record.embedding is not None else None,
            record.created_at,
            record.metadata,
        )
        return ChatRecord.from_db_row(dict(row))

    async def get_by_id(self, record_id: int) -> ChatRecord | None:
        """Get a record by ID."""
        if self.backend == "sqlite":
            return await self._get_by_id_sqlite(record_id)
        return await self._get_by_id_postgresql(record_id)

    async def _get_by_id_sqlite(self, record_id: int) -> ChatRecord | None:
        """Get record by ID from SQLite."""
        cursor = await self.conn.execute(
            "SELECT * FROM chat_records WHERE id = ?",
            (record_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_record_sqlite(row)

    async def _get_by_id_postgresql(self, record_id: int) -> ChatRecord | None:
        """Get record by ID from PostgreSQL."""
        row = await self.conn.fetchrow(
            "SELECT * FROM chat_records WHERE id = $1",
            record_id,
        )
        return ChatRecord.from_db_row(dict(row)) if row else None

    def _row_to_record_sqlite(self, row: tuple) -> ChatRecord:
        """Convert SQLite row to ChatRecord."""
        embedding = _blob_to_embedding(row[4]) if row[4] else None
        metadata = json.loads(row[6]) if row[6] else {}

        return ChatRecord(
            id=row[0],
            session_id=row[1],
            role=MessageRole(row[2]),
            content=row[3],
            embedding=embedding,
            created_at=datetime.fromisoformat(row[5]) if isinstance(row[5], str) else row[5],
            metadata=metadata,
        )

    async def get_by_session(
        self,
        session_id: str,
        limit: int = 100,
        before_id: int | None = None,
    ) -> list[ChatRecord]:
        """Get records for a session, ordered by creation time (newest first)."""
        if self.backend == "sqlite":
            return await self._get_by_session_sqlite(session_id, limit, before_id)
        return await self._get_by_session_postgresql(session_id, limit, before_id)

    async def _get_by_session_sqlite(
        self,
        session_id: str,
        limit: int,
        before_id: int | None,
    ) -> list[ChatRecord]:
        """Get session records from SQLite."""
        if before_id is not None:
            cursor = await self.conn.execute(
                """
                SELECT * FROM chat_records
                WHERE session_id = ? AND id < ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, before_id, limit),
            )
        else:
            cursor = await self.conn.execute(
                """
                SELECT * FROM chat_records
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, limit),
            )
        rows = await cursor.fetchall()
        return [self._row_to_record_sqlite(row) for row in rows]

    async def _get_by_session_postgresql(
        self,
        session_id: str,
        limit: int,
        before_id: int | None,
    ) -> list[ChatRecord]:
        """Get session records from PostgreSQL."""
        if before_id is not None:
            rows = await self.conn.fetch(
                """
                SELECT * FROM chat_records
                WHERE session_id = $1 AND id < $2
                ORDER BY created_at DESC
                LIMIT $3
                """,
                session_id,
                before_id,
                limit,
            )
        else:
            rows = await self.conn.fetch(
                """
                SELECT * FROM chat_records
                WHERE session_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                session_id,
                limit,
            )
        return [ChatRecord.from_db_row(dict(row)) for row in rows]

    async def get_latest(self, session_id: str) -> ChatRecord | None:
        """Get the most recent record for a session."""
        records = await self.get_by_session(session_id, limit=1)
        return records[0] if records else None

    async def count(self, session_id: str) -> int:
        """Count records in a session."""
        if self.backend == "sqlite":
            cursor = await self.conn.execute(
                "SELECT COUNT(*) FROM chat_records WHERE session_id = ?",
                (session_id,),
            )
            return (await cursor.fetchone())[0]
        return await self.conn.fetchval(
            "SELECT COUNT(*) FROM chat_records WHERE session_id = $1",
            session_id,
        )


class PointerRepository:
    """Repository for pointer operations."""

    def __init__(self, conn: Any, backend: str = "sqlite"):
        self.conn = conn
        self.backend = backend

    async def create(self, pointer: Pointer) -> Pointer:
        """Create a new pointer."""
        if self.backend == "sqlite":
            return await self._create_sqlite(pointer)
        return await self._create_postgresql(pointer)

    async def _create_sqlite(self, pointer: Pointer) -> Pointer:
        """Create pointer in SQLite."""
        embedding_blob = _embedding_to_blob(pointer.embedding)

        cursor = await self.conn.execute(
            """
            INSERT INTO pointers (
                source_id, target_id, embedding, pointer_type,
                summary, relevance_score, created_at, access_count, last_accessed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pointer.source_id,
                pointer.target_id,
                embedding_blob,
                pointer.pointer_type.value,
                pointer.summary,
                pointer.relevance_score,
                pointer.created_at.isoformat(),
                pointer.access_count,
                pointer.last_accessed.isoformat() if pointer.last_accessed else None,
            ),
        )
        pointer.id = cursor.lastrowid
        return pointer

    async def _create_postgresql(self, pointer: Pointer) -> Pointer:
        """Create pointer in PostgreSQL."""
        row = await self.conn.fetchrow(
            """
            INSERT INTO pointers (
                source_id, target_id, embedding, pointer_type,
                summary, relevance_score, created_at, access_count, last_accessed
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
            """,
            pointer.source_id,
            pointer.target_id,
            _embedding_to_list(pointer.embedding),
            pointer.pointer_type.value,
            pointer.summary,
            pointer.relevance_score,
            pointer.created_at,
            pointer.access_count,
            pointer.last_accessed,
        )
        return Pointer.from_db_row(dict(row))

    async def get_pointers_at_source(self, source_id: int) -> list[Pointer]:
        """Get all pointers stored at a source record."""
        if self.backend == "sqlite":
            return await self._get_pointers_at_source_sqlite(source_id)
        return await self._get_pointers_at_source_postgresql(source_id)

    async def _get_pointers_at_source_sqlite(self, source_id: int) -> list[Pointer]:
        """Get pointers at source from SQLite."""
        cursor = await self.conn.execute(
            "SELECT * FROM pointers WHERE source_id = ?",
            (source_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_pointer_sqlite(row) for row in rows]

    async def _get_pointers_at_source_postgresql(self, source_id: int) -> list[Pointer]:
        """Get pointers at source from PostgreSQL."""
        rows = await self.conn.fetch(
            "SELECT * FROM pointers WHERE source_id = $1",
            source_id,
        )
        return [Pointer.from_db_row(dict(row)) for row in rows]

    def _row_to_pointer_sqlite(self, row: tuple) -> Pointer:
        """Convert SQLite row to Pointer."""
        embedding = _blob_to_embedding(row[3])
        last_accessed = datetime.fromisoformat(row[9]) if row[9] else None

        return Pointer(
            id=row[0],
            source_id=row[1],
            target_id=row[2],
            embedding=embedding,
            pointer_type=PointerType(row[4]),
            summary=row[5],
            relevance_score=row[6],
            created_at=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7],
            access_count=row[8] or 0,
            last_accessed=last_accessed,
        )

    async def increment_access_count(self, pointer_id: int) -> None:
        """Increment access count and update last_accessed."""
        now = datetime.utcnow()
        if self.backend == "sqlite":
            await self.conn.execute(
                """
                UPDATE pointers
                SET access_count = access_count + 1,
                    last_accessed = ?
                WHERE id = ?
                """,
                (now.isoformat(), pointer_id),
            )
        else:
            await self.conn.execute(
                """
                UPDATE pointers
                SET access_count = access_count + 1,
                    last_accessed = $1
                WHERE id = $2
                """,
                now,
                pointer_id,
            )

    async def count_at_source(self, source_id: int) -> int:
        """Count pointers at a source."""
        if self.backend == "sqlite":
            cursor = await self.conn.execute(
                "SELECT COUNT(*) FROM pointers WHERE source_id = ?",
                (source_id,),
            )
            return (await cursor.fetchone())[0]
        return await self.conn.fetchval(
            "SELECT COUNT(*) FROM pointers WHERE source_id = $1",
            source_id,
        )


class MemoryRepository:
    """Combined repository for memory operations."""

    def __init__(self, conn: Any, config: WalnutConfig):
        self.conn = conn
        self.config = config
        self.backend = config.db.backend
        self.records = ChatRecordRepository(conn, self.backend)
        self.pointers = PointerRepository(conn, self.backend)

    async def append_record(
        self,
        session_id: str,
        role: str,
        content: str,
        embedding: np.ndarray | None = None,
        metadata: dict | None = None,
    ) -> ChatRecord:
        """Append a new record to a session's memory stream."""
        record = ChatRecord(
            session_id=session_id,
            role=MessageRole(role),
            content=content,
            embedding=embedding,
            metadata=metadata or {},
        )
        return await self.records.create(record)

    async def get_session_context(
        self,
        session_id: str,
        before_id: int | None = None,
        limit: int = 50,
    ) -> list[ChatRecord]:
        """Get context records for a session."""
        return await self.records.get_by_session(
            session_id,
            limit=limit,
            before_id=before_id,
        )
