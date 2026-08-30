# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
