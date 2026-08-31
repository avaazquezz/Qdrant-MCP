# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-08-31

### Added
- `<!-- mcp-name: io.github.avaazquezz/mcp-qdrant -->` marker in README.md — required by the [MCP Registry](https://registry.modelcontextprotocol.io) to verify PyPI package ownership before this server can be listed there. `v1.0.0` was already published without it, so this couldn't be a docs-only change — it needed a new PyPI release for the marker to actually be present in the published package's README.

## [1.0.0] - 2026-08-31

Fase 7 — hardening and distribution. No new tools (catalog is final at 49). This is
the last phase before a stable v1.0.0.

### Added
- Shared-secret authentication for the `streamable-http` transport: `QDRANT_MCP_SHARED_SECRET` (required whenever `QDRANT_MCP_TRANSPORT=streamable-http` — startup fails loudly otherwise), a `SharedSecretMiddleware` checking `Authorization: Bearer <secret>`, and `QDRANT_MCP_HTTP_HOST`/`QDRANT_MCP_HTTP_PORT` to bind for a real deployment. Not in the original roadmap — added after verifying hands-on, against a real Claude.ai account and a real public tunnel, that this server had no authentication at all in `streamable-http` mode, and that `Authorization: Bearer` is one of the two header names Claude.ai's remote-connector UI accepts without needing Anthropic's manual approval.
- `Dockerfile` (multi-stage, `uv`-based) + `.github/workflows/docker.yml`, pushing to `ghcr.io/avaazquezz/qdrant-mcp` on version tags.
- `.github/workflows/publish.yml`: builds and publishes to PyPI via `uv publish --trusted-publishing`, triggered by version tags. Requires a one-time "Trusted Publishing" registration on pypi.org (external, not automatable from here).
- `manifest.json` (repo root) + `.mcpbignore` + `.github/workflows/mcpb.yml`: a Claude Desktop `.mcpb` bundle using the MCPB spec's `"uv"` server type (manifest v0.4+) — `uv` resolves `pyproject.toml`'s dependencies on the user's machine, no vendoring, no local Python required beforehand. Validated with the official `mcpb` CLI (`validate`/`pack`); packed bundle is ~136 KB.
- `scripts/gen_tools_doc.py`: regenerates the README tools table from the live tool registry (`list_tools()`, the same view a real MCP client sees) between `<!-- TOOLS_TABLE_START/END -->` markers. `--check` mode wired into CI's `lint` job.
- README "Configuration" section with copy-pasteable `claude_desktop_config.json`/`.mcp.json` snippets and the verified Claude.ai remote-connector setup steps.
- Launch checklist for v1.0.0 in `ROADMAP.md` (PyPI trusted publishing setup, first tag, `modelcontextprotocol/servers` + Smithery submissions) — external actions, tracked but not executed automatically.

### Changed
- README tool descriptions switched from third-person prose to the tools' own imperative-mood docstring summaries, since the table is now generated verbatim from `list_tools()` rather than hand-edited — a few docstrings were reworded slightly (line-wrap points only, no behavior change) to avoid awkward auto-extracted summaries.
- `uvicorn` added as an explicit direct dependency (was already pulled in transitively by `mcp`, but `cli.py` now imports it directly to serve `streamable-http` with the auth middleware).

## [0.6.0] - 2026-08-31

Fase 5 (`aliases-cluster-admin`) was discarded before implementation — see `ROADMAP.md`
— so this release follows `0.4.0` directly, no `0.5.0`.

### Added
- New `observability` toolset (opt-in via `QDRANT_MCP_TOOLSETS=core,observability`): `qdrant_telemetry`, `qdrant_metrics_prometheus`, `qdrant_quotas_get`, `_set`, `qdrant_issues_list`, `_clear`.

### Removed from the original roadmap catalog
- `qdrant_write_protection_get`/`_set` are not implemented: verified hands-on that neither `qdrant-client==1.19.0`'s high-level client nor any of its 10 low-level REST API classes have anything related to locks/write-protection/read-only at the server level — no substitute concept exists (unlike Fase 2's `search`, fully consolidated into `query_points`).

### Design notes
- `qdrant_metrics_prometheus` returns the scrape URL, not the metrics content: verified hands-on that the underlying `client.http.service_api.metrics()` always calls `response.json()` regardless of type, and crashes against the real Prometheus plaintext exposition format it returns. A scraper needs to `GET` that URL itself anyway — same reasoning as Fase 4's snapshot download tools.
- This is the first toolset whose primary mechanism is the low-level REST layer (`client.http.<api>_api.<method>`) instead of `AsyncQdrantClient`'s high-level convenience methods — none of telemetry/quotas/issues is wrapped there (the one high-level exception, `client.cluster_telemetry()`, is distributed-cluster telemetry, out of scope since Fase 5 was discarded). `call_qdrant` works unchanged against these calls; they just return the full response envelope (`result`/`status`/`time`), unwrapped by hand.

