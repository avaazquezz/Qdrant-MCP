"""Regenerates the tools table in README.md from the live tool registry —
the same `list_tools()` data a real MCP client sees, not a re-parse of each
tool's Pydantic schema by hand.

Run `uv run python scripts/gen_tools_doc.py` to rewrite README.md in place,
or `--check` (used in CI) to fail if README.md would change.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp_types import Tool

from mcp_qdrant.config import ALL_TOOLSETS, Settings, Toolset
from mcp_qdrant.server import build_server

README_PATH = Path(__file__).resolve().parent.parent / "README.md"
TABLE_START = "<!-- TOOLS_TABLE_START -->"
TABLE_END = "<!-- TOOLS_TABLE_END -->"


_ABBREVIATIONS = ("e.g", "i.e", "etc")


def _summary(description: str | None) -> str:
    """First sentence of the tool's docstring, whitespace collapsed.

    Splits on ". ", but keeps merging the next chunk back in while the
    sentence-so-far ends in a known abbreviation (`e.g.`, `i.e.`, `etc.`) —
    otherwise those false sentence boundaries would truncate the summary
    mid-thought.
    """
    if not description:
        return ""
    first_paragraph = description.strip().split("\n\n", 1)[0]
    parts = " ".join(first_paragraph.split()).split(". ")
    sentence = parts[0]
    for part in parts[1:]:
        last_word = sentence.rstrip(".").split()[-1].lower()
        if not any(last_word.endswith(abbr) for abbr in _ABBREVIATIONS):
            break
        sentence += f". {part}"
    return f"{sentence.rstrip('.')}."


def _mark(value: bool | None) -> str:
    return "✅" if value else "❌"


async def _tools_for_toolset(toolset: Toolset) -> list[Tool]:
    settings = Settings(qdrant_local_path=":memory:", toolsets=(toolset,))
    server = build_server(settings)
    return await server.list_tools()


async def _collect_rows() -> list[str]:
    toolset_by_name: dict[str, Toolset] = {}
    for toolset in ALL_TOOLSETS:
        for tool in await _tools_for_toolset(toolset):
            toolset_by_name[tool.name] = toolset

    settings = Settings(qdrant_local_path=":memory:", toolsets=ALL_TOOLSETS)
    server = build_server(settings)
    all_tools = await server.list_tools()

    rows = []
    for tool in all_tools:
        annotations = tool.annotations
        rows.append(
            f"| `{tool.name}` | `{toolset_by_name[tool.name]}` "
            f"| {_mark(annotations.read_only_hint if annotations else None)} "
            f"| {_mark(annotations.destructive_hint if annotations else None)} "
            f"| {_mark(annotations.idempotent_hint if annotations else None)} "
            f"| {_summary(tool.description)} |"
        )
    return rows


def _render_table(rows: list[str]) -> str:
    header = "| Tool | Toolset | Read-only | Destructive | Idempotent | Description |"
    separator = "|---|---|---|---|---|---|"
    return "\n".join([TABLE_START, header, separator, *rows, TABLE_END])


def main() -> int:
    check_only = "--check" in sys.argv
    rows = asyncio.run(_collect_rows())
    new_table = _render_table(rows)

    readme = README_PATH.read_text()
    start = readme.index(TABLE_START)
    end = readme.index(TABLE_END) + len(TABLE_END)
    new_readme = readme[:start] + new_table + readme[end:]

    if check_only:
        if new_readme != readme:
            print(
                "README.md tools table is out of date. Run: uv run python scripts/gen_tools_doc.py"
            )
            return 1
        print("README.md tools table is up to date.")
        return 0

    README_PATH.write_text(new_readme)
    print("README.md tools table regenerated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
