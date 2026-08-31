"""Confirms the `snapshots` toolset works against a real Qdrant instance.

Verified hands-on (not assumed) that the URL `qdrant_snapshot_download`
returns is directly reusable as `qdrant_snapshot_recover`'s `location` — a
mock can't prove that round-trip, only a real server can. This test relies
on Qdrant being reachable at the *same* `QDRANT_URL` from both the test
runner and the Qdrant server itself (true for CI's service container and
for a plain `docker run -p 6333:6333`, but not for setups with port
remapping between the two).
"""

from __future__ import annotations

import os
import uuid

import pytest
from mcp.server import MCPServer
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from mcp_qdrant.tools import snapshots as snapshots_tools
from mcp_qdrant.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration


async def test_snapshots_toolset_against_real_qdrant() -> None:
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    client = AsyncQdrantClient(url=url, timeout=15)
    collection_name = f"mcp-test-{uuid.uuid4().hex[:8]}"

    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("snapshots",), read_only=False)
    snapshots_tools.register(registry, client, url)

    try:
        await client.create_collection(
            collection_name, vectors_config=VectorParams(size=4, distance=Distance.COSINE)
        )
        await client.upsert(
            collection_name,
            points=[PointStruct(id=1, vector=[1.0, 0.0, 0.0, 0.0], payload={"city": "ny"})],
        )

        # 1. Create.
        create_result = await server.call_tool(
            "qdrant_snapshot_create", {"collection_name": collection_name}
        )
        assert isinstance(create_result, CallToolResult)
        assert create_result.is_error is False
        snapshot_name = create_result.structured_content["name"]

        # 2. List: the snapshot we just created shows up.
        list_result = await server.call_tool(
            "qdrant_snapshot_list", {"collection_name": collection_name}
        )
        assert isinstance(list_result, CallToolResult)
        assert snapshot_name in [s["name"] for s in list_result.structured_content["result"]]

        # 3. Download: get the URL, and confirm it matches the real REST path.
        download_result = await server.call_tool(
            "qdrant_snapshot_download",
            {"collection_name": collection_name, "snapshot_name": snapshot_name},
        )
        assert isinstance(download_result, CallToolResult)
        assert download_result.is_error is False
        snapshot_url = download_result.structured_content["url"]
        assert snapshot_url == f"{url}/collections/{collection_name}/snapshots/{snapshot_name}"

        # 4. Mutate: delete the point, to prove recovery restores it.
        await client.delete(collection_name, points_selector=[1])
        count_before = await client.count(collection_name)
        assert count_before.count == 0

        # 5. Recover: point 1 comes back.
        recover_result = await server.call_tool(
            "qdrant_snapshot_recover",
            {"collection_name": collection_name, "location": snapshot_url},
        )
        assert isinstance(recover_result, CallToolResult)
        assert recover_result.is_error is False
        assert recover_result.structured_content["recovered"] is True
        record = (await client.retrieve(collection_name, ids=[1], with_payload=True))[0]
        assert record.payload == {"city": "ny"}

        # 6. Delete the snapshot.
        delete_result = await server.call_tool(
            "qdrant_snapshot_delete",
            {"collection_name": collection_name, "snapshot_name": snapshot_name},
        )
        assert isinstance(delete_result, CallToolResult)
        assert delete_result.structured_content["deleted"] is True

        # 7. Full-storage snapshots: create, list, download, delete.
        storage_create_result = await server.call_tool("qdrant_storage_snapshot_create", {})
        assert isinstance(storage_create_result, CallToolResult)
        assert storage_create_result.is_error is False
        storage_snapshot_name = storage_create_result.structured_content["name"]

        storage_list_result = await server.call_tool("qdrant_storage_snapshot_list", {})
        assert isinstance(storage_list_result, CallToolResult)
        assert storage_snapshot_name in [
            s["name"] for s in storage_list_result.structured_content["result"]
        ]

        storage_download_result = await server.call_tool(
            "qdrant_storage_snapshot_download", {"snapshot_name": storage_snapshot_name}
        )
        assert isinstance(storage_download_result, CallToolResult)
        assert (
            storage_download_result.structured_content["url"]
            == f"{url}/snapshots/{storage_snapshot_name}"
        )

        storage_delete_result = await server.call_tool(
            "qdrant_storage_snapshot_delete", {"snapshot_name": storage_snapshot_name}
        )
        assert isinstance(storage_delete_result, CallToolResult)
        assert storage_delete_result.structured_content["deleted"] is True
    finally:
        await client.delete_collection(collection_name)
        await client.close()
