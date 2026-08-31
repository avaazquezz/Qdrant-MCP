# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
