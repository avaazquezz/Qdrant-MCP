"""The `core` toolset: baseline tools every deployment registers by default."""

from __future__ import annotations

import logging

from mcp_types import ToolAnnotations
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient

from mcp_qdrant.qdrant_client import ping
from mcp_qdrant.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

_HEALTH_CHECK_ANNOTATIONS = ToolAnnotations(
    title="Qdrant health check",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,  # talks to an external Qdrant instance
)


class HealthCheckResult(BaseModel):
    """Outcome of a live round-trip to the configured Qdrant instance."""

    ok: bool
    collection_count: int | None = None
    error: str | None = None


def register(registry: ToolRegistry, client: AsyncQdrantClient) -> None:
    async def qdrant_health_check() -> HealthCheckResult:
        """Confirm the configured Qdrant instance is reachable and responding.

        Never raises to the caller: a health check that raises on the exact
        condition it exists to detect defeats its own purpose. Connection
        failures are logged and reported in the result's ok/error fields
        instead, so a client renders them without a tool-call error round-trip.
        """
        try:
            count = await ping(client)
        except Exception as exc:
            logger.warning("qdrant_health_check failed: %s", exc)
            return HealthCheckResult(ok=False, error=str(exc))
        return HealthCheckResult(ok=True, collection_count=count)

    registry.register(qdrant_health_check, toolset="core", annotations=_HEALTH_CHECK_ANNOTATIONS)
