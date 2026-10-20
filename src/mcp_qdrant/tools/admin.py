"""The `admin` toolset (Fase 12): collection aliases and single-node
introspection.

Verified hands-on against Qdrant `v1.19.0` running as a single node that
aliases, `collection_cluster_info` and `get_optimizations` all work there —
unlike shard keys and resharding (the reason Fase 5 was discarded), which
need a distributed deployment.

`qdrant_collection_optimizations` calls the low-level REST layer
(`client.http.collections_api`) instead of `AsyncQdrantClient.get_optimizations`:
the high-level wrapper silently drops the `with` selector, so it can only ever
return the summary and the running optimizations, never the queued/completed/
idle-segment detail. As in Fase 6, the low-level call returns the full
response envelope, so `.result` is unwrapped by hand.
"""

from __future__ import annotations

from typing import Annotated, Literal, cast

from mcp_types import ToolAnnotations
from pydantic import Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    CollectionClusterInfo,
    CollectionsAliasesResponse,
    CreateAliasOperation,
    DeleteAliasOperation,
    OptimizationsResponse,
    RenameAliasOperation,
)

from mcp_qdrant.tools.errors import call_qdrant
from mcp_qdrant.tools.registry import ToolRegistry

AliasOperationInput = CreateAliasOperation | DeleteAliasOperation | RenameAliasOperation
OptimizationDetail = Literal["queued", "completed", "idle_segments"]

_ALIAS_LIST_ANNOTATIONS = ToolAnnotations(
    title="List Qdrant aliases",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_COLLECTION_ALIASES_ANNOTATIONS = ToolAnnotations(
    title="List the aliases of one Qdrant collection",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_ALIAS_UPDATE_ANNOTATIONS = ToolAnnotations(
    title="Create, rename, re-point or delete Qdrant aliases",
    read_only_hint=False,
    # Re-pointing or deleting an alias silently changes what every consumer
    # of that name reads from, even though no collection data is touched.
    destructive_hint=True,
    idempotent_hint=False,
    open_world_hint=True,
)
_CLUSTER_INFO_ANNOTATIONS = ToolAnnotations(
    title="Get Qdrant collection shard layout",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_OPTIMIZATIONS_ANNOTATIONS = ToolAnnotations(
    title="Get Qdrant collection optimizer progress",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


def register(registry: ToolRegistry, client: AsyncQdrantClient) -> None:
    async def qdrant_alias_list() -> CollectionsAliasesResponse:
        """List every alias on the server with the collection it points to.

        An alias is an alternative name for a collection, accepted by Qdrant
        anywhere a `collection_name` is — see `qdrant_alias_update`. Aliases
        are not returned by `qdrant_collection_list`.

        Example: {}
        """
        return await call_qdrant(lambda: client.get_aliases())

    async def qdrant_collection_aliases(collection_name: str) -> CollectionsAliasesResponse:
        """List the aliases that point to one collection (an empty list if
        it has none). Fails with a clear error if the collection doesn't
        exist.

        Example: {"collection_name": "docs_v2"}
        """
        return await call_qdrant(lambda: client.get_collection_aliases(collection_name))

    async def qdrant_alias_update(
        operations: Annotated[list[AliasOperationInput], Field(min_length=1)],
    ) -> bool:
        """Create, rename, re-point or delete aliases — the basis of a
        zero-downtime reindex: build the new collection, then switch the
        alias that clients use.

        Each operation is exactly one of `create_alias`
        (`collection_name`, `alias_name`), `rename_alias`
        (`old_alias_name`, `new_alias_name`) or `delete_alias`
        (`alias_name`). Operations run in order in one request but are NOT
        rolled back as a group: if a later one fails, the earlier ones stay
        applied (verified) — check `qdrant_alias_list` after an error.
        To switch an alias to another collection, send a single
        `create_alias`: on an alias name that already exists it re-points it,
        and a single operation is all-or-nothing.

        Other verified behavior: deleting an alias that doesn't exist is a
        no-op, not an error; an alias can't take the name of an existing
        collection (409); creating one for a missing collection fails.
        Deleting a collection also removes the aliases that pointed to it. No
        collection data is ever modified.

        Example (zero-downtime switch): {"operations": [
            {"create_alias": {"collection_name": "docs_v2", "alias_name": "docs"}}
        ]}
        Example (rename then delete): {"operations": [
            {"rename_alias": {"old_alias_name": "docs", "new_alias_name": "docs_old"}},
            {"delete_alias": {"alias_name": "docs_old"}}
        ]}
        """
        return await call_qdrant(lambda: client.update_collection_aliases(operations))

    async def qdrant_collection_cluster_info(collection_name: str) -> CollectionClusterInfo:
        """Shard layout of a collection: how many shards it has and, for
        each local shard, its point count and replica state. Works on a
        single-node deployment too (one peer, `remote_shards` empty); shard
        transfers and resharding only ever appear on a distributed
        deployment. Fails with a clear error if the collection doesn't exist.

        Example: {"collection_name": "docs"}
        """
        return await call_qdrant(lambda: client.collection_cluster_info(collection_name))

    async def qdrant_collection_optimizations(
        collection_name: str,
        include: list[OptimizationDetail] | None = None,
        completed_limit: Annotated[int, Field(gt=0)] | None = None,
    ) -> OptimizationsResponse:
        """Progress of the background optimizer for a collection — answers
        "has it finished indexing?" and "why isn't the collection green?".

        Always returns a summary (queued optimizations/segments/points and
        idle segments) and the optimizations running right now. `include`
        adds detail lists: `queued` (waiting optimizations), `completed`
        (finished ones; bound them with `completed_limit`) and
        `idle_segments` (segments with nothing to optimize). Fails with a
        clear error if the collection doesn't exist.

        Example: {"collection_name": "docs"}
        Example (full detail): {"collection_name": "docs",
            "include": ["queued", "completed", "idle_segments"], "completed_limit": 5}
        """
        selector = ",".join(include) if include else None
        # The generated stubs type both optional params as plain `str`/`int`
        # despite defaulting to None and accepting it at runtime (verified
        # hands-on) — codegen quirk, same as `details_level` in Fase 6.
        response = await call_qdrant(
            lambda: client.http.collections_api.get_optimizations(
                collection_name,
                _with=cast(str, selector),
                completed_limit=cast(int, completed_limit),
            )
        )
        assert response.result is not None
        return response.result

    registry.register(qdrant_alias_list, toolset="admin", annotations=_ALIAS_LIST_ANNOTATIONS)
    registry.register(
        qdrant_collection_aliases, toolset="admin", annotations=_COLLECTION_ALIASES_ANNOTATIONS
    )
    registry.register(qdrant_alias_update, toolset="admin", annotations=_ALIAS_UPDATE_ANNOTATIONS)
    registry.register(
        qdrant_collection_cluster_info, toolset="admin", annotations=_CLUSTER_INFO_ANNOTATIONS
    )
    registry.register(
        qdrant_collection_optimizations, toolset="admin", annotations=_OPTIMIZATIONS_ANNOTATIONS
    )
