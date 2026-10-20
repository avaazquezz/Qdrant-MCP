"""Regenerates website/data/stats.generated.json: the figures the landing page quotes,
computed from the repository instead of typed into the page.

Everything here is derived: the version from pyproject.toml, tool counts from the live
registry, the number of tests from pytest's own collection, the release list from the
CHANGELOG headings. Nothing on the page that looks like a measurement is written by hand.

Run `uv run python scripts/gen_site_stats.py` to rewrite the file in place, or
`--check` (used in CI) to fail if it would change.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

from gen_tools_doc import collect_tool_rows

from mcp_qdrant.config import ALL_TOOLSETS, Settings
from mcp_qdrant.server import build_server

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "website" / "data" / "stats.generated.json"
_RELEASE_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
_COLLECTED = re.compile(r"(\d+) tests? collected")


def _count_lines(directory: Path) -> int:
    return sum(
        1
        for path in directory.rglob("*.py")
        for line in path.read_text().splitlines()
        if line.strip()
    )


def _collected_tests() -> int:
    """Number of tests pytest collects (integration tests included — collecting them
    does not need a Qdrant server)."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "--no-cov",
            "-p",
            "no:cacheprovider",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    match = _COLLECTED.search(result.stdout)
    if match is None:
        raise RuntimeError(f"could not read the collected-test count from:\n{result.stdout[-400:]}")
    return int(match.group(1))


async def _schema_kilobytes() -> dict[str, int]:
    """Size of the input schemas a client loads into the model's context, for the default
    toolset and for the whole catalog (what tests/unit/test_schemas.py budgets)."""

    async def total(toolsets: str) -> int:
        server = build_server(Settings.from_env({"QDRANT_MCP_TOOLSETS": toolsets}))
        return sum(len(json.dumps(tool.input_schema)) for tool in await server.list_tools())

    return {
        "core_schema_kb": round(await total("core") / 1000),
        "catalog_schema_kb": round(await total(",".join(ALL_TOOLSETS)) / 1000),
    }


def build_stats() -> dict[str, object]:
    rows = asyncio.run(collect_tool_rows())
    toolsets: dict[str, int] = {}
    for row in rows:
        toolsets[str(row["toolset"])] = toolsets.get(str(row["toolset"]), 0) + 1
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    releases = [
        {"version": version, "date": date}
        for version, date in _RELEASE_HEADING.findall((ROOT / "CHANGELOG.md").read_text())
    ]
    return {
        "version": project["version"],
        "tools": len(rows),
        "toolsets": toolsets,
        "read_only_tools": sum(1 for row in rows if row["read_only"]),
        "destructive_tools": sum(1 for row in rows if row["destructive"]),
        "tests": _collected_tests(),
        **asyncio.run(_schema_kilobytes()),
        "releases": releases,
        "source_lines": _count_lines(ROOT / "src" / "mcp_qdrant"),
        "test_lines": _count_lines(ROOT / "tests"),
    }


def main() -> int:
    check_only = "--check" in sys.argv
    new_json = json.dumps(build_stats(), indent=2, ensure_ascii=False) + "\n"

    if check_only:
        current = OUTPUT_PATH.read_text() if OUTPUT_PATH.exists() else ""
        if new_json != current:
            print(
                "website/data/stats.generated.json is out of date. "
                "Run: uv run python scripts/gen_site_stats.py"
            )
            return 1
        print("website/data/stats.generated.json is up to date.")
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(new_json)
    print("website/data/stats.generated.json regenerated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
