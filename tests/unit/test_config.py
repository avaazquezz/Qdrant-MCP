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


def test_streamable_http_without_shared_secret_raises() -> None:
    with pytest.raises(ValueError, match="QDRANT_MCP_SHARED_SECRET"):
        Settings.from_env({"QDRANT_MCP_TRANSPORT": "streamable-http"})


def test_streamable_http_with_shared_secret_is_valid() -> None:
    settings = Settings.from_env(
        {"QDRANT_MCP_TRANSPORT": "streamable-http", "QDRANT_MCP_SHARED_SECRET": "s3cr3t"}
    )
    assert settings.shared_secret == "s3cr3t"


def test_http_host_and_port_defaults_and_override() -> None:
    assert Settings.from_env({}).http_host == "127.0.0.1"
    assert Settings.from_env({}).http_port == 8000
    settings = Settings.from_env(
        {"QDRANT_MCP_HTTP_HOST": "0.0.0.0", "QDRANT_MCP_HTTP_PORT": "9000"}
    )
    assert settings.http_host == "0.0.0.0"
    assert settings.http_port == 9000


def test_byo_defaults_to_false() -> None:
    assert Settings.from_env({}).byo_qdrant is False


def test_byo_requires_streamable_http() -> None:
    with pytest.raises(ValueError, match="requires QDRANT_MCP_TRANSPORT=streamable-http"):
        Settings.from_env({"QDRANT_MCP_BYO": "1"})


def test_byo_is_incompatible_with_qdrant_url() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        Settings.from_env(
            {
                "QDRANT_MCP_BYO": "1",
                "QDRANT_MCP_TRANSPORT": "streamable-http",
                "QDRANT_URL": "http://localhost:6333",
            }
        )


def test_byo_is_incompatible_with_qdrant_local_path() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        Settings.from_env(
            {
                "QDRANT_MCP_BYO": "1",
                "QDRANT_MCP_TRANSPORT": "streamable-http",
                "QDRANT_LOCAL_PATH": "/tmp/qdrant",
            }
        )


def test_byo_does_not_require_shared_secret() -> None:
    settings = Settings.from_env({"QDRANT_MCP_BYO": "1", "QDRANT_MCP_TRANSPORT": "streamable-http"})
    assert settings.byo_qdrant is True
    assert settings.shared_secret is None


def test_byo_allows_optional_shared_secret() -> None:
    settings = Settings.from_env(
        {
            "QDRANT_MCP_BYO": "1",
            "QDRANT_MCP_TRANSPORT": "streamable-http",
            "QDRANT_MCP_SHARED_SECRET": "s3cr3t",
        }
    )
    assert settings.shared_secret == "s3cr3t"