## [0.4.0] - 2026-08-31

### Added
- New `snapshots` toolset (opt-in via `QDRANT_MCP_TOOLSETS=core,snapshots`): `qdrant_snapshot_create`, `_list`, `_delete`, `_recover`, `_download` (per collection), and `qdrant_storage_snapshot_create`, `_list`, `_delete`, `_download` (whole storage). No `qdrant_storage_snapshot_recover` — restoring a full-storage snapshot happens with the server stopped, pointed at the file at startup, not via a live API call.

### Design note: snapshot download returns a URL, not the file
Verified hands-on that `qdrant-client==1.19.0`'s only "download a snapshot" method (`client.http.snapshots_api.get_snapshot`/`get_full_snapshot`, not even exposed on the high-level client) always calls `response.json()` on the response — it crashes with `UnicodeDecodeError` against a real (binary) snapshot file. There is also no reasonable way to carry a multi-megabyte-to-gigabyte binary blob through an MCP tool result. So `qdrant_snapshot_download`/`qdrant_storage_snapshot_download` confirm the snapshot exists (via `list_snapshots`/`list_full_snapshots`, fully within the SDK) and return its descriptor plus the REST URL it's served at — fetch it yourself (`curl`, etc.). Verified hands-on that this URL is directly reusable as `qdrant_snapshot_recover`'s `location` (full round-trip: create → download → mutate → recover → data restored), as long as that URL is reachable **from the Qdrant server itself** — which may differ from the URL used to reach it from outside when Qdrant runs behind Docker port-remapping or a reverse proxy.

### Changed
- `src/mcp_qdrant/server.py`: `snapshots_tools.register()` is the first tool module to need more than `(registry, client)` — it also takes the configured `QDRANT_URL`, to build the download URLs above. No other module's `register()` signature changed.

## [0.3.0] - 2026-08-31

### Changed — minimum supported Qdrant server raised to v1.19.0
CI's Qdrant service image moves from `v1.13.6` to `v1.19.0` (matching the pinned
`qdrant-client==1.19.0`), and this is now the documented minimum self-hosted server
version for this project. Reason: `qdrant_collection_vector_create`/`_delete` (new in
this release) rely on the `create_vector_name`/`delete_vector_name` endpoint, verified
hands-on to 404 on Qdrant `v1.13.6` and `v1.15.1` and to work on `v1.19.0` — there was
no way to ship those two tools without this bump. As a side effect, the
client/server version-compatibility `UserWarning` documented since Fase 0 is gone.

### Added
- New `payload` toolset (opt-in via `QDRANT_MCP_TOOLSETS=core,payload`, or combined with `search`):
  - `qdrant_payload_set`, `_overwrite`, `_delete`, `_clear`, `_facet` — payload value CRUD and facet counting.
  - `qdrant_payload_index_create`, `_delete` — payload indexing, from a simple type name to a fully-tuned index (tokenizer, tenant/principal hints, on-disk placement), reusing `qdrant-client`'s own 9 index-param models directly.
  - `qdrant_points_batch_update` — runs upsert/delete/set-payload/overwrite-payload/delete-payload/clear-payload/update-vectors/delete-vectors atomically in one call, reusing `qdrant-client`'s own tagged operation types.
  - `qdrant_vectors_update`, `_delete` — replace or remove the vector(s) of existing points by id.
  - `qdrant_collection_vector_create`, `_delete` — add or remove a named vector (dense or sparse) on a collection that already has points, without touching them. Requires the newer Qdrant server floor above.
- Shared `mcp_qdrant.tools.points_shared.build_points_selector` — the "exactly one of `ids`/`points_filter`" validation, now reused by five tools across `points.py`/`payload.py`/`vectors.py`.

### Changed
- `qdrant_collection_create` (toolset unchanged: `core`) extended with: `vectors` (named/multi-vector, each a full `VectorParams` — supports `multivector_config` for ColBERT-style multi-vectors and per-vector `quantization_config`), `sparse_vectors`, `quantization_config` (scalar/product/binary), `strict_mode_config`, `metadata`. `vector_size`/`distance` (the Fase 1 shape) still work unchanged — exactly one of `vector_size` or `vectors` is required.
- `qdrant_collection_update` (toolset unchanged: `core`) extended with `vectors_config`, `quantization_config` (including `"disabled"` to turn it off), `sparse_vectors_config`, `strict_mode_config`. **Note**: `vectors_config`/`sparse_vectors_config` here only *adjust* a named vector that already exists — they cannot add a new one (verified: Qdrant rejects that with "Not existing vector name"); use `qdrant_collection_vector_create` for that.
- `qdrant_points_delete` (Fase 1): internals now call the shared `build_points_selector` instead of its own inline copy of the same check — no behavior change.

