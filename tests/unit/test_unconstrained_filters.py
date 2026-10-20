"""A filter with no conditions selects every point, so a tool that deletes or
changes points by filter must refuse it. Verified against a real Qdrant: `{}`,
`{"must": []}` and `{"should": []}` as a delete selector each removed every point
of the collection — a model that builds its condition list dynamically and ends up
with an empty one would wipe the data."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Filter, MinShould, UpdateResult, UpdateStatus

from mcp_qdrant.tools import payload as payload_tools
from mcp_qdrant.tools import points as points_tools
from mcp_qdrant.tools import vectors as vectors_tools
from mcp_qdrant.tools.points_shared import filter_has_no_conditions
from mcp_qdrant.tools.registry import ToolRegistry

_REAL_CONDITION = {"key": "city", "match": {"value": "ny"}}

# Every way of writing "no conditions" that the real model accepts.
EMPTY_FILTERS: list[dict[str, Any]] = [
    {},
    {"must": []},
    {"should": []},
    {"must_not": []},
    {"must": None},
    {"must": [], "should": [], "must_not": []},
    {"min_should": {"conditions": [], "min_count": 1}},
    {"must": [], "min_should": {"conditions": [], "min_count": 2}},
]
CONSTRAINED_FILTERS: list[dict[str, Any]] = [
    {"must": [_REAL_CONDITION]},
    {"must": _REAL_CONDITION},  # a single condition, not a list
    {"should": [_REAL_CONDITION]},
    {"must_not": [_REAL_CONDITION]},
    {"min_should": {"conditions": [_REAL_CONDITION], "min_count": 1}},
    {"must": [], "should": [_REAL_CONDITION]},  # one empty list next to a real one
]


def _build() -> tuple[MCPServer[None], AsyncMock]:
    mock = AsyncMock()
    mock.delete.return_value = UpdateResult(operation_id=1, status=UpdateStatus.COMPLETED)
    mock.set_payload.return_value = mock.delete.return_value
    mock.overwrite_payload.return_value = mock.delete.return_value
    mock.delete_payload.return_value = mock.delete.return_value
    mock.clear_payload.return_value = mock.delete.return_value
    mock.delete_vectors.return_value = mock.delete.return_value
    mock.batch_update_points.return_value = [mock.delete.return_value]
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core", "payload"), read_only=False)
    client = cast(AsyncQdrantClient, mock)
    points_tools.register(registry, client)
    payload_tools.register(registry, client)
    vectors_tools.register(registry, client)
    return server, mock


# tool, client method, the other required arguments
_FILTER_TOOLS: list[tuple[str, str, dict[str, Any]]] = [
    ("qdrant_points_delete", "delete", {}),
    ("qdrant_payload_set", "set_payload", {"payload": {"a": 1}}),
    ("qdrant_payload_overwrite", "overwrite_payload", {"payload": {"a": 1}}),
    ("qdrant_payload_delete", "delete_payload", {"keys": ["a"]}),
    ("qdrant_payload_clear", "clear_payload", {}),
    ("qdrant_vectors_delete", "delete_vectors", {"vector_names": ["dense"]}),
]


@pytest.mark.parametrize(("tool", "method", "extra"), _FILTER_TOOLS)
@pytest.mark.parametrize("empty", EMPTY_FILTERS)
async def test_a_filter_with_no_conditions_is_refused_before_touching_qdrant(
    tool: str, method: str, extra: dict[str, Any], empty: dict[str, Any]
) -> None:
    server, mock = _build()

    with pytest.raises(ToolError, match="no conditions"):
        await server.call_tool(tool, {"collection_name": "docs", "points_filter": empty, **extra})

    getattr(mock, method).assert_not_awaited()


@pytest.mark.parametrize(("tool", "method", "extra"), _FILTER_TOOLS)
@pytest.mark.parametrize("filter_", CONSTRAINED_FILTERS)
async def test_a_filter_with_a_real_condition_still_goes_through(
    tool: str, method: str, extra: dict[str, Any], filter_: dict[str, Any]
) -> None:
    server, mock = _build()

    await server.call_tool(tool, {"collection_name": "docs", "points_filter": filter_, **extra})

    getattr(mock, method).assert_awaited_once()


@pytest.mark.parametrize(("tool", "method", "extra"), _FILTER_TOOLS)
async def test_selecting_by_ids_is_unaffected(
    tool: str, method: str, extra: dict[str, Any]
) -> None:
    server, mock = _build()

    await server.call_tool(tool, {"collection_name": "docs", "ids": [1, 2], **extra})

    getattr(mock, method).assert_awaited_once()


def test_the_emptiness_check_agrees_with_the_cases_above() -> None:
    for sample in EMPTY_FILTERS:
        assert filter_has_no_conditions(Filter.model_validate(sample)), sample
    for sample in CONSTRAINED_FILTERS:
        assert not filter_has_no_conditions(Filter.model_validate(sample)), sample
    assert filter_has_no_conditions(Filter(min_should=MinShould(conditions=[], min_count=1)))


# --- the same hole through qdrant_points_batch_update -------------------------------------

_BATCH_WITH_FILTER: list[tuple[str, dict[str, Any]]] = [
    ("delete", {"delete": {"filter": {}}}),
    ("delete", {"delete": {"filter": {"must": []}}}),
    ("set_payload", {"set_payload": {"payload": {"a": 1}, "filter": {}}}),
    ("overwrite_payload", {"overwrite_payload": {"payload": {"a": 1}, "filter": {"should": []}}}),
    ("delete_payload", {"delete_payload": {"keys": ["a"], "filter": {}}}),
    ("clear_payload", {"clear_payload": {"filter": {}}}),
    ("delete_vectors", {"delete_vectors": {"vector": ["dense"], "filter": {}}}),
]


@pytest.mark.parametrize(("name", "operation"), _BATCH_WITH_FILTER)
async def test_a_batch_operation_with_an_empty_filter_is_refused_and_names_it(
    name: str, operation: dict[str, Any]
) -> None:
    server, mock = _build()

    with pytest.raises(ToolError) as excinfo:
        await server.call_tool(
            "qdrant_points_batch_update",
            {
                "collection_name": "docs",
                "operations": [
                    {"upsert": {"points": [{"id": 1, "vector": [0.1]}]}},
                    operation,
                ],
            },
        )

    assert f"operations[1].{name}.filter" in str(excinfo.value)
    mock.batch_update_points.assert_not_awaited()  # nothing at all is sent, not even the upsert


async def test_a_batch_with_a_real_filter_or_with_ids_goes_through() -> None:
    server, mock = _build()

    await server.call_tool(
        "qdrant_points_batch_update",
        {
            "collection_name": "docs",
            "operations": [
                {"delete": {"filter": {"must": [_REAL_CONDITION]}}},
                {"delete": {"points": [1, 2]}},
                {"set_payload": {"payload": {"a": 1}, "points": [3]}},
                {"upsert": {"points": [{"id": 4, "vector": [0.1]}]}},
            ],
        },
    )

    mock.batch_update_points.assert_awaited_once()


async def test_the_batch_tool_no_longer_claims_to_be_atomic() -> None:
    """Verified against Qdrant: a valid operation followed by a failing one leaves the
    first applied. The tool must not promise otherwise."""
    server, _ = _build()

    (tool,) = [t for t in await server.list_tools() if t.name == "qdrant_points_batch_update"]

    assert "atomic" not in (tool.description or "").lower().replace("not all-or-nothing", "")
    assert "not all-or-nothing" in (tool.description or "").lower()
    assert tool.annotations is not None and "atomically" not in (tool.annotations.title or "")
