"""The `snapshots` toolset (Fase 4): backup/restore at collection level and
for the whole storage.

`qdrant-client==1.19.0`'s only "download a snapshot" method
(`client.http.snapshots_api.get_snapshot`/`get_full_snapshot`) is unusable:
it always calls `response.json()` on the result, which crashes with a
`UnicodeDecodeError` against a real (binary) snapshot file — verified
hands-on, not assumed. There is also no sane way to carry a
multi-megabyte-to-gigabyte binary blob through an MCP tool result anyway.
So `qdrant_snapshot_download`/`qdrant_storage_snapshot_download` here don't
fetch bytes: they confirm (via `list_snapshots`/`list_full_snapshots`,
fully within the SDK) that the snapshot exists and return its descriptor
plus the REST URL it's served at — verified hands-on that this URL is
directly reusable as `qdrant_snapshot_recover`'s `location`.

There is no `recover_full_snapshot`: restoring the whole storage happens
with the server stopped, pointed at the snapshot file at startup — not a
live API call — so no such tool exists here.
"""

from __future__ import annotations

from urllib.parse import quote, urlsplit

from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import SnapshotDescription, SnapshotPriority

from mcp_qdrant.config import url_origin
from mcp_qdrant.tools.errors import call_qdrant, require_result
from mcp_qdrant.tools.registry import ToolRegistry

