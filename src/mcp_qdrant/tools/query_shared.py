"""Query-construction helpers shared by the `qdrant_query` family: `query.py`'s
`qdrant_query` (toolset `core`) and `search.py`'s `qdrant_query_batch`/`_groups`,
`qdrant_recommend*`, `qdrant_discover*` (toolset `search`). Not a toolset itself —
nothing here calls `ToolRegistry.register`.
"""

from __future__ import annotations

from typing import Literal

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel
from qdrant_client.http.models import Filter, Fusion, FusionQuery, LookupLocation, Prefetch

VectorOrId = list[float] | int | str
FusionName = Literal["rrf", "dbsf"]

_FUSION_BY_NAME: dict[FusionName, Fusion] = {"rrf": Fusion.RRF, "dbsf": Fusion.DBSF}


class PrefetchInput(BaseModel):
    """One prefetch stage: an independent query narrowing candidates before
    the outer query reranks or fuses them. One level only — Qdrant allows
    nested prefetch, but nothing in this catalog needs it."""

    query_vector: VectorOrId
    using: str | None = None
    query_filter: Filter | None = None
    limit: int | None = None


class LookupFromInput(BaseModel):
    """Resolve the query/context vector from a point id in another
    collection instead of passing it inline."""

    collection: str
    vector: str | None = None


def build_query_value(
    query_vector: VectorOrId | None, fusion: FusionName | None
) -> VectorOrId | FusionQuery:
    """Exactly one of `query_vector` (a literal vector or point id) or
    `fusion` (combine the prefetch stages via RRF/DBSF) must be given."""
    if (query_vector is None) == (fusion is None):
        raise ToolError("Provide exactly one of `query_vector` or `fusion`, not both/neither.")
    if fusion is not None:
        return FusionQuery(fusion=_FUSION_BY_NAME[fusion])
    assert query_vector is not None
    return query_vector


def build_prefetch_list(prefetch: list[PrefetchInput] | None) -> list[Prefetch] | None:
    if prefetch is None:
        return None
    return [
        Prefetch(query=p.query_vector, using=p.using, filter=p.query_filter, limit=p.limit)
        for p in prefetch
    ]


def build_lookup_from(lookup_from: LookupFromInput | None) -> LookupLocation | None:
    if lookup_from is None:
        return None
    return LookupLocation(collection=lookup_from.collection, vector=lookup_from.vector)
