"""Web API for WalnutEverMem using FastAPI."""

import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from walnut_ever_mem.config import DatabaseConfig, EmbeddingConfig, WalnutConfig
from walnut_ever_mem.database import DatabaseInitializer
from walnut_ever_mem.models import ChatRecord, MessageRole, Pointer, SearchResult
from walnut_ever_mem.repository import MemoryRepository
from walnut_ever_mem.services import MemoryService, RetrievalService


class ConfigRequest(BaseModel):
    """Request body for configuration."""

    db_backend: str = Field(default="sqlite", description="Database backend: sqlite or postgresql")
    sqlite_path: str = Field(default="walnut_memory.db", description="SQLite database path")
    db_host: str = Field(default="localhost", description="PostgreSQL host")
    db_port: int = Field(default=5432, description="PostgreSQL port")
    db_database: str = Field(default="walnut_memory", description="PostgreSQL database name")
    db_user: str = Field(default="postgres", description="PostgreSQL user")
    db_password: str = Field(default="", description="PostgreSQL password")
    embedding_dimension: int = Field(default=1536, description="Embedding vector dimension")
    embedding_provider: str = Field(default="openai", description="Embedding provider")
    embedding_model_name: str = Field(default="text-embedding-3-small", description="Model name")
    embedding_api_key: str | None = Field(default=None, description="API key")
    similarity_threshold: float = Field(default=0.7, description="Similarity threshold")


class InitRequest(BaseModel):
    """Request body for database initialization."""

    config: ConfigRequest = Field(default_factory=ConfigRequest)
    drop_existing: bool = Field(default=False, description="Drop existing tables")


class RememberRequest(BaseModel):
    """Request body for storing a memory."""

    session_id: str = Field(..., description="Session identifier")
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    embedding: list[float] | None = Field(default=None, description="Optional pre-computed embedding")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata")


class RecallRequest(BaseModel):
    """Request body for recalling memories."""

    session_id: str = Field(..., description="Session identifier")
    query: str = Field(..., description="Search query")
    query_embedding: list[float] | None = Field(default=None, description="Pre-computed query embedding")
    max_results: int = Field(default=10, description="Maximum results to return")
    min_similarity: float | None = Field(default=None, description="Minimum similarity threshold")


class ChatRecordResponse(BaseModel):
    """Response model for chat record."""

    id: int
    session_id: str
    role: str
    content: str
    embedding: list[float] | None = None
    created_at: str
    metadata: dict[str, Any]


class SearchResultResponse(BaseModel):
    """Response model for search result."""

    record: ChatRecordResponse
    score: float
    via_pointer: bool
    pointer_source_id: int | None = None


class ConfigResponse(BaseModel):
    """Response model for configuration."""

    db_backend: str
    db_path_or_host: str
    embedding_dimension: int
    embedding_provider: str
    embedding_model_name: str


class StatusResponse(BaseModel):
    """Response model for status."""

    status: str
    backend: str
    tables_exist: bool
    dimension_match: bool | None
    recorded_dimension: int | None


class AppState:
    """Application state container."""

    def __init__(self):
        self.config: WalnutConfig | None = None
        self._initialized = False

    def is_initialized(self) -> bool:
        return self._initialized

    def set_config(self, config: WalnutConfig) -> None:
        self.config = config
        self._initialized = True


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    env_file = Path(".env")
    if env_file.exists():
        try:
            app_state.config = WalnutConfig.from_file(".env")
            app_state._initialized = True
        except Exception:
            pass
    yield


app = FastAPI(
    title="WalnutEverMem API",
    description="Infinite Context Memory Foundation for LLMs",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_config() -> WalnutConfig:
    """Dependency to get current configuration."""
    if not app_state.is_initialized():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized. Call /init first.",
        )
    return app_state.config


