"""Tests for configuration system."""

import pytest

from walnut_ever_mem.config import (
    DatabaseConfig,
    EmbeddingConfig,
    RetrievalConfig,
    WalnutConfig,
)


def test_database_config_defaults():
    """Test default database configuration."""
    config = DatabaseConfig()
    assert config.host == "localhost"
    assert config.port == 5432
    assert config.database == "walnut_memory"
    assert config.user == "postgres"


def test_database_config_connection_url():
    """Test connection URL generation."""
    config = DatabaseConfig(
        host="db.example.com",
        port=5433,
        database="test_db",
        user="testuser",
        password="secret",
    )
    assert config.connection_url == "postgresql://testuser:secret@db.example.com:5433/test_db"


def test_embedding_config_dimension_validation():
    """Test embedding dimension validation."""
    config = EmbeddingConfig(dimension=1536)
    assert config.dimension == 1536

    with pytest.raises(ValueError):
        EmbeddingConfig(dimension=32)

    with pytest.raises(ValueError):
        EmbeddingConfig(dimension=5000)


def test_embedding_config_providers():
    """Test embedding provider configuration."""
    config = EmbeddingConfig(
        provider="openai",
        model_name="text-embedding-3-large",
        dimension=3072,
    )
    assert config.provider == "openai"
    assert config.dimension == 3072


def test_retrieval_config_defaults():
    """Test default retrieval configuration."""
    config = RetrievalConfig()
    assert config.similarity_threshold == 0.7
    assert config.max_pointers_per_node == 100


def test_walnut_config_nested():
    """Test nested configuration."""
    config = WalnutConfig(
        db=DatabaseConfig(host="custom.host"),
        embedding=EmbeddingConfig(dimension=1024),
    )
    assert config.db.host == "custom.host"
    assert config.embedding.dimension == 1024


def test_walnut_config_to_dict():
    """Test configuration export."""
    config = WalnutConfig()
    d = config.to_dict()
    assert "db" in d
    assert "embedding" in d
    assert "retrieval" in d
