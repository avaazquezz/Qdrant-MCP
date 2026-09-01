"""Regenerates website/data/tools.generated.json from the live tool registry —
the same collect_tool_rows() data scripts/gen_tools_doc.py uses for the
README table, just with the full (untruncated) description.

Run `uv run python scripts/gen_tools_json.py` to rewrite the file in place,
or `--check` (used in CI) to fail if it would change.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from gen_tools_doc import collect_tool_rows

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "website" / "data" / "tools.generated.json"


def main() -> int:
    check_only = "--check" in sys.argv
    rows = asyncio.run(collect_tool_rows())
    new_json = json.dumps(rows, indent=2, ensure_ascii=False) + "\n"

    if check_only:
        current = OUTPUT_PATH.read_text() if OUTPUT_PATH.exists() else ""
        if new_json != current:
            print(
                "website/data/tools.generated.json is out of date. "
                "Run: uv run python scripts/gen_tools_json.py"
            )
            return 1
        print("website/data/tools.generated.json is up to date.")
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(new_json)
    print("website/data/tools.generated.json regenerated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
