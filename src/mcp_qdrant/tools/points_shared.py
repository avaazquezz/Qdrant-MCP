"""Helpers shared by the point-writing tools: the points-selector used by every
tool that targets points by id list or payload filter (`points.py`'s
`qdrant_points_delete` and Fase 3's `payload.py`/`vectors.py`), and the
`PointVectorValue` type used by every tool that writes a point's vectors
(`qdrant_points_upsert`, `qdrant_vectors_update`), and `page_offset`, used by
every tool that pages through points (`qdrant_points_scroll`,
`qdrant_collection_copy`). Not a toolset itself — nothing here calls
`ToolRegistry.register`.
"""

from __future__ import annotations

from uuid import UUID

from mcp.server.mcpserver.exceptions import ToolError
from qdrant_client.http.models import Filter, FilterSelector, PointIdsList, SparseVector

# A point's vector(s): one unnamed dense vector, one unnamed multivector
# (ColBERT-style), or a dict keyed by vector name whose values are dense,
# sparse, or multivectors. Never `Document`/`Image`/`InferenceObject`
# (qdrant-client's server-side embedding inference variants) — this server
# never generates embeddings itself.
PointVectorValue = (
    list[float] | list[list[float]] | dict[str, list[float] | SparseVector | list[list[float]]]
)


def page_offset(offset: object) -> int | str | None:
    """A scroll page offset in a form that serializes cleanly.

    The REST client only ever returns int/str/UUID/None here (never the
    gRPC-only PointId protobuf variant, since this server never opts into
    prefer_grpc) — stringify anything else defensively rather than assume.
    """
    if offset is None or isinstance(offset, int | str):
        return offset
    return str(offset)


def filter_has_no_conditions(points_filter: Filter) -> bool:
    """True if the filter constrains nothing — Qdrant treats that as "every point"."""

    def blank(conditions: object) -> bool:
        return conditions is None or (isinstance(conditions, list) and not conditions)

    min_should = points_filter.min_should
    return (
        blank(points_filter.must)
        and blank(points_filter.should)
        and blank(points_filter.must_not)
        and (min_should is None or blank(min_should.conditions))
    )


def reject_unconstrained_filter(points_filter: Filter, where: str = "`points_filter`") -> None:
    """A filter with no conditions selects every point in the collection (verified:
    `{}`, `{"must": []}` and `{"should": []}` all delete everything). On a tool that
    changes or deletes points that is almost never what was meant — typically a
    condition list that came out empty — so it is refused instead of obeyed."""
    if filter_has_no_conditions(points_filter):
        raise ToolError(
            f"{where} has no conditions, so it would match every point in the collection. "
            "Add at least one condition, or list the ids explicitly."
        )


def build_points_selector(
    ids: list[int | str] | None, points_filter: Filter | None
) -> PointIdsList | FilterSelector:
    """Exactly one of `ids` or `points_filter` must be given, and a filter must
    constrain something."""
    if (ids is None) == (points_filter is None):
        raise ToolError("Provide exactly one of `ids` or `points_filter`, not both/neither.")
    if ids is not None:
        # list is invariant in mypy: list[int | str] isn't assignable to
        # PointIdsList's list[int | str | UUID] — rebuild with the wider type.
        point_ids: list[int | str | UUID] = list(ids)
        return PointIdsList(points=point_ids)
    assert points_filter is not None
    reject_unconstrained_filter(points_filter)
    return FilterSelector(filter=points_filter)