_CREATE_ANNOTATIONS = ToolAnnotations(
    title="Create a Qdrant collection snapshot",
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)
_LIST_ANNOTATIONS = ToolAnnotations(
    title="List Qdrant collection snapshots",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_DELETE_ANNOTATIONS = ToolAnnotations(
    title="Delete a Qdrant collection snapshot",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)
_RECOVER_ANNOTATIONS = ToolAnnotations(
    title="Recover a Qdrant collection from a snapshot",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)
_DOWNLOAD_ANNOTATIONS = ToolAnnotations(
    title="Get a Qdrant collection snapshot's download URL",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_STORAGE_CREATE_ANNOTATIONS = ToolAnnotations(
    title="Create a full Qdrant storage snapshot",
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)
_STORAGE_LIST_ANNOTATIONS = ToolAnnotations(
    title="List full Qdrant storage snapshots",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_STORAGE_DELETE_ANNOTATIONS = ToolAnnotations(
    title="Delete a full Qdrant storage snapshot",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)
_STORAGE_DOWNLOAD_ANNOTATIONS = ToolAnnotations(
    title="Get a full Qdrant storage snapshot's download URL",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


class SnapshotDownloadInfo(BaseModel):
    name: str
    size: int
    checksum: str | None
    url: str


class SnapshotDeleteResult(BaseModel):
    """True when the snapshot was removed. Unlike `qdrant_collection_delete`,
    deleting a snapshot that doesn't exist is an error, not a False (verified)."""

    deleted: bool


class SnapshotRecoverResult(BaseModel):
    recovered: bool


def _find_snapshot(snapshots: list[SnapshotDescription], snapshot_name: str) -> SnapshotDescription:
    for snapshot in snapshots:
        if snapshot.name == snapshot_name:
            return snapshot
    raise ToolError(f"Snapshot {snapshot_name!r} not found.")


def _require_qdrant_url(qdrant_url: str | None) -> str:
    if qdrant_url is None:
        raise ToolError(
            "Downloading a snapshot requires QDRANT_URL (remote mode); this server is "
            "configured with QDRANT_LOCAL_PATH, which has no HTTP endpoint to serve it from."
        )
    return qdrant_url


def _check_recover_location(location: str, allowed: set[tuple[str, str, int]]) -> None:
    """The Qdrant server itself fetches `location`, so an unchecked URL lets
    whoever drives the model make it request any address it can reach (SSRF:
    internal services, cloud metadata endpoints). Only the server's own disk and
    origins the operator listed are allowed."""
    if urlsplit(location).scheme == "file":
        return
    if url_origin(location) not in allowed:
        raise ToolError(
            f"`location` {location!r} is not allowed: use a `file://` path on the Qdrant "
            "server, a URL on QDRANT_URL's own origin (e.g. from `qdrant_snapshot_download`), "
            "or an origin the operator listed in QDRANT_MCP_SNAPSHOT_ALLOWED_ORIGINS."
        )


def register(
    registry: ToolRegistry,
    client: AsyncQdrantClient,
    qdrant_url: str | None,
    allowed_origins: tuple[str, ...] = (),
) -> None:
    allowed_recover_origins = {
        origin for origin in map(url_origin, (qdrant_url or "", *allowed_origins)) if origin
    }

    async def qdrant_snapshot_create(collection_name: str) -> SnapshotDescription:
        """Create a snapshot of one collection's current state.

        Example: {"collection_name": "docs"}
        """
        snapshot = await call_qdrant(lambda: client.create_snapshot(collection_name))
        # Only None when wait=False (not exposed here) races ahead of the
        # server actually finishing the snapshot.
        return require_result(snapshot, "snapshot description")

    async def qdrant_snapshot_list(collection_name: str) -> list[SnapshotDescription]:
        """List the snapshots stored for one collection.

        Example: {"collection_name": "docs"}
        """
        return await call_qdrant(lambda: client.list_snapshots(collection_name))

    async def qdrant_snapshot_delete(
        collection_name: str, snapshot_name: str
    ) -> SnapshotDeleteResult:
        """Delete a collection snapshot, freeing its disk space on the
        server — does not touch the live collection. Fails if the snapshot
        doesn't exist.

        Example: {"collection_name": "docs", "snapshot_name": "docs-....snapshot"}
        """
        deleted = await call_qdrant(lambda: client.delete_snapshot(collection_name, snapshot_name))
        return SnapshotDeleteResult(deleted=bool(deleted))

    async def qdrant_snapshot_recover(
        collection_name: str,
        location: str,
        priority: SnapshotPriority | None = None,
        checksum: str | None = None,
        api_key: str | None = None,
    ) -> SnapshotRecoverResult:
        """Restore the points (vectors and payload) captured in a snapshot
        into `collection_name` — points written since the snapshot are lost.
        On an existing collection, its current configuration (e.g. optimizer
        settings), payload indexes and aliases are kept, not rolled back to the
        snapshot's (verified). A missing collection is created with the
        snapshot's configuration.

        `location` must be reachable by the Qdrant **server itself**, not
        necessarily by whoever calls this tool: an HTTP(S) URL (e.g. from
        `qdrant_snapshot_download`) or a `file://` path on the server's own
        disk. If Qdrant runs behind Docker port-remapping or a reverse
        proxy, the URL the server needs may differ from the one used to
        reach it from outside — this tool does not try to guess that.
        `checksum` (SHA256) verifies integrity before recovering; `api_key`
        authenticates to a *remote* snapshot host, not this Qdrant instance.
        Allowed locations: `file://`, QDRANT_URL's own origin, and the origins
        the operator listed in QDRANT_MCP_SNAPSHOT_ALLOWED_ORIGINS — anything
        else is refused before Qdrant is asked to fetch it.

        Example: {"collection_name": "docs", "location": "http://localhost:6333/collections/docs/snapshots/docs-....snapshot"}
        """
        _check_recover_location(location, allowed_recover_origins)
        recovered = await call_qdrant(
            lambda: client.recover_snapshot(
                collection_name,
                location=location,
                priority=priority,
                checksum=checksum,
                api_key=api_key,
            )
        )
        return SnapshotRecoverResult(recovered=bool(recovered))

    async def qdrant_snapshot_download(
        collection_name: str, snapshot_name: str
    ) -> SnapshotDownloadInfo:
        """Confirm a collection snapshot exists and return where to fetch
        it from — this tool does not transfer the (potentially huge)
        snapshot file itself; download it yourself (e.g. `curl`) from the
        returned `url`.

        Example: {"collection_name": "docs", "snapshot_name": "docs-....snapshot"}
        """
        url = _require_qdrant_url(qdrant_url)
        snapshots = await call_qdrant(lambda: client.list_snapshots(collection_name))
        snapshot = _find_snapshot(snapshots, snapshot_name)
        return SnapshotDownloadInfo(
            name=snapshot.name,
            size=snapshot.size,
            checksum=snapshot.checksum,
            url=(
                f"{url}/collections/{quote(collection_name, safe='')}"
                f"/snapshots/{quote(snapshot.name, safe='')}"
            ),
        )

    async def qdrant_storage_snapshot_create() -> SnapshotDescription:
        """Create a snapshot of the whole storage: a snapshot of every
        collection plus the alias mapping (verified: no server configuration
        is included), not just one collection.

        Example: {}
        """
        snapshot = await call_qdrant(lambda: client.create_full_snapshot())
        return require_result(snapshot, "snapshot description")

    async def qdrant_storage_snapshot_list() -> list[SnapshotDescription]:
        """List the full-storage snapshots stored on the server.

        Example: {}
        """
        return await call_qdrant(lambda: client.list_full_snapshots())

    async def qdrant_storage_snapshot_delete(snapshot_name: str) -> SnapshotDeleteResult:
        """Delete a full-storage snapshot, freeing its disk space. Fails if
        the snapshot doesn't exist.

        Example: {"snapshot_name": "full-....snapshot"}
        """
        deleted = await call_qdrant(lambda: client.delete_full_snapshot(snapshot_name))
        return SnapshotDeleteResult(deleted=bool(deleted))

    async def qdrant_storage_snapshot_download(snapshot_name: str) -> SnapshotDownloadInfo:
        """Confirm a full-storage snapshot exists and return where to
        fetch it from — same caveat as `qdrant_snapshot_download`: this
        tool does not transfer the file itself.

        There is no `qdrant_storage_snapshot_recover`: restoring a full
        storage snapshot is done with the server stopped, pointed at the
        snapshot file at startup — not a live API call.

        Example: {"snapshot_name": "full-....snapshot"}
        """
        url = _require_qdrant_url(qdrant_url)
        snapshots = await call_qdrant(lambda: client.list_full_snapshots())
        snapshot = _find_snapshot(snapshots, snapshot_name)
        return SnapshotDownloadInfo(
            name=snapshot.name,
            size=snapshot.size,
            checksum=snapshot.checksum,
            url=f"{url}/snapshots/{quote(snapshot.name, safe='')}",
        )

    registry.register(qdrant_snapshot_create, toolset="snapshots", annotations=_CREATE_ANNOTATIONS)
    registry.register(qdrant_snapshot_list, toolset="snapshots", annotations=_LIST_ANNOTATIONS)
    registry.register(qdrant_snapshot_delete, toolset="snapshots", annotations=_DELETE_ANNOTATIONS)
    registry.register(
        qdrant_snapshot_recover, toolset="snapshots", annotations=_RECOVER_ANNOTATIONS
    )
    registry.register(
        qdrant_snapshot_download, toolset="snapshots", annotations=_DOWNLOAD_ANNOTATIONS
    )
    registry.register(
        qdrant_storage_snapshot_create, toolset="snapshots", annotations=_STORAGE_CREATE_ANNOTATIONS
    )
    registry.register(
        qdrant_storage_snapshot_list, toolset="snapshots", annotations=_STORAGE_LIST_ANNOTATIONS
    )
    registry.register(
        qdrant_storage_snapshot_delete,
        toolset="snapshots",
        annotations=_STORAGE_DELETE_ANNOTATIONS,
    )
    registry.register(
        qdrant_storage_snapshot_download,
        toolset="snapshots",
        annotations=_STORAGE_DOWNLOAD_ANNOTATIONS,
    )
