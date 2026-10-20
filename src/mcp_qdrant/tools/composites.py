"""The `admin` toolset (Fase 13): operations composed from several Qdrant
calls, where the data stays on the server instead of passing through the
LLM's context.

Both tools are deterministic code over data Qdrant already holds — no
embeddings, no chunking — so they stay within the project's "pure wrapper,
not a RAG" principle:

- `qdrant_collection_copy` moves points (vectors and payload) between two
  collections of the same instance. Re-creating a collection with another
  distance, quantization or HNSW layout is the usual reason, and without this
  tool the vectors would have to round-trip through the model.
- `qdrant_payload_schema_infer` profiles the payload keys actually present, so
  a filter can be written against real keys instead of guessed ones.
"""

from __future__ import annotations

from collections import Counter
from typing import Annotated, Any, cast

from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    PointStruct,
    Sample,
    SampleQuery,
    VectorStruct,
)

from mcp_qdrant.tools.errors import call_qdrant
from mcp_qdrant.tools.points_shared import page_offset
from mcp_qdrant.tools.registry import ToolRegistry
from mcp_qdrant.tools.schemas import FilterInput

# Index types Qdrant can facet on (verified hands-on against v1.19.0: keyword,
# integer, uuid and bool work; float, datetime, text and geo answer 400 "No
# appropriate index for faceting").
_FACETABLE_INDEX_TYPES = frozenset({"keyword", "integer", "uuid", "bool"})

