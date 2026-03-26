"""Utility functions and helpers."""

from datetime import datetime
from typing import Any

import numpy as np


def format_timestamp(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def cosine_similarity_batch(
    query: np.ndarray,
    vectors: list[np.ndarray],
) -> np.ndarray:
    """Compute cosine similarity between query and multiple vectors.

    Args:
        query: Query vector (1D)
        vectors: List of vectors to compare against

    Returns:
        Array of similarity scores
    """
    if not vectors:
        return np.array([])

    matrix = np.stack(vectors)
    query_norm = np.linalg.norm(query)
    matrix_norms = np.linalg.norm(matrix, axis=1)

    similarities = np.dot(matrix, query) / (matrix_norms * query_norm)
    return similarities


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."





def validate_embedding_dimension(embedding: np.ndarray, expected_dim: int) -> bool:
    """Validate embedding has expected dimension."""
    return embedding.shape[-1] == expected_dim


def merge_metadata(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge two metadata dictionaries."""
    result = base.copy()
    result.update(override)
    return result
