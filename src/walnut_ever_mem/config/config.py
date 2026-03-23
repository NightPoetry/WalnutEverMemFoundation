"""Core configuration for WalnutEverMem."""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database connection configuration.

    Supports both SQLite (default, zero-config) and PostgreSQL.
    """

    model_config = SettingsConfigDict(env_prefix="WALNUT_DB_")

    backend: Literal["sqlite", "postgresql"] = Field(
        default="sqlite",
        description="Database backend: sqlite (default) or postgresql",
    )

    sqlite_path: str = Field(
        default="walnut_memory.db",
        description="SQLite database file path (only for sqlite backend)",
    )

    host: str = Field(default="localhost", description="Database host (postgresql only)")
    port: int = Field(default=5432, description="Database port (postgresql only)")
    database: str = Field(default="walnut_memory", description="Database name (postgresql only)")
    user: str = Field(default="postgres", description="Database user (postgresql only)")
    password: str = Field(default="", description="Database password (postgresql only)")

    @property
    def connection_url(self) -> str:
        """Build connection URL based on backend."""
        if self.backend == "sqlite":
            return f"sqlite+aiosqlite:///{self.sqlite_path}"
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def sqlite_file_path(self) -> Path:
        """Get SQLite file path as Path object."""
        return Path(self.sqlite_path)

    def ensure_sqlite_dir(self) -> None:
        """Ensure SQLite database directory exists."""
        if self.backend == "sqlite":
            self.sqlite_file_path.parent.mkdir(parents=True, exist_ok=True)


class EmbeddingConfig(BaseSettings):
    """Embedding configuration.

    Users can configure embedding dimension based on their chosen model:
    - OpenAI text-embedding-3-small: 1536
    - OpenAI text-embedding-3-large: 3072
    - Cohere embed-v3: 1024
    - Local models (sentence-transformers): varies
    """

    model_config = SettingsConfigDict(env_prefix="WALNUT_EMBED_")

    dimension: int = Field(
        default=1536,
        ge=64,
        le=4096,
        description="Embedding vector dimension (must match your embedding model)",
    )
    provider: Literal["openai", "cohere", "local", "custom"] = Field(
        default="openai",
        description="Embedding provider",
    )
    model_name: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name",
    )
    api_key: str | None = Field(
        default=None,
        description="API key for embedding provider",
    )
    api_base: str | None = Field(
        default=None,
        description="Custom API base URL",
    )

    @field_validator("dimension")
    @classmethod
    def validate_dimension(cls, v: int) -> int:
        """Validate dimension is reasonable."""
        if v < 64:
            raise ValueError("Embedding dimension too small (min 64)")
        if v > 4096:
            raise ValueError("Embedding dimension too large (max 4096)")
        return v


class RetrievalConfig(BaseSettings):
    """Retrieval behavior configuration."""

    model_config = SettingsConfigDict(env_prefix="WALNUT_RETRIEVE_")

    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold for pointer matching",
    )
    max_pointers_per_node: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum pointers stored at each node",
    )
    pointer_cleanup_threshold: int = Field(
        default=1000,
        description="Trigger cleanup when pointer count exceeds this",
    )


class WalnutConfig(BaseSettings):
    """Main configuration for WalnutEverMem.

    Configuration can be provided via:
    1. Environment variables (prefixed with WALNUT_)
    2. .env file
    3. Direct instantiation

    Example:
        # From environment (SQLite, zero-config)
        config = WalnutConfig()

        # Custom SQLite path
        config = WalnutConfig(
            db=DatabaseConfig(sqlite_path="/path/to/memory.db")
        )

        # PostgreSQL
        config = WalnutConfig(
            db=DatabaseConfig(
                backend="postgresql",
                host="localhost",
                port=5432,
            )
        )

        # From .env file
        config = WalnutConfig(_env_file=".env")
    """

    model_config = SettingsConfigDict(
        env_prefix="WALNUT_",
        env_nested_delimiter="__",
    )

    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)

    debug: bool = Field(default=False, description="Enable debug mode")

    @classmethod
    def from_file(cls, path: str) -> "WalnutConfig":
        """Load configuration from a .env file."""
        return cls(_env_file=path)

    def to_dict(self) -> dict:
        """Export configuration as dictionary."""
        return self.model_dump()