_COPY_ANNOTATIONS = ToolAnnotations(
    title="Copy points between Qdrant collections",
    read_only_hint=False,
    # Points that already exist in the target under the same id are replaced.
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)
_SCHEMA_INFER_ANNOTATIONS = ToolAnnotations(
    title="Infer the payload schema of a Qdrant collection",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


class CollectionCopyResult(BaseModel):
    """`copied` points were written in this call; if `done` is false, call
    again with `offset=next_offset` to continue."""

    copied: int
    next_offset: int | str | None
    done: bool


class ValueCount(BaseModel):
    value: str | int | bool
    count: int


class PayloadFieldProfile(BaseModel):
    key: str
    types: list[str]
    is_array: bool
    present_in: int
    indexed: bool
    index_type: str | None
    top_values: list[ValueCount] | None


class PayloadSchemaProfile(BaseModel):
    collection_points: int | None
    sampled: int
    fields: list[PayloadFieldProfile]
    fields_truncated: bool
    indexed_but_unseen: list[str]


def _type_name(value: object) -> str:
    # bool before int: bool is an int subclass.
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return type(value).__name__


def _walk(value: Any, key: str, seen: dict[str, tuple[set[str], bool]]) -> None:
    """Record every leaf of `value` under the key Qdrant filters use for it:
    `a.b` for nested objects, `a[].b` for objects inside an array, and the bare
    key for an array of scalars."""

    def record(leaf_key: str, type_name: str | None, array: bool) -> None:
        types, was_array = seen.setdefault(leaf_key, (set(), False))
        if type_name is not None:
            types.add(type_name)
        seen[leaf_key] = (types, was_array or array)

    if isinstance(value, dict):
        for child_key, child in value.items():
            _walk(child, f"{key}.{child_key}" if key else str(child_key), seen)
    elif isinstance(value, list):
        if not value:
            record(key, None, True)
        for item in value:
            if isinstance(item, dict):
                for child_key, child in item.items():
                    _walk(child, f"{key}[].{child_key}", seen)
            elif isinstance(item, list):
                record(key, "array", True)
            else:
                record(key, _type_name(item), True)
    else:
        record(key, _type_name(value), False)


def register(registry: ToolRegistry, client: AsyncQdrantClient) -> None:
    async def _same_collection(source: str, target: str) -> bool:
        """True if both names resolve to one collection (an alias counts)."""
        if source == target:
            return True
        aliases = await call_qdrant(lambda: client.get_aliases())
        resolved = {a.alias_name: a.collection_name for a in aliases.aliases}
        return resolved.get(source, source) == resolved.get(target, target)

    async def copy_batch(
        source: str,
        target: str,
        copy_filter: FilterInput | None,
        *,
        start: int | str | None,
        limit: int,
    ) -> tuple[int, int | str | None]:
        """Copy one page; returns (points copied, offset of the next page)."""
        records, raw_next = await call_qdrant(
            lambda: client.scroll(
                source,
                scroll_filter=copy_filter,
                limit=limit,
                offset=start,
                with_payload=True,
                with_vectors=True,
            )
        )
        if records:
            structs = [
                PointStruct(id=r.id, vector=cast(VectorStruct, r.vector), payload=r.payload)
                for r in records
            ]
            await call_qdrant(lambda: client.upsert(target, points=structs))
        return len(records), page_offset(raw_next)

    async def facet_top_values(collection: str, key: str, limit: int) -> list[ValueCount]:
        facet = await call_qdrant(lambda: client.facet(collection, key=key, limit=limit))
        return [
            ValueCount(
                value=hit.value if isinstance(hit.value, str | int | bool) else str(hit.value),
                count=hit.count,
            )
            for hit in facet.hits
        ]

    async def qdrant_collection_copy(
        source_collection: str,
        target_collection: str,
        copy_filter: FilterInput | None = None,
        batch_size: Annotated[int, Field(gt=0, le=1000)] = 100,
        max_points: Annotated[int, Field(gt=0, le=100_000)] = 1000,
        offset: int | str | None = None,
    ) -> CollectionCopyResult:
        """Copy points (all vectors — dense, sparse and multivector — and
        payload) from one collection to another of the same Qdrant instance,
        entirely server-side: the vectors never pass through the model.

        The target must already exist with a compatible vector configuration
        (see `qdrant_collection_info`); this tool does not create it. Use it to
        re-create a collection with another distance, quantization or HNSW
        layout, then switch an alias with `qdrant_alias_update`.

        Each call copies at most `max_points` points, in batches of
        `batch_size`, so no single call runs long. If the result has
        `done: false`, call again with the same arguments and
        `offset=next_offset`. Points that already exist in the target under the
        same id are overwritten, so re-running a copy is safe; points that were
        deleted from the source are not removed from the target. `copy_filter`
        copies only matching points. Points are visited in id order, so points
        added to the source with a lower id than the current offset during a
        long copy are not picked up.

        If a batch fails, the error reports how many points were copied and the
        `offset` to resume from.

        Example: {"source_collection": "docs_v1", "target_collection": "docs_v2"}
        Example (continue): {"source_collection": "docs_v1", "target_collection": "docs_v2",
            "offset": 1000}
        """
        if await _same_collection(source_collection, target_collection):
            raise ToolError(
                f"`{source_collection}` and `{target_collection}` are the same collection "
                "(possibly through an alias); a collection can't be copied onto itself."
            )
        if not await call_qdrant(lambda: client.collection_exists(target_collection)):
            raise ToolError(
                f"Target collection `{target_collection}` doesn't exist: create it first with "
                "qdrant_collection_create, using a vector configuration compatible with "
                f"`{source_collection}` (see qdrant_collection_info)."
            )

        copied = 0
        next_offset: int | str | None = offset
        while copied < max_points:
            batch_start = next_offset
            try:
                page_count, next_offset = await copy_batch(
                    source_collection,
                    target_collection,
                    copy_filter,
                    start=batch_start,
                    limit=min(batch_size, max_points - copied),
                )
            except ToolError as exc:
                raise ToolError(
                    f"Copy stopped after {copied} points; resume with offset={batch_start!r}. "
                    f"Qdrant said: {exc}"
                ) from exc
            copied += page_count
            # An empty page ends the copy even if Qdrant returned a next offset
            # (it doesn't, in practice): otherwise this loop could never advance.
            if page_count == 0 or next_offset is None:
                next_offset = None
                break
        return CollectionCopyResult(
            copied=copied, next_offset=next_offset, done=next_offset is None
        )

    async def qdrant_payload_schema_infer(
        collection_name: str,
        sample_size: Annotated[int, Field(gt=0, le=1000)] = 100,
        sample_filter: FilterInput | None = None,
        top_values: Annotated[int, Field(ge=0, le=50)] = 5,
        max_fields: Annotated[int, Field(gt=0, le=1000)] = 200,
    ) -> PayloadSchemaProfile:
        """Profile the payload keys that actually occur in a collection, so
        filters can be written against real keys instead of guessed ones.

        Looks at a random sample of `sample_size` points (optionally limited by
        `sample_filter`) and reports, per key: the value types seen
        (`string`, `integer`, `float`, `boolean`, `null`), whether it was ever
        an array, how many sampled points have it (`present_in`), and whether
        it has a payload index (`indexed`, `index_type`). Keys use the syntax
        filters expect: `a.b` for nested objects, `a[].b` for objects inside an
        array. For keys with a keyword/integer/uuid/bool index, `top_values`
        adds the most frequent values over the **whole collection** (not just
        the sample), taken from the index; set it to 0 to skip. Also lists
        indexed keys that no sampled point has (`indexed_but_unseen`).

        Because it is a sample, a rare key can be missed: raise `sample_size`
        (up to 1000) if a field you expect doesn't show up. At most
        `max_fields` keys are returned, most common first
        (`fields_truncated` says if more existed).

        Example: {"collection_name": "docs"}
        """
        info = await call_qdrant(lambda: client.get_collection(collection_name))
        sample = await call_qdrant(
            lambda: client.query_points(
                collection_name,
                query=SampleQuery(sample=Sample.RANDOM),
                query_filter=sample_filter,
                limit=sample_size,
                with_payload=True,
                with_vectors=False,
            )
        )

        per_point_keys: Counter[str] = Counter()
        all_types: dict[str, set[str]] = {}
        arrays: set[str] = set()
        for point in sample.points:
            seen: dict[str, tuple[set[str], bool]] = {}
            _walk(point.payload or {}, "", seen)
            for key, (types, was_array) in seen.items():
                per_point_keys[key] += 1
                all_types.setdefault(key, set()).update(types)
                if was_array:
                    arrays.add(key)

        schema = info.payload_schema
        ranked = sorted(per_point_keys, key=lambda k: (-per_point_keys[k], k))
        profiles: list[PayloadFieldProfile] = []
        for key in ranked[:max_fields]:
            index = schema.get(key)
            index_type = index.data_type.value if index is not None else None
            values = (
                await facet_top_values(collection_name, key, top_values)
                if top_values > 0 and index_type in _FACETABLE_INDEX_TYPES
                else None
            )
            profiles.append(
                PayloadFieldProfile(
                    key=key,
                    types=sorted(all_types[key]),
                    is_array=key in arrays,
                    present_in=per_point_keys[key],
                    indexed=index is not None,
                    index_type=index_type,
                    top_values=values,
                )
            )
        return PayloadSchemaProfile(
            collection_points=info.points_count,
            sampled=len(sample.points),
            fields=profiles,
            fields_truncated=len(ranked) > max_fields,
            indexed_but_unseen=sorted(set(schema) - set(per_point_keys)),
        )

    registry.register(qdrant_collection_copy, toolset="admin", annotations=_COPY_ANNOTATIONS)
    registry.register(
        qdrant_payload_schema_infer, toolset="admin", annotations=_SCHEMA_INFER_ANNOTATIONS
    )
