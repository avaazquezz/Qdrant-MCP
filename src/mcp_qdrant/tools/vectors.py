"""The `payload` toolset (Fase 3, part 2): atomic batch updates and
named-vector operations, both on existing points and on the collection
itself. See `payload.py` for the payload value/index side of this toolset.
"""

from __future__ import annotations

from typing import Annotated, Literal, cast

from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    ClearPayloadOperation,
    DeleteOperation,
    DeletePayloadOperation,
    DeleteVectorsOperation,
    DenseVectorConfig,
    DenseVectorNameConfig,
    Distance,
    Filter,
    Modifier,
    MultiVectorComparator,
    MultiVectorConfig,
    OverwritePayloadOperation,
    PointVectors,
    SetPayloadOperation,
    SparseVector,
    SparseVectorConfig,
    SparseVectorNameConfig,
    UpdateResult,
    UpdateVectorsOperation,
    UpsertOperation,
    VectorStorageDatatype,
    VectorStruct,
)

from mcp_qdrant.tools.errors import call_qdrant
from mcp_qdrant.tools.points_shared import build_points_selector
from mcp_qdrant.tools.registry import ToolRegistry

BatchOperation = (
    UpsertOperation
    | DeleteOperation
    | SetPayloadOperation
    | OverwritePayloadOperation
    | DeletePayloadOperation
    | ClearPayloadOperation
    | UpdateVectorsOperation
    | DeleteVectorsOperation
)

