# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.1] - 2026-08-30

### Added
- Project scaffold: `pyproject.toml`, `uv` dependency management, ruff/mypy/pytest/pre-commit config.
- `MCPServer` instance wired to a shared `AsyncQdrantClient` (`QDRANT_URL` / `QDRANT_API_KEY` / `QDRANT_LOCAL_PATH`), with retrying connectivity via `tenacity`.
- Toolset registration mechanism (`core`, `search`, `payload`, `snapshots`, `admin`, `observability`), filterable via `QDRANT_MCP_TOOLSETS` (default: `core` only).
- Read-only guardrail: `QDRANT_MCP_READ_ONLY` blocks registration of any tool annotated `destructiveHint=true`.
- Stderr-only logging, safe for the `stdio` transport.
- `qdrant_health_check` tool: end-to-end connectivity smoke test against the configured Qdrant instance.
- CI: lint, typecheck, and unit + integration tests (against a real `qdrant/qdrant:v1.13.6` service) on every PR.
