"""The `core` toolset: collection CRUD (create/list/info/update/delete/exists)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    BinaryQuantization,
    CollectionInfo,
    CollectionParamsDiff,
    CollectionsResponse,
    Disabled,
    Distance,
    HnswConfigDiff,
    OptimizersConfigDiff,
    ProductQuantization,
    ScalarQuantization,
    SparseVectorParams,
    StrictModeConfig,
    VectorParams,
    VectorParamsDiff,
)

from mcp_qdrant.tools.errors import call_qdrant
from mcp_qdrant.tools.registry import ToolRegistry

QuantizationConfigInput = ScalarQuantization | ProductQuantization | BinaryQuantization

_CREATE_ANNOTATIONS = ToolAnnotations(
    title="Create Qdrant collection",
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)
_LIST_ANNOTATIONS = ToolAnnotations(
    title="List Qdrant collections",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_INFO_ANNOTATIONS = ToolAnnotations(
    title="Get Qdrant collection info",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_UPDATE_ANNOTATIONS = ToolAnnotations(
    title="Update Qdrant collection",
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_DELETE_ANNOTATIONS = ToolAnnotations(
    title="Delete Qdrant collection",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)
_EXISTS_ANNOTATIONS = ToolAnnotations(
    title="Check Qdrant collection existence",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


class CollectionDeleteResult(BaseModel):
    """True if the collection existed and was removed; False is a no-op, not
    an error (verified against a real Qdrant instance: DELETE on a missing
    collection returns 200/false, not 404)."""

    deleted: bool


class CollectionExistsResult(BaseModel):
    exists: bool


def register(registry: ToolRegistry, client: AsyncQdrantClient) -> None:
    async def qdrant_collection_create(
        collection_name: str,
        vector_size: Annotated[int, Field(gt=0)] | None = None,
        distance: Literal["Cosine", "Euclid", "Dot", "Manhattan"] = "Cosine",
        vectors: dict[str, VectorParams] | None = None,
        sparse_vectors: dict[str, SparseVectorParams] | None = None,
        quantization_config: QuantizationConfigInput | None = None,
        strict_mode_config: StrictModeConfig | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CollectionInfo:
        """Create a collection: either a single unnamed vector (`vector_size`
        + `distance`), or one or more named vectors (`vectors`, each a full
        `VectorParams` — size, distance, and optionally its own
        `multivector_config` for ColBERT-style multi-vectors or
        `quantization_config`) — exactly one of the two. `sparse_vectors`
        defines sparse (keyword-style) vectors at creation time.
        `quantization_config` (scalar/product/binary) and
        `strict_mode_config` apply to the whole collection.

        Fails with a clear error if a collection with this name already exists.

        Example (simple): {"collection_name": "docs", "vector_size": 4, "distance": "Cosine"}
        Example (hybrid): {"collection_name": "docs", "vectors": {
            "dense": {"size": 4, "distance": "Cosine"}
        }, "sparse_vectors": {"sparse": {}}}
        """
        if (vector_size is None) == (vectors is None):
            raise ToolError("Provide exactly one of `vector_size` or `vectors`, not both/neither.")
        vectors_config = (
            VectorParams(size=vector_size, distance=Distance(distance))
            if vector_size is not None
            else vectors
        )
        assert vectors_config is not None
        await call_qdrant(
            lambda: client.create_collection(
                collection_name,
                vectors_config=vectors_config,
                sparse_vectors_config=sparse_vectors,
                quantization_config=quantization_config,
                strict_mode_config=strict_mode_config,
                metadata=metadata,
            )
        )
        return await call_qdrant(lambda: client.get_collection(collection_name))

    async def qdrant_collection_list() -> CollectionsResponse:
        """List every collection name in the configured Qdrant instance.

        Example: {}
        """
        return await call_qdrant(lambda: client.get_collections())

    async def qdrant_collection_info(collection_name: str) -> CollectionInfo:
        """Return full config and status of one collection.

        Fails with a clear error if the collection doesn't exist.

        Example: {"collection_name": "docs"}
        """
        return await call_qdrant(lambda: client.get_collection(collection_name))

    async def qdrant_collection_update(
        collection_name: str,
        optimizers_config: OptimizersConfigDiff | None = None,
        hnsw_config: HnswConfigDiff | None = None,
        collection_params: CollectionParamsDiff | None = None,
        vectors_config: dict[str, VectorParamsDiff] | None = None,
        quantization_config: QuantizationConfigInput | Literal["disabled"] | None = None,
        sparse_vectors_config: dict[str, SparseVectorParams] | None = None,
        strict_mode_config: StrictModeConfig | None = None,
    ) -> CollectionInfo:
        """Update optimizer/HNSW/collection/vector params on an existing
        collection.

        Only the fields you pass are changed; omitted ones keep their current
        value. `quantization_config="disabled"` turns quantization off.
        `vectors_config`/`sparse_vectors_config` only **adjust** named
        vectors that already exist (HNSW/quantization/index tuning) — they
        cannot add a new one; use `qdrant_collection_vector_create` for
        that, or this fails with Qdrant's own "Not existing vector name"
        error. Fails with a clear error if the collection doesn't exist.

        Example: {"collection_name": "docs", "optimizers_config": {"indexing_threshold": 10000}}
        """
        resolved_quantization = (
            Disabled.DISABLED if quantization_config == "disabled" else quantization_config
        )
        await call_qdrant(
            lambda: client.update_collection(
                collection_name,
                optimizers_config=optimizers_config,
                hnsw_config=hnsw_config,
                collection_params=collection_params,
                vectors_config=vectors_config,
                quantization_config=resolved_quantization,
                sparse_vectors_config=sparse_vectors_config,
                strict_mode_config=strict_mode_config,
            )
        )
        return await call_qdrant(lambda: client.get_collection(collection_name))

    async def qdrant_collection_delete(collection_name: str) -> CollectionDeleteResult:
        """Delete a collection and all its points; a no-op if it doesn't exist.

        Example: {"collection_name": "docs"}
        """
        deleted = await call_qdrant(lambda: client.delete_collection(collection_name))
        return CollectionDeleteResult(deleted=deleted)

    async def qdrant_collection_exists(collection_name: str) -> CollectionExistsResult:
        """Check whether a collection exists, without raising if it doesn't.

        Example: {"collection_name": "docs"}
        """
        exists = await call_qdrant(lambda: client.collection_exists(collection_name))
        return CollectionExistsResult(exists=exists)

    registry.register(qdrant_collection_create, toolset="core", annotations=_CREATE_ANNOTATIONS)
    registry.register(qdrant_collection_list, toolset="core", annotations=_LIST_ANNOTATIONS)
    registry.register(qdrant_collection_info, toolset="core", annotations=_INFO_ANNOTATIONS)
    registry.register(qdrant_collection_update, toolset="core", annotations=_UPDATE_ANNOTATIONS)
    registry.register(qdrant_collection_delete, toolset="core", annotations=_DELETE_ANNOTATIONS)
    registry.register(qdrant_collection_exists, toolset="core", annotations=_EXISTS_ANNOTATIONS)
