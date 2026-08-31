"""The `observability` toolset (Fase 6): telemetry, Prometheus metrics,
quotas, and issues — health/ops info about the Qdrant server itself, not
about any particular collection's data.

Every tool here calls `client.http.<api>_api.<method>(...)` — the low-level
REST layer — instead of `AsyncQdrantClient`'s high-level convenience
methods, because none of this is wrapped there (the one exception,
`client.cluster_telemetry()`, is distributed-cluster telemetry, a
different endpoint that doesn't apply to a single-node deployment and is
out of scope here, consistent with Fase 5 being discarded). Verified
hands-on that `call_qdrant` still works unchanged against these low-level
calls — they raise the same `UnexpectedResponse`/`ResponseHandlingException`
as the high-level client. Unlike the high-level wrapper, these return the
full response envelope (`result`/`status`/`time`/`usage`), not the
already-unwrapped domain object — `_unwrap` pulls `result` out.

`qdrant_write_protection_get`/`_set` from the original roadmap catalog are
not implemented: verified hands-on that neither the high-level client nor
any of its low-level REST API classes have anything related to
locks/write-protection/read-only at the server level in this client
version — no substitute concept exists to fall back on (unlike Fase 2's
`search`, fully consolidated into `query_points`).

`qdrant_metrics_prometheus` does not fetch metrics content: verified
hands-on that `client.http.service_api.metrics()` always calls
`response.json()` regardless of the declared return type, and crashes with
`JSONDecodeError` against the real Prometheus plaintext exposition format
it returns. A Prometheus scraper needs to `GET` that URL itself anyway, so
this tool returns the scrape URL instead — same reasoning, and the same
`_require_qdrant_url` guard, as Fase 4's snapshot download tools.
"""

from __future__ import annotations

from typing import Any, cast

from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import QuotaConfig, QuotaStatus, TelemetryData

from mcp_qdrant.tools.errors import call_qdrant
from mcp_qdrant.tools.registry import ToolRegistry

_TELEMETRY_ANNOTATIONS = ToolAnnotations(
    title="Get Qdrant server telemetry",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_METRICS_ANNOTATIONS = ToolAnnotations(
    title="Get the Qdrant Prometheus metrics URL",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_QUOTAS_GET_ANNOTATIONS = ToolAnnotations(
    title="Get Qdrant server quotas",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_QUOTAS_SET_ANNOTATIONS = ToolAnnotations(
    title="Set Qdrant server quotas",
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_ISSUES_LIST_ANNOTATIONS = ToolAnnotations(
    title="List Qdrant server issues",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_ISSUES_CLEAR_ANNOTATIONS = ToolAnnotations(
    title="Clear Qdrant server issues",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)


class MetricsUrlInfo(BaseModel):
    url: str


def _unwrap[T](result: T | None) -> T:
    assert result is not None
    return result


def _require_qdrant_url(qdrant_url: str | None) -> str:
    if qdrant_url is None:
        raise ToolError(
            "This requires QDRANT_URL (remote mode); this server is configured with "
            "QDRANT_LOCAL_PATH, which has no HTTP endpoint to serve it from."
        )
    return qdrant_url


def register(registry: ToolRegistry, client: AsyncQdrantClient, qdrant_url: str | None) -> None:
    async def qdrant_telemetry(details_level: int | None = None) -> TelemetryData:
        """Server-wide telemetry: build info, per-collection stats, request
        counters, memory and hardware usage. Not tied to any one collection.

        Example: {}
        """
        # The generated stub types this as plain `int` despite defaulting to
        # None and accepting it fine at runtime — codegen quirk, not a real
        # constraint (verified hands-on).
        response = await call_qdrant(
            lambda: client.http.service_api.telemetry(details_level=cast(int, details_level))
        )
        return _unwrap(response.result)

    async def qdrant_metrics_prometheus() -> MetricsUrlInfo:
        """Return the URL where Qdrant serves Prometheus-format metrics —
        this tool does not fetch the metrics themselves (they're plain
        text, not JSON); point your Prometheus scraper at the returned
        `url` instead.

        Example: {}
        """
        url = _require_qdrant_url(qdrant_url)
        return MetricsUrlInfo(url=f"{url}/metrics")

    async def qdrant_quotas_get() -> QuotaStatus:
        """Current server-wide resource quotas (memory/disk limits) and
        actual usage.

        Example: {}
        """
        response = await call_qdrant(lambda: client.http.quotas_api.get_quotas())
        return _unwrap(response.result)

    async def qdrant_quotas_set(
        enabled: bool | None = None,
        max_resident_memory_percent: int | None = None,
        max_disk_usage_percent: int | None = None,
        release_margin_percent: int | None = None,
    ) -> bool:
        """Update server-wide resource quotas. Only the fields you pass are
        changed; omitted ones keep their current value.

        Example: {"enabled": true, "max_resident_memory_percent": 90}
        """
        quota_config = QuotaConfig(
            enabled=enabled,
            max_resident_memory_percent=max_resident_memory_percent,
            max_disk_usage_percent=max_disk_usage_percent,
            release_margin_percent=release_margin_percent,
        )
        response = await call_qdrant(
            lambda: client.http.quotas_api.update_quotas(quota_config=quota_config)
        )
        return _unwrap(response.result)

    async def qdrant_issues_list() -> dict[str, Any]:
        """List the issues Qdrant has detected about its own configuration
        (e.g. a heavily-filtered field with no payload index). **API Beta**
        in Qdrant itself — the exact shape can change without notice, so
        this is returned as-is rather than forced into a fixed schema.

        Example: {}
        """
        response = await call_qdrant(lambda: client.http.beta_api.get_issues())
        result = response.get("result") if isinstance(response, dict) else None
        return result if isinstance(result, dict) else {}

    async def qdrant_issues_clear() -> bool:
        """Clear all accumulated issues.

        Example: {}
        """
        response = await call_qdrant(lambda: client.http.beta_api.clear_issues())
        return _unwrap(response.result)

    registry.register(qdrant_telemetry, toolset="observability", annotations=_TELEMETRY_ANNOTATIONS)
    registry.register(
        qdrant_metrics_prometheus, toolset="observability", annotations=_METRICS_ANNOTATIONS
    )
    registry.register(
        qdrant_quotas_get, toolset="observability", annotations=_QUOTAS_GET_ANNOTATIONS
    )
    registry.register(
        qdrant_quotas_set, toolset="observability", annotations=_QUOTAS_SET_ANNOTATIONS
    )
    registry.register(
        qdrant_issues_list, toolset="observability", annotations=_ISSUES_LIST_ANNOTATIONS
    )
    registry.register(
        qdrant_issues_clear, toolset="observability", annotations=_ISSUES_CLEAR_ANNOTATIONS
    )