def _config_request_to_config(req: ConfigRequest) -> WalnutConfig:
    """Convert ConfigRequest to WalnutConfig."""
    return WalnutConfig(
        db=DatabaseConfig(
            backend=req.db_backend,
            sqlite_path=req.sqlite_path,
            host=req.db_host,
            port=req.db_port,
            database=req.db_database,
            user=req.db_user,
            password=req.db_password,
        ),
        embedding=EmbeddingConfig(
            dimension=req.embedding_dimension,
            provider=req.embedding_provider,
            model_name=req.embedding_model_name,
            api_key=req.embedding_api_key,
        ),
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "WalnutEverMem",
        "version": "0.1.0",
        "status": "initialized" if app_state.is_initialized() else "not_initialized",
    }


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get system status."""
    if not app_state.is_initialized():
        return StatusResponse(
            status="not_initialized",
            backend="none",
            tables_exist=False,
            dimension_match=None,
            recorded_dimension=None,
        )

    config = app_state.config
    initializer = DatabaseInitializer(config)
    result = await initializer.verify_schema()

    return StatusResponse(
        status="initialized" if result.get("tables_exist") else "not_initialized",
        backend=config.db.backend,
        tables_exist=result.get("tables_exist", False),
        dimension_match=result.get("dimension_match"),
        recorded_dimension=result.get("recorded_dimension"),
    )


@app.post("/init", response_model=StatusResponse)
async def initialize_database(req: InitRequest):
    """Initialize database with configuration."""
    config = _config_request_to_config(req.config)

    initializer = DatabaseInitializer(config)

    if req.drop_existing:
        await initializer.drop_schema()

    await initializer.initialize()

    app_state.config = config
    app_state._initialized = True

    result = await initializer.verify_schema()

    return StatusResponse(
        status="initialized",
        backend=config.db.backend,
        tables_exist=result.get("tables_exist", True),
        dimension_match=result.get("dimension_match"),
        recorded_dimension=result.get("recorded_dimension"),
    )


@app.get("/config", response_model=ConfigResponse)
async def get_configuration(config: WalnutConfig = Depends(get_config)):
    """Get current configuration."""
    return ConfigResponse(
        db_backend=config.db.backend,
        db_path_or_host=config.db.sqlite_path if config.db.backend == "sqlite" else config.db.host,
        embedding_dimension=config.embedding.dimension,
        embedding_provider=config.embedding.provider,
        embedding_model_name=config.embedding.model_name,
    )


@app.post("/remember", response_model=ChatRecordResponse)
async def remember(req: RememberRequest, config: WalnutConfig = Depends(get_config)):
    """Store a new memory."""
    import aiosqlite
    import asyncpg

    embedding = np.array(req.embedding) if req.embedding else None

    if config.db.backend == "sqlite":
        async with aiosqlite.connect(config.db.sqlite_path) as conn:
            repo = MemoryRepository(conn, config)
            record = await repo.append_record(
                session_id=req.session_id,
                role=req.role,
                content=req.content,
                embedding=embedding,
                metadata=req.metadata,
            )
    else:
        conn = await asyncpg.connect(config.db.connection_url)
        try:
            repo = MemoryRepository(conn, config)
            record = await repo.append_record(
                session_id=req.session_id,
                role=req.role,
                content=req.content,
                embedding=embedding,
                metadata=req.metadata,
            )
        finally:
            await conn.close()

    return ChatRecordResponse(
        id=record.id,
        session_id=record.session_id,
        role=record.role.value,
        content=record.content,
        embedding=record.embedding.tolist() if record.embedding is not None else None,
        created_at=record.created_at.isoformat(),
        metadata=record.metadata,
    )


@app.post("/recall", response_model=list[SearchResultResponse])
async def recall(req: RecallRequest, config: WalnutConfig = Depends(get_config)):
    """Recall relevant memories."""
    import aiosqlite
    import asyncpg

    query_embedding = np.array(req.query_embedding) if req.query_embedding else None

    if config.db.backend == "sqlite":
        async with aiosqlite.connect(config.db.sqlite_path) as conn:
            repo = MemoryRepository(conn, config)
            service = MemoryService(repo, config)
            results = await service.recall(
                query=req.query,
                session_id=req.session_id,
                max_results=req.max_results,
            )
    else:
        conn = await asyncpg.connect(config.db.connection_url)
        try:
            repo = MemoryRepository(conn, config)
            service = MemoryService(repo, config)
            results = await service.recall(
                query=req.query,
                session_id=req.session_id,
                max_results=req.max_results,
            )
        finally:
            await conn.close()

    return [
        SearchResultResponse(
            record=ChatRecordResponse(
                id=r.record.id,
                session_id=r.record.session_id,
                role=r.record.role.value,
                content=r.record.content,
                embedding=r.record.embedding.tolist() if r.record.embedding is not None else None,
                created_at=r.record.created_at.isoformat(),
                metadata=r.record.metadata,
            ),
            score=r.score,
            via_pointer=r.via_pointer,
            pointer_source_id=r.pointer_source_id,
        )
        for r in results
    ]


@app.get("/sessions/{session_id}/context", response_model=list[ChatRecordResponse])
async def get_context(
    session_id: str,
    limit: int = 50,
    config: WalnutConfig = Depends(get_config),
):
    """Get recent context for a session."""
    import aiosqlite
    import asyncpg

    if config.db.backend == "sqlite":
        async with aiosqlite.connect(config.db.sqlite_path) as conn:
            repo = MemoryRepository(conn, config)
            records = await repo.get_session_context(session_id, limit=limit)
    else:
        conn = await asyncpg.connect(config.db.connection_url)
        try:
            repo = MemoryRepository(conn, config)
            records = await repo.get_session_context(session_id, limit=limit)
        finally:
            await conn.close()

    return [
        ChatRecordResponse(
            id=r.id,
            session_id=r.session_id,
            role=r.role.value,
            content=r.content,
            embedding=r.embedding.tolist() if r.embedding is not None else None,
            created_at=r.created_at.isoformat(),
            metadata=r.metadata,
        )
        for r in records
    ]


def run_server():
    """Run the FastAPI server."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run_server()