### Removed from the original roadmap catalog
None — unlike Fase 2, this phase ships full coverage of everything `ROADMAP.md` listed for it.

## [0.2.0] - 2026-08-31

### Added
- New `search` toolset (opt-in via `QDRANT_MCP_TOOLSETS=core,search`): `qdrant_query_batch`, `qdrant_query_groups`, `qdrant_recommend`, `_batch`, `_groups`, `qdrant_discover`, `_batch`, `qdrant_distance_matrix_pairs`, `_offsets` — all built on the unified Query API (`query_points`/`query_batch_points`/`query_points_groups`/`search_matrix_*`).
- Shared `mcp_qdrant.tools.query_shared` helpers (`build_query_value`, `build_prefetch_list`, `build_lookup_from`) reused by `qdrant_query` and every `search` toolset tool that needs a query/prefetch/lookup shape.

### Changed
- `qdrant_query` (toolset unchanged: `core`) extended with `fusion` (RRF/DBSF hybrid search over `prefetch` stages), `using` (named-vector selection), and `lookup_from` (resolve the query vector from a point id in another collection). `query_vector` is now optional (required only when `fusion` isn't used) and additionally accepts a point id, not just a literal vector — fully backward compatible with existing calls.

### Removed from the original roadmap catalog
- `qdrant_search`/`_batch`/`_groups` (originally planned as "legacy" tools) are not implemented: verified that `qdrant-client==1.19.0` (pinned) no longer exposes `search`/`search_batch`/`search_groups`/`recommend`/`recommend_batch`/`recommend_groups`/`discover`/`discover_batch` at all — not even in its low-level REST layer — having fully consolidated them into the unified Query API. Wrapping them would mean duplicating `qdrant_query` with zero real capability behind it, or bypassing the pinned SDK with raw HTTP. `qdrant_recommend`/`_batch`/`_groups` and `qdrant_discover`/`_batch` are unaffected — they're real query types (`RecommendQuery`/`DiscoverQuery`) built on `query_points`.

## [0.1.0] - 2026-08-30

### Added
- Full collection CRUD: `qdrant_collection_create`, `_list`, `_info`, `_update`, `_delete`, `_exists`.
- Full points CRUD: `qdrant_points_upsert`, `_get`, `_delete`, `_scroll`, `_count`.
- `qdrant_query`: vector similarity search with an optional payload filter and limit (modern unified Query API, `query_points`).
- Shared `call_qdrant()` helper: retries transport-level failures (same policy as `qdrant_health_check`'s ping) and translates a surviving Qdrant error into a `ToolError` carrying Qdrant's own message, instead of a generic crash.
- Rich per-tool descriptions with examples, shipped from this phase (not deferred to Fase 7).

### Fixed
- `QDRANT_MCP_READ_ONLY` now blocks any tool not marked `read_only_hint=true`, not only `destructive_hint=true` ones — closes a gap where a mutating-but-non-destructive tool (e.g. creating a collection) could register under read-only mode.

### Changed
- `qdrant_client.py`: the retry policy used by `ping` is now the named, reusable `qdrant_retry` decorator (same parameters, no behavior change).

## [0.0.1] - 2026-08-30

### Added
- Project scaffold: `pyproject.toml`, `uv` dependency management, ruff/mypy/pytest/pre-commit config.
- `MCPServer` instance wired to a shared `AsyncQdrantClient` (`QDRANT_URL` / `QDRANT_API_KEY` / `QDRANT_LOCAL_PATH`), with retrying connectivity via `tenacity`.
- Toolset registration mechanism (`core`, `search`, `payload`, `snapshots`, `admin`, `observability`), filterable via `QDRANT_MCP_TOOLSETS` (default: `core` only).
- Read-only guardrail: `QDRANT_MCP_READ_ONLY` blocks registration of any tool annotated `destructiveHint=true`.
- Stderr-only logging, safe for the `stdio` transport.
- `qdrant_health_check` tool: end-to-end connectivity smoke test against the configured Qdrant instance.
- CI: lint, typecheck, and unit + integration tests (against a real `qdrant/qdrant:v1.13.6` service) on every PR.
