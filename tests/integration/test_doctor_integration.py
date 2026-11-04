"""`qdrant_collection_doctor` against a real Qdrant: what it reports on a small collection, and
proof that every fix it emits is accepted as is by the real tool it names (the alias name aside,
which is a placeholder). The doctor isn't wired into `build_server` here, so it runs on its own
server; `build_server` only executes the fixes."""

from __future__ import annotations

import json
import os
import random
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from mcp.server import MCPServer
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    CollectionStatus,
    Distance,
    PointStruct,
    TextIndexParams,
    TextScoringParams,
    TextScoringType,
    VectorParams,
)

from mcp_qdrant.config import ALL_TOOLSETS, Settings
from mcp_qdrant.server import build_server
from mcp_qdrant.tools import doctor as doctor_tools
from mcp_qdrant.tools.doctor import ALIAS_PLACEHOLDER, DoctorFinding, DoctorFix, DoctorReport
from mcp_qdrant.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration

URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class Env:
    def __init__(self, client: AsyncQdrantClient, name: str) -> None:
        self.client = client
        self.name = name
        self.fixes = build_server(Settings(qdrant_url=URL, toolsets=ALL_TOOLSETS))
        self.doctor: MCPServer[None] = MCPServer(name="doctor")
        registry = ToolRegistry(self.doctor, enabled_toolsets=("admin",), read_only=True)
        doctor_tools.register(registry, client)

    async def report(self) -> DoctorReport:
        result = await _call(
            self.doctor, "qdrant_collection_doctor", {"collection_name": self.name}
        )
        return DoctorReport.model_validate(result)

    async def apply(self, fix: DoctorFix | None, alias: str | None = None) -> Any:
        """Run a fix through the real tool, its arguments as JSON as a client receives them,
        with the alias placeholder (if any) replaced by `alias`."""
        assert fix is not None
        arguments = json.dumps(fix.arguments)
        if alias is not None:
            arguments = arguments.replace(json.dumps(ALIAS_PLACEHOLDER), json.dumps(alias))
        return await _call(self.fixes, fix.tool, json.loads(arguments))


@pytest.fixture
async def env() -> AsyncIterator[Env]:
    client = AsyncQdrantClient(url=URL, timeout=30)
    name = f"mcp-test-doctor-{uuid.uuid4().hex[:8]}"
    try:
        yield Env(client, name)
    finally:
        await client.delete_collection(name)  # also removes the aliases pointing to it
        await client.close()


async def _call(server: MCPServer[None], tool: str, args: dict[str, Any]) -> Any:
    result = await server.call_tool(tool, args)
    assert isinstance(result, CallToolResult) and not result.is_error, result
    return result.structured_content


def _rules(report: DoctorReport) -> set[str]:
    return {finding.rule for finding in report.findings}


def _finding(report: DoctorReport, rule: str, severity: str) -> DoctorFinding:
    [finding] = [f for f in report.findings if (f.rule, f.severity) == (rule, severity)]
    return finding


async def test_small_collection_is_unindexed_and_unaliased_until_aliased(env: Env) -> None:
    await env.client.create_collection(
        env.name, vectors_config=VectorParams(size=64, distance=Distance.COSINE)
    )
    points = [PointStruct(id=i, vector=[random.random() for _ in range(64)]) for i in range(500)]
    await env.client.upsert(env.name, points, wait=True)

    report = await env.report()
    assert {"unindexed", "aliases"} <= _rules(report)
    assert report.checked == ["status", "unindexed", "memory", "aliases"]
    unindexed = _finding(report, "unindexed", "info")
    assert unindexed.evidence["indexed_vectors_count"] == 0
    assert unindexed.evidence["points_count"] == 500

    aliases = _finding(report, "aliases", "info")
    assert await env.apply(aliases.fix, alias=f"{env.name}-live") == {"result": True}
    live = await env.client.get_collection_aliases(env.name)
    assert [a.alias_name for a in live.aliases] == [f"{env.name}-live"]

    assert "aliases" not in _rules(await env.report())
    # Through the alias itself, Qdrant lists no aliases for that name; the doctor mustn't care.
    through_alias = DoctorReport.model_validate(
        await _call(env.doctor, "qdrant_collection_doctor", {"collection_name": f"{env.name}-live"})
    )
    assert through_alias.points_count == 500
    assert "aliases" not in _rules(through_alias)


async def test_grey_and_memory_fixes_are_accepted_as_is(env: Env) -> None:
    """A grey status and 1 GiB of vectors can't be produced on demand, so these two fixes come
    from the rules run on the real collection's info with that one value changed."""
    await env.client.create_collection(
        env.name, vectors_config=VectorParams(size=256, distance=Distance.COSINE)
    )
    info = await env.client.get_collection(env.name)

    grey = doctor_tools._status(env.name, info.model_copy(update={"status": CollectionStatus.GREY}))
    assert grey is not None and grey.severity == "warning"
    await env.apply(grey.fix)

    memory = doctor_tools._memory(env.name, info.model_copy(update={"points_count": 1 << 20}))
    assert memory is not None
    await env.apply(memory.fix)
    applied = (await env.client.get_collection(env.name)).config
    assert applied.quantization_config is not None
    assert isinstance(applied.params.vectors, VectorParams)
    assert applied.params.vectors.memory == "cold"  # the originals left RAM


async def test_text_contract_fixes_clear_their_findings(env: Env) -> None:
    await env.client.create_collection(
        env.name,
        vectors_config={"dense": VectorParams(size=384, distance=Distance.COSINE)},
        # Declared through raw metadata: `qdrant_collection_update` refuses a model for a vector
        # the collection doesn't have, so this state only comes from outside this server.
        metadata={"mcp_qdrant": {"text_field": "body", "models": {"gone": MODEL}}},
    )

    report = await env.report()
    assert "text_contract" in report.checked
    stale = _finding(report, "text_contract", "error")
    assert stale.evidence["vector"] == "gone"
    no_bm25 = _finding(report, "text_contract", "info")

    await env.apply(stale.fix)
    await env.apply(no_bm25.fix)

    report = await env.report()
    assert "text_contract" in report.checked
    assert "text_contract" not in _rules(report)
    # `scoring: true` comes back as `{"type": "bm25"}`, which the rule must accept.
    index = (await env.client.get_collection(env.name)).payload_schema["body"]
    assert isinstance(index.params, TextIndexParams)
    assert index.params.scoring == TextScoringParams(type=TextScoringType.BM25)
