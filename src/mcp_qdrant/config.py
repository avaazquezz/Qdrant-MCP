"""Environment-driven runtime configuration for mcp_qdrant.

All external configuration enters here and only here: Settings.from_env()
reads os.environ once at startup and validates it with Pydantic so a
misconfigured deployment fails loudly before the server starts serving
tool calls, instead of failing obscurely on the first tool call.
"""

from __future__ import annotations

import os
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

Transport = Literal["stdio", "streamable-http"]
Toolset = Literal["core", "search", "payload", "snapshots", "admin", "observability"]

ALL_TOOLSETS: tuple[Toolset, ...] = (
    "core",
    "search",
    "payload",
    "snapshots",
    "admin",
    "observability",
)
DEFAULT_TOOLSETS: tuple[Toolset, ...] = ("core",)
# Largest number of points/hits one tool call may ask for. Each result carries its
# payload (and vectors, if requested) into the model's context, so an unbounded
# `limit` is a way to flood it by accident.
DEFAULT_MAX_LIMIT = 1000
# The cap can't go below what the tools' own defaults ask for, or a call with no
# arguments beyond the required ones would be refused: the largest default request
# is 30 results (`limit` 10 × `group_size` 3, or `sample` 10 × `limit` 3 on the
# distance matrices, or three batch items of 10). A test calls every tool with only
# its required arguments at this minimum, so a new default that exceeds it fails there.
MIN_MAX_LIMIT = 30


class Settings(BaseModel):
    """Validated process configuration, built once from environment variables."""

    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_local_path: str | None = None
    read_only: bool = False
    transport: Transport = "stdio"
    toolsets: tuple[Toolset, ...] = DEFAULT_TOOLSETS
    shared_secret: str | None = None
    http_host: str = "127.0.0.1"
    http_port: int = 8000
    max_limit: Annotated[int, Field(ge=MIN_MAX_LIMIT)] = DEFAULT_MAX_LIMIT

    @model_validator(mode="after")
    def _check_single_connection_target(self) -> Settings:
        if self.qdrant_url and self.qdrant_local_path:
            raise ValueError("Set only one of QDRANT_URL or QDRANT_LOCAL_PATH, not both.")
        return self

    @model_validator(mode="after")
    def _require_shared_secret_for_streamable_http(self) -> Settings:
        # Verified hands-on (a real public tunnel + Claude.ai's own connector
        # UI) that an unauthenticated streamable-http server is trivially
        # usable by anyone with the URL — refuse to start that way silently.
        if self.transport == "streamable-http" and not self.shared_secret:
            raise ValueError(
                "QDRANT_MCP_SHARED_SECRET is required when "
                "QDRANT_MCP_TRANSPORT=streamable-http, to avoid serving an "
                "unauthenticated endpoint over the network."
            )
        return self

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        e = env if env is not None else dict(os.environ)
        # A leftover flag from a v1.1.x deployment must not be silently ignored:
        # the server would start in a different mode than the operator expects.
        if _parse_bool(e.get("QDRANT_MCP_BYO")):
            raise ValueError(
                "QDRANT_MCP_BYO was removed in v2.0.0 (bring-your-own-Qdrant mode no "
                "longer exists). Unset it and configure QDRANT_URL or QDRANT_LOCAL_PATH."
            )
        raw_toolsets = e.get("QDRANT_MCP_TOOLSETS", "core")
        toolsets = tuple(t.strip() for t in raw_toolsets.split(",") if t.strip())
        unknown = sorted(set(toolsets) - set(ALL_TOOLSETS))
        if unknown:
            raise ValueError(
                f"Unknown toolset(s) in QDRANT_MCP_TOOLSETS: {unknown}. "
                f"Valid values: {ALL_TOOLSETS}."
            )
        return cls(
            qdrant_url=e.get("QDRANT_URL") or None,
            qdrant_api_key=e.get("QDRANT_API_KEY") or None,
            qdrant_local_path=e.get("QDRANT_LOCAL_PATH") or None,
            read_only=_parse_bool(e.get("QDRANT_MCP_READ_ONLY")),
            transport=e.get("QDRANT_MCP_TRANSPORT", "stdio"),  # type: ignore[arg-type]
            toolsets=toolsets,  # type: ignore[arg-type]
            shared_secret=e.get("QDRANT_MCP_SHARED_SECRET") or None,
            http_host=e.get("QDRANT_MCP_HTTP_HOST", "127.0.0.1"),
            http_port=int(e.get("QDRANT_MCP_HTTP_PORT", "8000")),
            max_limit=_parse_max_limit(e.get("QDRANT_MCP_MAX_LIMIT")),
        )


def _parse_max_limit(value: str | None) -> int:
    if value is None or not value.strip():
        return DEFAULT_MAX_LIMIT
    try:
        return int(value)
    except ValueError:
        raise ValueError(
            f"QDRANT_MCP_MAX_LIMIT must be an integer of at least {MIN_MAX_LIMIT} (so every "
            f"tool's default arguments fit), got {value!r}."
        ) from None


def _parse_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}
