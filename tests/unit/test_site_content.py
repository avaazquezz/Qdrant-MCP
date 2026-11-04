"""The landing promises that every test it cites exists (website/content/log.ts: "every `tests`
entry is a test that exists"). Renaming a test used to break that promise silently — two did
when Qdrant 1.20 changed the behavior they pinned. This keeps the page honest."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "website" / "content"


def _defined(name: str, file: Path) -> bool:
    return file.is_file() and re.search(rf"def {re.escape(name)}\b", file.read_text()) is not None


def test_every_test_the_engineering_log_cites_exists_in_its_file() -> None:
    log = (CONTENT / "log.ts").read_text()
    cited = re.findall(r"name: '(test_\w+)',\s*file: '([^']+)'", log)
    assert cited, "the parser found no cited tests: has log.ts changed shape?"
    missing = [(name, file) for name, file in cited if not _defined(name, ROOT / file)]
    assert missing == []


def test_every_test_named_in_the_page_copy_exists() -> None:
    # Test names, not file paths such as tests/unit/test_schemas.py.
    names = set(re.findall(r"(?<![/\w])test_\w+\b(?!\.py)", (CONTENT / "copy.ts").read_text()))
    tests = [p.read_text() for p in (ROOT / "tests").rglob("test_*.py")]
    missing = [n for n in names if not any(re.search(rf"def {n}\b", t) for t in tests)]
    assert missing == []
