"""Stderr-only logging setup.

MCP's stdio transport treats stdout as the JSON-RPC wire; anything else
written there corrupts every message after it. This is the single place
allowed to touch the root logger's handlers, and it hard-codes
stream=sys.stderr — called before MCPServer() is constructed, so the SDK's
own internal logging configuration (which also defaults to stderr, but we
don't want two configurations racing) finds handlers already in place.
"""

from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger to write exclusively to stderr.

    Idempotent: clears existing handlers first, so calling this twice (e.g.
    once per test) never accumulates duplicate log lines.
    """
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
    root.setLevel(level)
