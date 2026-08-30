"""Proves the one property that matters for stdio transport: logging never touches stdout."""

from __future__ import annotations

import logging

import pytest

from mcp_qdrant.logging_setup import configure_logging


def test_logging_writes_only_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging()
    logging.getLogger("mcp_qdrant.test").warning("hello from a tool")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "hello from a tool" in captured.err


def test_configure_logging_is_idempotent(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging()
    configure_logging()
    logging.getLogger("mcp_qdrant.test").warning("only once")
    captured = capsys.readouterr()
    assert captured.err.count("only once") == 1
