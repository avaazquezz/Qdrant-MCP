"""Unit tests for the server's guidance (Fase 21): instructions, prompts and tool titles."""

from __future__ import annotations

import asyncio
import itertools
import re

import pytest
from mcp.server import MCPServer

from mcp_qdrant.config import ALL_TOOLSETS, Settings, Toolset
from mcp_qdrant.server import build_server

TOOL_NAME = re.compile(r"\bqdrant_[a-z_]+\b")


def _server(
    toolsets: tuple[Toolset, ...] = ALL_TOOLSETS, read_only: bool = False
) -> MCPServer[None]:
    return build_server(Settings(toolsets=toolsets, read_only=read_only))


def _texts(server: MCPServer[None]) -> list[str]:
    """The instructions plus every prompt rendered with sample arguments."""
    texts = [server.instructions or ""]
    for prompt in asyncio.run(server.list_prompts()):
        args = {arg.name: "x" for arg in prompt.arguments or []}
        rendered = asyncio.run(server.get_prompt(prompt.name, args))
        texts += [message.content.text for message in rendered.messages]  # type: ignore[union-attr]
    return texts


CONFIGS = [
    (toolsets, read_only)
    for size in (1, 2, len(ALL_TOOLSETS))
    for toolsets in itertools.combinations(ALL_TOOLSETS, size)
    for read_only in (False, True)
]


@pytest.mark.parametrize(("toolsets", "read_only"), CONFIGS)
def test_guidance_never_names_a_tool_this_server_lacks(
    toolsets: tuple[Toolset, ...], read_only: bool
) -> None:
    server = _server(toolsets, read_only)
    registered = {tool.name for tool in asyncio.run(server.list_tools())}
    named = {name for text in _texts(server) for name in TOOL_NAME.findall(text)}
    assert named <= registered, named - registered


def test_instructions_stay_short() -> None:
    """They go into the model's context in every conversation (verified in Claude Code)."""
    for toolsets, read_only in CONFIGS:
        assert len((_server(toolsets, read_only).instructions or "").split()) <= 150


def test_read_only_says_so_and_registers_no_workflow() -> None:
    server = _server(read_only=True)
    assert "read-only" in (server.instructions or "")
    assert asyncio.run(server.list_prompts()) == []


@pytest.mark.parametrize(
    ("toolsets", "prompts"),
    [
        (("core",), set()),
        (("core", "admin"), {"tune_search", "zero_downtime_reindex"}),
        (("core", "payload"), {"text_search_setup"}),
        (ALL_TOOLSETS, {"tune_search", "zero_downtime_reindex", "text_search_setup"}),
    ],
)
def test_prompts_need_their_toolsets(toolsets: tuple[Toolset, ...], prompts: set[str]) -> None:
    assert {p.name for p in asyncio.run(_server(toolsets).list_prompts())} == prompts


def test_prompts_render_their_arguments() -> None:
    server = _server()
    rendered = asyncio.run(
        server.get_prompt("text_search_setup", {"collection": "boe", "language": "spanish"})
    )
    text = rendered.messages[0].content.text  # type: ignore[union-attr]
    assert "`boe`" in text and '"language": "spanish"' in text
    reindex = asyncio.run(
        server.get_prompt("zero_downtime_reindex", {"collection": "docs", "alias": "live"})
    )
    assert "`docs_v2`" in reindex.messages[0].content.text  # type: ignore[union-attr]


def test_every_tool_has_a_title() -> None:
    tools = asyncio.run(_server().list_tools())
    assert all(tool.title and tool.title == tool.annotations.title for tool in tools)  # type: ignore[union-attr]
