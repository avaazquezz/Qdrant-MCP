"""Points-selector helper shared by every tool that targets points by id list
or payload filter: `points.py`'s `qdrant_points_delete` (Fase 1) and Fase 3's
`payload.py` (`set`/`overwrite`/`delete`/`clear`) and `vectors.py`
(`vectors_delete`). Not a toolset itself — nothing here calls
`ToolRegistry.register`.
"""

from __future__ import annotations

from uuid import UUID

from mcp.server.mcpserver.exceptions import ToolError
from qdrant_client.http.models import Filter, FilterSelector, PointIdsList


def build_points_selector(
    ids: list[int | str] | None, points_filter: Filter | None
) -> PointIdsList | FilterSelector:
    """Exactly one of `ids` or `points_filter` must be given."""
    if (ids is None) == (points_filter is None):
        raise ToolError("Provide exactly one of `ids` or `points_filter`, not both/neither.")
    if ids is not None:
        # list is invariant in mypy: list[int | str] isn't assignable to
        # PointIdsList's list[int | str | UUID] — rebuild with the wider type.
        point_ids: list[int | str | UUID] = list(ids)
        return PointIdsList(points=point_ids)
    assert points_filter is not None
    return FilterSelector(filter=points_filter)
