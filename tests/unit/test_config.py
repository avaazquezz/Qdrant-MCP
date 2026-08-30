"""Unit tests for Settings.from_env: env var parsing and validation."""

from __future__ import annotations

import pytest

from mcp_qdrant.config import Settings


def test_defaults_with_empty_env() -> None:
    settings = Settings.from_env({})
    assert settings.qdrant_url is None
    assert settings.qdrant_local_path is None
    assert settings.read_only is False
    assert settings.transport == "stdio"
    assert settings.toolsets == ("core",)


def test_parses_multiple_toolsets() -> None:
    settings = Settings.from_env({"QDRANT_MCP_TOOLSETS": "core, search"})
    assert settings.toolsets == ("core", "search")


@pytest.mark.parametrize("value", ["1", "true", "True", "yes", "on"])
def test_read_only_truthy_values(value: str) -> None:
    settings = Settings.from_env({"QDRANT_MCP_READ_ONLY": value})
    assert settings.read_only is True


@pytest.mark.parametrize("value", ["0", "false", "", "off"])
def test_read_only_falsy_values(value: str) -> None:
    settings = Settings.from_env({"QDRANT_MCP_READ_ONLY": value})
    assert settings.read_only is False


def test_unknown_toolset_raises() -> None:
    with pytest.raises(ValueError, match="Unknown toolset"):
        Settings.from_env({"QDRANT_MCP_TOOLSETS": "bogus"})


def test_url_and_local_path_are_mutually_exclusive() -> None:
    with pytest.raises(ValueError, match="only one of"):
        Settings.from_env(
            {"QDRANT_URL": "http://localhost:6333", "QDRANT_LOCAL_PATH": "/tmp/qdrant"}
        )
