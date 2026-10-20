"""Records website/data/scenarios.generated.json: the demo transcripts the landing page
plays back, captured by running the REAL tools against a REAL Qdrant.

The page never fabricates a tool call or a result. Every step below is executed through
the MCP server in-process (`server.call_tool`, the same path a client uses), the response
is summarized by a small pure function, and the outcome — including the error text of a
refused call — is written to JSON. CI re-records and fails if the file would change, so a
behavior change in a tool (or in Qdrant) cannot leave the page describing something that
no longer happens.

Needs a Qdrant at QDRANT_URL (default http://localhost:6333). It creates and removes its
own `demo_*` collections.

Run `uv run python scripts/record_scenarios.py` to rewrite the file in place, or `--check`
(used in CI, which has a Qdrant service) to fail if it would change.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import DeleteAlias, DeleteAliasOperation

from mcp_qdrant import __version__
from mcp_qdrant.config import ALL_TOOLSETS, Settings
from mcp_qdrant.server import build_server

OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent / "website" / "data" / "scenarios.generated.json"
)
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
DEMO_COLLECTIONS = ("demo_articles", "demo_docs_v1", "demo_docs_v2", "demo_events", "demo_safe")

Summary = Callable[[dict[str, Any]], Any]


def _vectors(config: dict[str, Any]) -> Any:
    vectors = config["params"].get("vectors")
    if isinstance(vectors, dict) and "size" in vectors:
        return {"size": vectors["size"], "distance": vectors["distance"]}
    return {
        name: {"size": v["size"], "distance": v["distance"]} for name, v in (vectors or {}).items()
    }


def _info(content: dict[str, Any]) -> dict[str, Any]:
    config = content["config"]
    summary: dict[str, Any] = {
        "status": content["status"],
        "points_count": content["points_count"],
        "vectors": _vectors(config),
        "hnsw_m": config["hnsw_config"]["m"],
    }
    sparse = config["params"].get("sparse_vectors")
    if sparse:
        summary["sparse_vectors"] = sorted(sparse)
    return summary


def _hits(content: dict[str, Any]) -> dict[str, Any]:
    return {
        "hits": [
            {
                "id": point["id"],
                "title": (point.get("payload") or {}).get("title"),
                "score": round(point["score"], 4),
            }
            for point in content["points"]
        ]
    }


def _profile(content: dict[str, Any]) -> dict[str, Any]:
    return {
        "sampled": content["sampled"],
        "collection_points": content["collection_points"],
        "fields": [
            {
                key: field[key]
                for key in ("key", "types", "is_array", "present_in", "indexed", "index_type")
            }
            | ({"top_values": field["top_values"]} if field["top_values"] else {})
            for field in content["fields"]
        ],
        "indexed_but_unseen": content["indexed_but_unseen"],
    }


SUMMARIES: dict[str, Summary] = {
    "qdrant_collection_create": _info,
    "qdrant_collection_info": _info,
    "qdrant_points_upsert": lambda c: {"status": c["status"]},
    "qdrant_points_delete": lambda c: {"status": c["status"]},
    "qdrant_query": _hits,
    "qdrant_alias_update": lambda c: {"applied": c["result"]},
    "qdrant_collection_copy": lambda c: c,
    "qdrant_payload_index_create": lambda c: {"status": c["status"]},
    "qdrant_payload_schema_infer": _profile,
    "qdrant_points_count": lambda c: {"count": c["count"]},
}


async def _step(server: MCPServer[None], tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        result = await server.call_tool(tool, arguments)
    except ToolError as exc:
        return {"tool": tool, "arguments": arguments, "ok": False, "error": str(exc)}
    assert isinstance(result, CallToolResult) and result.structured_content is not None, tool
    content = result.structured_content
    return {"tool": tool, "arguments": arguments, "ok": True, "result": SUMMARIES[tool](content)}


# --- the data ----------------------------------------------------------------------------------
# Hand-made 4-d vectors and token ids, small enough to read. Sparse indices stand for tokens:
# 1 password, 2 key, 3 invoice, 4 sso, 5 export, 6 delete, 7 account, 8 reset.
_ARTICLES = [
    (1, "Reset your password", [0.9, 0.1, 0.1, 0.0], {1: 1.0, 8: 1.0}),
    (2, "Rotate API keys", [0.1, 0.9, 0.1, 0.0], {2: 1.0, 8: 0.4}),
    (3, "Invoice and billing FAQ", [0.0, 0.1, 0.9, 0.1], {3: 1.0}),
    (4, "Set up single sign-on", [0.8, 0.3, 0.0, 0.3], {4: 1.0, 1: 0.3}),
    (5, "Export your data", [0.1, 0.1, 0.2, 0.9], {5: 1.0, 7: 0.3}),
    (6, "Delete your account", [0.3, 0.0, 0.1, 0.8], {6: 1.0, 7: 1.0, 1: 0.2}),
]


def _sparse(weights: dict[int, float]) -> dict[str, list[Any]]:
    return {"indices": list(weights), "values": list(weights.values())}


async def hybrid_search(server: MCPServer[None]) -> list[dict[str, Any]]:
    name = "demo_articles"
    dense_query = [0.85, 0.2, 0.0, 0.2]
    sparse_query = _sparse({1: 1.0, 8: 1.0})
    return [
        await _step(
            server,
            "qdrant_collection_create",
            {
                "collection_name": name,
                "vectors": {"dense": {"size": 4, "distance": "Cosine"}},
                "sparse_vectors": {"sparse": {}},
            },
        ),
        await _step(
            server,
            "qdrant_points_upsert",
            {
                "collection_name": name,
                "points": [
                    {
                        "id": point_id,
                        "vector": {"dense": dense, "sparse": _sparse(sparse)},
                        "payload": {"title": title},
                    }
                    for point_id, title, dense, sparse in _ARTICLES
                ],
            },
        ),
        await _step(
            server,
            "qdrant_query",
            {"collection_name": name, "query_vector": dense_query, "using": "dense", "limit": 3},
        ),
        await _step(
            server,
            "qdrant_query",
            {"collection_name": name, "query_vector": sparse_query, "using": "sparse", "limit": 3},
        ),
        await _step(
            server,
            "qdrant_query",
            {
                "collection_name": name,
                "fusion": "rrf",
                "prefetch": [
                    {"query_vector": dense_query, "using": "dense", "limit": 6},
                    {"query_vector": sparse_query, "using": "sparse", "limit": 6},
                ],
                "limit": 3,
            },
        ),
    ]


async def zero_downtime_reindex(server: MCPServer[None]) -> list[dict[str, Any]]:
    return [
        await _step(
            server,
            "qdrant_collection_create",
            {"collection_name": "demo_docs_v1", "vector_size": 2, "distance": "Cosine"},
        ),
        await _step(
            server,
            "qdrant_points_upsert",
            {
                "collection_name": "demo_docs_v1",
                "points": [
                    {"id": i, "vector": [1.0, i * 0.2], "payload": {"title": f"Article {i}"}}
                    for i in range(1, 5)
                ],
            },
        ),
        await _step(
            server,
            "qdrant_alias_update",
            {
                "operations": [
                    {"create_alias": {"collection_name": "demo_docs_v1", "alias_name": "demo_docs"}}
                ]
            },
        ),
        await _step(
            server,
            "qdrant_collection_create",
            {
                "collection_name": "demo_docs_v2",
                "vector_size": 2,
                "distance": "Euclid",
                "hnsw_config": {"m": 24},
            },
        ),
        await _step(
            server,
            "qdrant_collection_copy",
            {"source_collection": "demo_docs", "target_collection": "demo_docs_v2"},
        ),
        await _step(
            server,
            "qdrant_alias_update",
            {
                "operations": [
                    {"create_alias": {"collection_name": "demo_docs_v2", "alias_name": "demo_docs"}}
                ]
            },
        ),
        await _step(server, "qdrant_collection_info", {"collection_name": "demo_docs"}),
    ]


async def know_the_payload(server: MCPServer[None]) -> list[dict[str, Any]]:
    name = "demo_events"
    cities = ["ny", "sf", "ny", "sf"]
    return [
        await _step(
            server,
            "qdrant_collection_create",
            {"collection_name": name, "vector_size": 2, "distance": "Cosine"},
        ),
        await _step(
            server,
            "qdrant_points_upsert",
            {
                "collection_name": name,
                "points": [
                    {
                        "id": i,
                        "vector": [1.0, 0.0],
                        "payload": {
                            "city": city,
                            "price": 10.0 * i,
                            "tags": ["a", "b"],
                            "user id": f"u{i}",
                            "meta": {"owner": "ops"},
                        },
                    }
                    for i, city in enumerate(cities, start=1)
                ],
            },
        ),
        await _step(
            server,
            "qdrant_payload_index_create",
            {"collection_name": name, "field_name": "city", "field_schema": "keyword"},
        ),
        await _step(server, "qdrant_payload_schema_infer", {"collection_name": name}),
        await _step(
            server,
            "qdrant_points_count",
            {
                "collection_name": name,
                "count_filter": {"must": [{"key": '"user id"', "match": {"value": "u3"}}]},
            },
        ),
    ]


async def safety_rails(
    server: MCPServer[None], read_only_tools: int, all_tools: int
) -> list[dict[str, Any]]:
    name = "demo_safe"
    empty_filter = {"collection_name": name, "points_filter": {"must": []}}
    await _step(
        server,
        "qdrant_collection_create",
        {"collection_name": name, "vector_size": 2, "distance": "Cosine"},
    )
    await _step(
        server,
        "qdrant_points_upsert",
        {"collection_name": name, "points": [{"id": i, "vector": [1.0, 0.0]} for i in range(1, 5)]},
    )
    return [
        await _step(server, "qdrant_points_count", {"collection_name": name}),
        await _step(server, "qdrant_points_delete", empty_filter),
        await _step(server, "qdrant_points_count", {"collection_name": name}),
        {
            "method": "tools/list",
            "environment": {"QDRANT_MCP_READ_ONLY": "1"},
            "ok": True,
            "result": {"tools_visible": read_only_tools, "tools_in_full_server": all_tools},
        },
    ]


async def record() -> dict[str, Any]:
    settings = Settings.from_env(
        {"QDRANT_URL": QDRANT_URL, "QDRANT_MCP_TOOLSETS": ",".join(ALL_TOOLSETS)}
    )
    read_only = Settings.from_env(
        {
            "QDRANT_URL": QDRANT_URL,
            "QDRANT_MCP_TOOLSETS": ",".join(ALL_TOOLSETS),
            "QDRANT_MCP_READ_ONLY": "1",
        }
    )
    server = build_server(settings)
    all_tools = len(await server.list_tools())
    read_only_tools = len(await build_server(read_only).list_tools())

    client = AsyncQdrantClient(url=QDRANT_URL, timeout=15)
    try:
        await _cleanup(client)
        scenarios = [
            {"id": "hybrid-search", "steps": await hybrid_search(server)},
            {"id": "zero-downtime-reindex", "steps": await zero_downtime_reindex(server)},
            {"id": "know-the-payload", "steps": await know_the_payload(server)},
            {"id": "safety-rails", "steps": await safety_rails(server, read_only_tools, all_tools)},
        ]
    finally:
        await _cleanup(client)
        qdrant_version = (await client.info()).version
        await client.close()
    return {
        "recorded_with": {"mcp_qdrant": __version__, "qdrant": qdrant_version},
        "scenarios": scenarios,
    }


async def _cleanup(client: AsyncQdrantClient) -> None:
    # Deleting an alias that doesn't exist is a verified no-op, so this is safe to repeat.
    await client.update_collection_aliases(
        [DeleteAliasOperation(delete_alias=DeleteAlias(alias_name="demo_docs"))]
    )
    for name in DEMO_COLLECTIONS:
        await client.delete_collection(name)


def main() -> int:
    logging.disable(logging.INFO)  # the HTTP client and the registry log every call at INFO
    check_only = "--check" in sys.argv
    new_json = json.dumps(asyncio.run(record()), indent=2, ensure_ascii=False) + "\n"

    if check_only:
        current = OUTPUT_PATH.read_text() if OUTPUT_PATH.exists() else ""
        if new_json != current:
            print(
                "website/data/scenarios.generated.json is out of date. "
                "Run: uv run python scripts/record_scenarios.py (needs a Qdrant)"
            )
            return 1
        print("website/data/scenarios.generated.json is up to date.")
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(new_json)
    print("website/data/scenarios.generated.json recorded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