_VECTOR_CREATE_ANNOTATIONS = ToolAnnotations(
    title="Add a named vector to a Qdrant collection",
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_VECTOR_DELETE_ANNOTATIONS = ToolAnnotations(
    title="Remove a named vector from a Qdrant collection",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)
_BATCH_UPDATE_ANNOTATIONS = ToolAnnotations(
    title="Batch-update Qdrant points atomically",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=False,
    open_world_hint=True,
)
_VECTORS_UPDATE_ANNOTATIONS = ToolAnnotations(
    title="Update point vectors",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)
_VECTORS_DELETE_ANNOTATIONS = ToolAnnotations(
    title="Delete point vectors",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)


class PointVectorInput(BaseModel):
    """A point's vector(s) to replace — never `Document`/`Image`/
    `InferenceObject` (same rule as `PointInput` in points.py: this server
    never generates embeddings itself)."""

    id: int | str
    vector: (
        list[float] | list[list[float]] | dict[str, list[float] | SparseVector | list[list[float]]]
    )


def register(registry: ToolRegistry, client: AsyncQdrantClient) -> None:
    async def qdrant_collection_vector_create(
        collection_name: str,
        vector_name: str,
        vector_kind: Literal["dense", "sparse"],
        size: Annotated[int, Field(gt=0)] | None = None,
        distance: Literal["Cosine", "Euclid", "Dot", "Manhattan"] | None = None,
        multivector_comparator: Literal["max_sim"] | None = None,
        datatype: VectorStorageDatatype | None = None,
        modifier: Modifier | None = None,
    ) -> UpdateResult:
        """Add a new named vector (dense or sparse) to a collection that
        already has points, without touching them.

        Requires a recent Qdrant server: verified hands-on that this 404s on
        v1.13.6 and v1.15.1, and works on v1.19.0 (this project's CI floor
        from Fase 3 onward) — pin your server accordingly. For
        `vector_kind="dense"`, give both `size` and `distance` (optionally
        `multivector_comparator="max_sim"` for ColBERT-style multi-vectors);
        for `"sparse"`, give neither and use `modifier`/`datatype` instead.

        Example (dense): {"collection_name": "docs", "vector_name": "dense",
            "vector_kind": "dense", "size": 4, "distance": "Cosine"}
        Example (sparse): {"collection_name": "docs", "vector_name": "sparse",
            "vector_kind": "sparse"}
        """
        config: DenseVectorNameConfig | SparseVectorNameConfig
        if vector_kind == "dense":
            if size is None or distance is None:
                raise ToolError('`vector_kind="dense"` requires both `size` and `distance`.')
            multivector_config = (
                MultiVectorConfig(comparator=MultiVectorComparator.MAX_SIM)
                if multivector_comparator == "max_sim"
                else None
            )
            config = DenseVectorNameConfig(
                dense=DenseVectorConfig(
                    size=size,
                    distance=Distance(distance),
                    multivector_config=multivector_config,
                    datatype=datatype,
                )
            )
        else:
            if size is not None or distance is not None:
                raise ToolError('`vector_kind="sparse"` does not take `size`/`distance`.')
            config = SparseVectorNameConfig(
                sparse=SparseVectorConfig(modifier=modifier, datatype=datatype)
            )
        return await call_qdrant(
            lambda: client.create_vector_name(
                collection_name, vector_name=vector_name, vector_name_config=config
            )
        )

    async def qdrant_collection_vector_delete(
        collection_name: str, vector_name: str
    ) -> UpdateResult:
        """Remove a named vector (dense or sparse) from a collection —
        points keep their other vectors and payload. Same server-version
        requirement as `qdrant_collection_vector_create`.

        Example: {"collection_name": "docs", "vector_name": "sparse"}
        """
        return await call_qdrant(
            lambda: client.delete_vector_name(collection_name, vector_name=vector_name)
        )

    async def qdrant_points_batch_update(
        collection_name: str, operations: Annotated[list[BatchOperation], Field(min_length=1)]
    ) -> list[UpdateResult]:
        """Run multiple point operations (upsert, delete, set/overwrite/
        delete/clear payload, update/delete vectors) atomically against one
        collection, in the order given. Each item is one of Qdrant's own
        tagged operation shapes, keyed by operation name.

        Example: {"collection_name": "docs", "operations": [
            {"upsert": {"points": [{"id": 1, "vector": [0.1, 0.2, 0.3, 0.4]}]}},
            {"delete_payload": {"keys": ["city"], "points": [1]}}
        ]}
        """
        return await call_qdrant(
            lambda: client.batch_update_points(collection_name, update_operations=operations)
        )

    async def qdrant_vectors_update(
        collection_name: str, points: Annotated[list[PointVectorInput], Field(min_length=1)]
    ) -> UpdateResult:
        """Replace the vector(s) of existing points by id — leaves their
        payload untouched. For a named-vector collection, `vector` is a
        dict keyed by vector name; for a single unnamed vector, pass a
        plain vector.

        Example: {"collection_name": "docs", "points": [
            {"id": 1, "vector": [0.1, 0.2, 0.3, 0.4]}
        ]}
        """
        # PointVectorInput.vector is a narrower union than PointVectors.vector
        # (excludes Document/Image/InferenceObject); dict value types are
        # invariant in mypy too, so a plain reassignment doesn't widen it.
        point_vectors = [PointVectors(id=p.id, vector=cast(VectorStruct, p.vector)) for p in points]
        return await call_qdrant(
            lambda: client.update_vectors(collection_name, points=point_vectors)
        )

    async def qdrant_vectors_delete(
        collection_name: str,
        vector_names: Annotated[list[str], Field(min_length=1)],
        ids: list[int | str] | None = None,
        points_filter: Filter | None = None,
    ) -> UpdateResult:
        """Remove specific named vectors from selected points, keeping
        their payload and other vectors — exactly one of `ids`/
        `points_filter`.

        Example: {"collection_name": "docs", "vector_names": ["sparse"], "ids": [1]}
        """
        selector = build_points_selector(ids, points_filter)
        return await call_qdrant(
            lambda: client.delete_vectors(collection_name, vectors=vector_names, points=selector)
        )

    registry.register(
        qdrant_collection_vector_create, toolset="payload", annotations=_VECTOR_CREATE_ANNOTATIONS
    )
    registry.register(
        qdrant_collection_vector_delete, toolset="payload", annotations=_VECTOR_DELETE_ANNOTATIONS
    )
    registry.register(
        qdrant_points_batch_update, toolset="payload", annotations=_BATCH_UPDATE_ANNOTATIONS
    )
    registry.register(
        qdrant_vectors_update, toolset="payload", annotations=_VECTORS_UPDATE_ANNOTATIONS
    )
    registry.register(
        qdrant_vectors_delete, toolset="payload", annotations=_VECTORS_DELETE_ANNOTATIONS
    )
