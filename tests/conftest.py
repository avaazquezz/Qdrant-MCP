"""Shared pytest fixtures for mcp_qdrant tests (the `integration` marker is
registered in pyproject.toml)."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from qdrant_client.http.models import (
    CollectionConfig,
    CollectionInfo,
    CollectionParams,
    CollectionStatus,
    HnswConfig,
    OptimizersConfig,
    OptimizersStatusOneOf,
)


@pytest.fixture
def make_collection_info() -> Callable[..., CollectionInfo]:
    """A minimal but real CollectionInfo factory — used wherever a test needs
    the client to return one, so structured_content serialization is
    exercised against a genuine pydantic model instead of a loosely shaped
    mock."""

    def _make(points_count: int = 0) -> CollectionInfo:
        return CollectionInfo(
            status=CollectionStatus.GREEN,
            optimizer_status=OptimizersStatusOneOf.OK,
            segments_count=1,
            points_count=points_count,
            config=CollectionConfig(
                params=CollectionParams(),
                hnsw_config=HnswConfig(m=16, ef_construct=100, full_scan_threshold=10000),
                optimizer_config=OptimizersConfig(default_segment_number=0, flush_interval_sec=5),
            ),
            payload_schema={},
        )

    return _make
