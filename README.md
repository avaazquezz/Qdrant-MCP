# Qdrant MCP

<!-- mcp-name: io.github.avaazquezz/mcp-qdrant -->

[![PyPI version](https://img.shields.io/pypi/v/mcp-qdrant.svg)](https://pypi.org/project/mcp-qdrant/)
[![CI](https://github.com/avaazquezz/Qdrant-MCP/actions/workflows/ci.yml/badge.svg)](https://github.com/avaazquezz/Qdrant-MCP/actions/workflows/ci.yml)
[![Python versions](https://img.shields.io/pypi/pyversions/mcp-qdrant.svg)](https://pypi.org/project/mcp-qdrant/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**A Model Context Protocol (MCP) server that exposes the full [Qdrant](https://qdrant.tech)
vector database API as tools** — collection management, advanced hybrid search, payload and
vector editing, snapshots, and server observability. Not just `store`/`find`.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Requirements](#requirements)
- [Installation](#installation)
  - [PyPI](#pypi)
  - [Docker](#docker)
  - [Claude Desktop bundle (`.mcpb`)](#claude-desktop-bundle-mcpb)
- [Quick Start](#quick-start)
- [Connecting to Claude](#connecting-to-claude)
  - [Claude Desktop / Claude Code (local, stdio)](#claude-desktop--claude-code-local-stdio)
  - [Remote (streamable-http)](#remote-streamable-http)
  - [Bring your own Qdrant (`QDRANT_MCP_BYO`)](#bring-your-own-qdrant-qdrant_mcp_byo)
- [Configuration Reference](#configuration-reference)
- [Available Tools](#available-tools)
- [Read-Only Mode](#read-only-mode)
- [Architecture](#architecture)
- [Security](#security)
- [Development](#development)
- [Versioning & Changelog](#versioning--changelog)
- [License](#license)

## Overview

Qdrant MCP is a thin [MCP](https://modelcontextprotocol.io) server that wraps the Qdrant API
one-to-one: it registers a tool per Qdrant operation, validates the input with Pydantic, calls
the official `qdrant-client` SDK, and returns the result. It never generates embeddings, never
parses documents, and never decides how to chunk text — **it is not a RAG system**, on purpose.
Whatever an LLM client wants to store or query, it brings its own vectors.

That focus is also what sets it apart from the [official Qdrant MCP
server](https://github.com/qdrant/mcp-server-qdrant), which exposes exactly two tools
(`store`/`find`) and does embed documents for you. This server covers the rest of Qdrant's
surface — everything under collections, points, search, payload, indexing, snapshots, and
observability — so an LLM client can manage a Qdrant deployment end to end, not just push and
pull memories through a narrow interface.

See [ROADMAP.md](ROADMAP.md) for the full phase-by-phase design history, including every
finding that shaped a decision (in Spanish).

## Key Features

- **Full collection & point lifecycle** — create/update/delete collections, CRUD on points,
  scrolling, counting.
- **Every Qdrant search mode** — plain vector search, hybrid search (RRF/DBSF fusion with
  prefetch stages), grouped queries, recommend, discover, and pairwise distance matrices.
- **Payload & vector editing** — set/overwrite/delete/clear payload, payload indexes, facet
  counting, named (dense/sparse) vector management, atomic batch operations.
- **Snapshots** — per-collection and full-storage backup/restore.
- **Observability** — telemetry, Prometheus metrics endpoint, resource quotas, self-diagnosed
  issues.
- **Opt-in tool surface** — tools are grouped into toolsets you enable explicitly, so a client
  isn't handed 60+ overlapping tools by default.
- **Read-only guard** — one flag removes every mutating tool from the registry entirely.
- **Bring-your-own-Qdrant mode** — run a public endpoint with no database of your own; every
  caller supplies their own Qdrant, isolated by construction, protected by an SSRF guard.
- **Resilient by default** — every Qdrant call goes through retry-with-backoff and returns
  Qdrant's own error message on failure, never a generic exception.

## Requirements

- **Python 3.12+**
- **Qdrant server v1.19.0 or newer.** Two tools
  (`qdrant_collection_vector_create`/`qdrant_collection_vector_delete`) depend on an endpoint
  that returns `404` on older Qdrant servers (verified against v1.13.6 and v1.15.1) — everything
  else works on older versions, but v1.19.0+ is the only version this project tests against.

## Installation

### PyPI

```bash
# Run without installing (recommended for Claude Desktop/Code configs)
uvx mcp-qdrant

# Or install into your environment
pip install mcp-qdrant
```

### Docker

```bash
docker run --rm -p 8000:8000 \
  -e QDRANT_URL=http://host.docker.internal:6333 \
  -e QDRANT_MCP_TRANSPORT=streamable-http \
  -e QDRANT_MCP_HTTP_HOST=0.0.0.0 \
  -e QDRANT_MCP_SHARED_SECRET=<a long random secret> \
  ghcr.io/avaazquezz/qdrant-mcp:latest
```

The image only makes sense with `streamable-http` — `stdio` needs a client to own the process's
stdin/stdout directly, which a detached container can't provide. The server binds
`127.0.0.1` by default, so `QDRANT_MCP_HTTP_HOST=0.0.0.0` is required for the port to be
reachable from outside the container. Images are published on every tagged release as
`{version}`, `{major}.{minor}`, and `latest`.

### Claude Desktop bundle (`.mcpb`)

Download `mcp-qdrant.mcpb` from the [latest release](https://github.com/avaazquezz/Qdrant-MCP/releases)
and double-click it. Claude Desktop installs the server via `uv` (resolving dependencies on your
machine, no Python installation required) and prompts for Qdrant URL, API key, local path,
toolsets, and read-only mode through its own settings form — no JSON to edit.

## Quick Start

Point the server at a local Qdrant instance over `stdio` and confirm it's reachable:

```bash
QDRANT_URL=http://localhost:6333 mcp-qdrant
```

Once connected from an MCP client, a typical first exchange looks like:

1. **`qdrant_health_check`** — confirms the configured Qdrant instance is reachable before
   doing anything else.
2. **`qdrant_collection_create`** — `{"collection_name": "docs", "vector_size": 4, "distance": "Cosine"}`.
3. **`qdrant_points_upsert`** — `{"collection_name": "docs", "points": [{"id": 1, "vector": [0.1, 0.2, 0.3, 0.4], "payload": {"title": "hello"}}]}`.
4. **`qdrant_query`** — `{"collection_name": "docs", "query_vector": [0.1, 0.2, 0.3, 0.4], "limit": 5}`.

The full parameter shape of every tool is described in its own MCP schema — an LLM client reads
those directly via `tools/list`; the table in [Available Tools](#available-tools) below is a
human-readable summary of the same data.

## Connecting to Claude

### Claude Desktop / Claude Code (local, `stdio`)

`claude_desktop_config.json` (Claude Desktop) or `.mcp.json` (Claude Code):

```json
{
  "mcpServers": {
    "qdrant": {
      "command": "uvx",
      "args": ["mcp-qdrant"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_MCP_TOOLSETS": "core,search"
      }
    }
  }
}
```

Or use the `.mcpb` bundle described in [Installation](#claude-desktop-bundle-mcpb) — same
result, no JSON to edit.

### Remote (`streamable-http`)

For a server reachable over the network (e.g. added as a custom connector in Claude.ai) with a
single, fixed backing Qdrant. `QDRANT_MCP_SHARED_SECRET` is **required** in this mode — the
server refuses to start as `streamable-http` without one, to avoid serving an unauthenticated
endpoint over the network (verified hands-on: an open `streamable-http` server is trivially
usable by anyone with the URL).

```bash
QDRANT_URL=http://localhost:6333 \
QDRANT_MCP_TRANSPORT=streamable-http \
QDRANT_MCP_HTTP_HOST=0.0.0.0 \
QDRANT_MCP_SHARED_SECRET=<a long random secret> \
mcp-qdrant
```

In Claude.ai (**Customize → Connectors → Add custom connector**, verified hands-on against a
real account): enter the server's HTTPS URL, then on the detected authentication screen choose
**"None"** and add a **Request header** — `Authorization` → `Bearer <the same secret>`.
(`Authorization` is used here because it's one of the two header names Claude.ai's
custom-connector UI accepts without requiring Anthropic's manual approval of a custom name.)

### Bring your own Qdrant (`QDRANT_MCP_BYO`)

A `streamable-http` deployment can run with **no backing Qdrant of its own** — every caller
supplies their *own* Qdrant instance (their own Qdrant Cloud account, their company's
self-hosted Qdrant, whatever) per request, instead of using one the operator hosts and pays for.
Isolation between callers is automatic — each one talks to their own database — so there's no
shared secret, no per-user account, and no data at rest on this server.

```bash
QDRANT_MCP_BYO=1 \
QDRANT_MCP_TRANSPORT=streamable-http \
QDRANT_MCP_HTTP_HOST=0.0.0.0 \
mcp-qdrant
```

Two request headers, reused for a different purpose than their name suggests — verified
hands-on that Claude.ai's custom-connector "Request headers" UI rejects made-up header names
outright unless Anthropic has approved them, so this reuses two pre-approved ones instead of
inventing `X-Qdrant-Url`/`X-Qdrant-Api-Key`:

- `Authorization` (**required**) — your Qdrant URL, e.g. `https://xyz.cloud.qdrant.io:6333`.
  Sent verbatim, no `Bearer` prefix (unlike the personal-instance mode above, which uses the
  same header for a shared secret).
- `x-api-key` (optional) — your Qdrant API key, if your instance needs one.

In Claude.ai: **Add custom connector** → authentication **"None"** → add both as **Request
headers**. Your Qdrant must be reachable from the public internet — see
[Security](#security) for what the SSRF guard rejects.

**How it works, under the hood:** every tool resolves its Qdrant client lazily, at call time,
rather than once at startup. In BYO mode that client is a `BYOQdrantClientProxy` that reads the
real `AsyncQdrantClient` from a `contextvars.ContextVar`, set per-request by the auth
middleware — so none of the tool implementations need to know BYO mode exists. Clients are
pooled in a bounded LRU cache (256 entries, keyed by URL + API key) so repeat callers don't pay
a fresh TLS handshake on every call, with a 15-second grace period before an evicted client is
closed so an in-flight request is never cut off mid-call.

#### Recommended setup: one MCP deployment, one Qdrant per project

This is the most common way to run this project: deploy the MCP **once**, in BYO mode, as a
long-lived service — then, for each new project, spin up your own Qdrant and point a connector
at it, without ever touching the MCP deployment again.

1. **Deploy the MCP once**, self-hosted (e.g. Docker behind a reverse proxy with TLS), in BYO
   mode as shown above. This never changes between projects.
2. **Per project, run your own Qdrant** with `docker-compose`, protected with its own API key
   ([`QDRANT__SERVICE__API_KEY`](https://qdrant.tech/documentation/guides/security/) — Qdrant's
   own auth, unrelated to this server):

   ```yaml
   services:
     qdrant:
       image: qdrant/qdrant:latest
       restart: unless-stopped
       environment:
         QDRANT__SERVICE__API_KEY: ${QDRANT_API_KEY}
       volumes:
         - ./qdrant_storage:/qdrant/storage
   ```

   All data for that project lives in `./qdrant_storage`, on your own server — the MCP
   deployment never stores or sees it beyond relaying each request.
3. **Expose that Qdrant under its own public HTTPS domain** (e.g. via Traefik/Let's Encrypt) —
   the SSRF guard rejects private/internal addresses, so it must be reachable from the public
   internet, not just from inside your server's Docker network.
4. **Add one connector per project**, pointing at the same MCP deployment but with different
   headers:
   - **Claude.ai**: a separate custom connector per project — `Authorization` = that project's
     Qdrant URL, `x-api-key` = its API key.
   - **Claude Code** (`.mcp.json`, remote HTTP server with custom headers):
     ```json
     {
       "mcpServers": {
         "qdrant-project-x": {
           "type": "http",
           "url": "https://your-mcp.example.com/mcp",
           "headers": {
             "Authorization": "https://qdrant-project-x.example.com",
             "x-api-key": "${QDRANT_PROJECT_X_API_KEY}"
           }
         }
       }
     }
     ```

Adding a project is then just a new `docker-compose up` for its Qdrant plus a new connector —
the MCP deployment itself is never redeployed or restarted.

## Configuration Reference

All configuration is via environment variables, read once at startup — a misconfiguration fails
immediately instead of surfacing later as a confusing tool error.

| Variable | Default | Required | Purpose |
|---|---|---|---|
| `QDRANT_URL` | — | No¹ | URL of your Qdrant instance, e.g. `http://localhost:6333` or a Qdrant Cloud URL. |
| `QDRANT_API_KEY` | — | No | API key for `QDRANT_URL`, if your instance requires one. |
| `QDRANT_LOCAL_PATH` | — | No¹ | Path to an embedded/on-disk Qdrant instance, instead of a URL. |
| `QDRANT_MCP_READ_ONLY` | `false` | No | Removes every tool not marked read-only from the registry. See [Read-Only Mode](#read-only-mode). |
| `QDRANT_MCP_TRANSPORT` | `stdio` | No | `stdio` (local, for Claude Desktop/Code) or `streamable-http` (network). |
| `QDRANT_MCP_TOOLSETS` | `core` | No | Comma-separated list of toolsets to register. See [Available Tools](#available-tools). |
| `QDRANT_MCP_SHARED_SECRET` | — | Required for `streamable-http` unless BYO² | Bearer token clients must send in the `Authorization` header. |
| `QDRANT_MCP_HTTP_HOST` | `127.0.0.1` | No | Bind host for `streamable-http`. Use `0.0.0.0` in a container. |
| `QDRANT_MCP_HTTP_PORT` | `8000` | No | Bind port for `streamable-http`. |
| `QDRANT_MCP_BYO` | `false` | No | Enables [bring-your-own-Qdrant mode](#bring-your-own-qdrant-qdrant_mcp_byo). |

¹ `QDRANT_URL` and `QDRANT_LOCAL_PATH` are mutually exclusive; if neither is set, the client
falls back to the `qdrant-client` SDK's own default of `localhost:6333`.
² In BYO mode the shared secret is optional — it adds an extra anti-bot gate on top of the
per-caller isolation BYO already provides, rather than protecting shared data. BYO mode also
requires `QDRANT_MCP_TRANSPORT=streamable-http` and is mutually exclusive with
`QDRANT_URL`/`QDRANT_LOCAL_PATH` (there is nothing "backing" to point at).

## Available Tools

Tools are grouped into **toolsets**, enabled via `QDRANT_MCP_TOOLSETS` (comma-separated). Only
`core` is enabled by default — the rest are explicit opt-ins, so a client isn't handed every
tool at once:

- **`core`** — collection and point CRUD, plus `qdrant_query` and the `qdrant_health_check`
  smoke test. Enough for a fully working MCP on its own.
- **`search`** — everything beyond plain vector search: batched/grouped queries, recommend,
  discover, and pairwise distance matrices.
- **`payload`** — payload editing and indexing, named-vector management, atomic batch point
  operations.
- **`snapshots`** — collection and full-storage backup/restore.
- **`observability`** — telemetry, metrics, quotas, and self-diagnosed issues.
- **`admin`** is a reserved toolset name with no registered tools — cluster/shard
  administration was scoped out (see [ROADMAP.md](ROADMAP.md), Fase 5): its most useful
  capability, real resharding, only exists on Qdrant Cloud, and the rest only matters for a
  distributed deployment. Setting `QDRANT_MCP_TOOLSETS=admin` is valid but registers nothing.

The table below is generated directly from the live tool registry — run
`uv run python scripts/gen_tools_doc.py` after adding or changing a tool to keep it in sync
(CI fails the build if it drifts).

<!-- TOOLS_TABLE_START -->
| Tool | Toolset | Read-only | Destructive | Idempotent | Description |
|---|---|---|---|---|---|
| `qdrant_health_check` | `core` | ✅ | ❌ | ✅ | Confirm the configured Qdrant instance is reachable and responding. |
| `qdrant_collection_create` | `core` | ❌ | ❌ | ❌ | Create a collection: either a single unnamed vector (`vector_size` + `distance`), or one or more named vectors (`vectors`, each a full `VectorParams` — size, distance, and optionally its own `multivector_config` for ColBERT-style multi-vectors or `quantization_config`) — exactly one of the two. |
| `qdrant_collection_list` | `core` | ✅ | ❌ | ✅ | List every collection name in the configured Qdrant instance. |
| `qdrant_collection_info` | `core` | ✅ | ❌ | ✅ | Return full config and status of one collection. |
| `qdrant_collection_update` | `core` | ❌ | ❌ | ✅ | Update optimizer/HNSW/collection/vector params on an existing collection. |
| `qdrant_collection_delete` | `core` | ❌ | ✅ | ✅ | Delete a collection and all its points; a no-op if it doesn't exist. |
| `qdrant_collection_exists` | `core` | ✅ | ❌ | ✅ | Check whether a collection exists, without raising if it doesn't. |
| `qdrant_points_upsert` | `core` | ❌ | ✅ | ✅ | Insert or replace points (id + vector + payload) in a collection. |
| `qdrant_points_get` | `core` | ✅ | ❌ | ✅ | Retrieve points by id; unknown ids are simply omitted, not an error. |
| `qdrant_points_delete` | `core` | ❌ | ✅ | ✅ | Delete points by id list or by payload filter — exactly one of the two. |
| `qdrant_points_scroll` | `core` | ✅ | ❌ | ✅ | Page through all points in a collection, optionally filtered. |
| `qdrant_points_count` | `core` | ✅ | ❌ | ✅ | Count points in a collection, optionally matching a filter. |
| `qdrant_query` | `core` | ✅ | ❌ | ✅ | Vector similarity search, with optional hybrid search over multiple prefetch stages. |
| `qdrant_query_batch` | `search` | ✅ | ❌ | ✅ | Run multiple independent queries against one collection in a single round trip — same query shapes as `qdrant_query` (plain vector or fusion+prefetch hybrid search), one per list item. |
| `qdrant_query_groups` | `search` | ✅ | ❌ | ✅ | Vector query grouped by a payload field, up to `group_size` hits per group — e.g. the best-matching chunks per source document. |
| `qdrant_recommend` | `search` | ✅ | ❌ | ✅ | Find points similar to a set of positive examples and dissimilar to a set of negative ones (vectors or point ids) — Qdrant's recommendation API. |
| `qdrant_recommend_batch` | `search` | ✅ | ❌ | ✅ | Run multiple independent recommend queries against one collection in a single round trip. |
| `qdrant_recommend_groups` | `search` | ✅ | ❌ | ✅ | Recommend query grouped by a payload field, up to `group_size` hits per group. |
| `qdrant_discover` | `search` | ✅ | ❌ | ✅ | Rank points by how well they fit a target within positive/negative context pairs (vectors or point ids) — Qdrant's discovery search, a finer-grained alternative to recommend. |
| `qdrant_discover_batch` | `search` | ✅ | ❌ | ✅ | Run multiple independent discover queries against one collection in a single round trip. |
| `qdrant_distance_matrix_pairs` | `search` | ✅ | ❌ | ✅ | Pairwise distance matrix between a random sample of points: for each of `sample` points, its `limit` closest neighbors among that same sample — returned as a flat list of (a, b, score) pairs. |
| `qdrant_distance_matrix_offsets` | `search` | ✅ | ❌ | ✅ | Same distance matrix as `qdrant_distance_matrix_pairs`, in a column-oriented shape (offsets into a shared id list + a parallel score array) — more compact for large samples. |
| `qdrant_payload_set` | `payload` | ❌ | ❌ | ✅ | Merge fields into the payload of selected points — exactly one of `ids`/`points_filter`. |
| `qdrant_payload_overwrite` | `payload` | ❌ | ✅ | ✅ | Replace the entire payload of selected points with `payload` — exactly one of `ids`/`points_filter`. |
| `qdrant_payload_delete` | `payload` | ❌ | ✅ | ✅ | Delete specific payload keys from selected points — exactly one of `ids`/`points_filter`. |
| `qdrant_payload_clear` | `payload` | ❌ | ✅ | ✅ | Wipe the entire payload of selected points, keeping their vectors — exactly one of `ids`/`points_filter`. |
| `qdrant_payload_facet` | `payload` | ✅ | ❌ | ✅ | Count distinct values of a payload field across the collection (or a filtered subset) — e.g. how many points per `city`. |
| `qdrant_payload_index_create` | `payload` | ❌ | ❌ | ✅ | Create a payload index on `field_name`, speeding up filters that use it. |
| `qdrant_payload_index_delete` | `payload` | ❌ | ✅ | ✅ | Delete the payload index on `field_name`. |
| `qdrant_collection_vector_create` | `payload` | ❌ | ❌ | ✅ | Add a new named vector (dense or sparse) to a collection that already has points, without touching them. |
| `qdrant_collection_vector_delete` | `payload` | ❌ | ✅ | ✅ | Remove a named vector (dense or sparse) from a collection — points keep their other vectors and payload. |
| `qdrant_points_batch_update` | `payload` | ❌ | ✅ | ❌ | Run multiple point operations (upsert, delete, set/overwrite/delete/clear payload, update/delete vectors) atomically against one collection, in the order given. |
| `qdrant_vectors_update` | `payload` | ❌ | ✅ | ✅ | Replace the vector(s) of existing points by id — leaves their payload untouched. |
| `qdrant_vectors_delete` | `payload` | ❌ | ✅ | ✅ | Remove specific named vectors from selected points, keeping their payload and other vectors — exactly one of `ids`/`points_filter`. |
| `qdrant_snapshot_create` | `snapshots` | ❌ | ❌ | ❌ | Create a snapshot of one collection's current state. |
| `qdrant_snapshot_list` | `snapshots` | ✅ | ❌ | ✅ | List the snapshots stored for one collection. |
| `qdrant_snapshot_delete` | `snapshots` | ❌ | ✅ | ✅ | Delete a collection snapshot, freeing its disk space on the server — does not touch the live collection. |
| `qdrant_snapshot_recover` | `snapshots` | ❌ | ✅ | ✅ | Overwrite `collection_name` with the state captured in a snapshot — everything written since that snapshot is lost. |
| `qdrant_snapshot_download` | `snapshots` | ✅ | ❌ | ✅ | Confirm a collection snapshot exists and return where to fetch it from — this tool does not transfer the (potentially huge) snapshot file itself; download it yourself (e.g. `curl`) from the returned `url`. |
| `qdrant_storage_snapshot_create` | `snapshots` | ❌ | ❌ | ❌ | Create a snapshot of the whole storage (every collection and server config), not just one collection. |
| `qdrant_storage_snapshot_list` | `snapshots` | ✅ | ❌ | ✅ | List the full-storage snapshots stored on the server. |
| `qdrant_storage_snapshot_delete` | `snapshots` | ❌ | ✅ | ✅ | Delete a full-storage snapshot, freeing its disk space. |
| `qdrant_storage_snapshot_download` | `snapshots` | ✅ | ❌ | ✅ | Confirm a full-storage snapshot exists and return where to fetch it from — same caveat as `qdrant_snapshot_download`: this tool does not transfer the file itself. |
| `qdrant_telemetry` | `observability` | ✅ | ❌ | ✅ | Server-wide telemetry: build info, per-collection stats, request counters, memory and hardware usage. |
| `qdrant_metrics_prometheus` | `observability` | ✅ | ❌ | ✅ | Return the URL where Qdrant serves Prometheus-format metrics — this tool does not fetch the metrics themselves (they're plain text, not JSON); point your Prometheus scraper at the returned `url` instead. |
| `qdrant_quotas_get` | `observability` | ✅ | ❌ | ✅ | Current server-wide resource quotas (memory/disk limits) and actual usage. |
| `qdrant_quotas_set` | `observability` | ❌ | ❌ | ✅ | Update server-wide resource quotas. |
| `qdrant_issues_list` | `observability` | ✅ | ❌ | ✅ | List the issues Qdrant has detected about its own configuration (e.g. a heavily-filtered field with no payload index). |
| `qdrant_issues_clear` | `observability` | ❌ | ✅ | ✅ | Clear all accumulated issues. |
<!-- TOOLS_TABLE_END -->

## Read-Only Mode

Setting `QDRANT_MCP_READ_ONLY=1` removes every tool whose `destructiveHint` isn't explicitly
`false` (i.e. anything that isn't `readOnlyHint=true`) **from the registry itself** — a client
calling `tools/list` never sees them, rather than seeing them and having calls rejected. This is
the mechanism to hand an LLM client safe, read-only access to a Qdrant deployment: point it at
your database, set the flag, and there is no code path left for it to write anything.

## Architecture

- **Single shared client.** One `AsyncQdrantClient` (or, in BYO mode, a proxy — see below) is
  built once at startup and closed over by every tool. Tools resolve it lazily at call time
  rather than caching anything from it at registration.
- **One registration choke point.** Every tool module calls into a single `ToolRegistry`, which
  is where the toolset filter and the read-only guard are both enforced — a tool can't bypass
  either by registering itself differently.
- **Resilience.** Every Qdrant call is wrapped with `tenacity`-based retry and backoff (the
  `qdrant-client` SDK itself only exposes a timeout, not retries), and translated into an MCP
  `ToolError` carrying Qdrant's own error message instead of a generic failure — so "collection
  not found" reads as exactly that.
- **`stdio`-safe logging.** All logging goes to `stderr`, configured before the MCP server
  object is even constructed — writing to `stdout` under the `stdio` transport would corrupt the
  JSON-RPC message framing.
- **BYO mode's indirection.** In `QDRANT_MCP_BYO` mode, the "client" every tool holds is a proxy
  that reads the real, per-caller `AsyncQdrantClient` out of a context variable set by request
  middleware — see [Bring your own Qdrant](#bring-your-own-qdrant-qdrant_mcp_byo) for the full
  mechanism.

## Security

- **Mandatory authentication for the personal `streamable-http` mode.** The server refuses to
  start without `QDRANT_MCP_SHARED_SECRET` — verified hands-on that an unauthenticated instance
  is trivially usable by anyone with the URL.
- **SSRF protection in BYO mode.** Since a BYO deployment connects to whatever URL an untrusted
  public caller supplies — from a host that may also run other services on internal networks —
  every URL is checked before use: only `http`/`https`, DNS-resolved, and rejected if any
  resolved address is private, loopback, link-local, or the cloud metadata address. This check
  **re-resolves on every request** rather than caching a prior result, specifically to defeat DNS
  rebinding.
- **Input validation everywhere.** Every tool's input is a Pydantic model — malformed input is
  rejected with a structured error before it reaches the Qdrant SDK.
- **No secrets at rest, no secrets logged.** BYO mode holds no long-lived credentials; API keys
  passed via `x-api-key` live only as long as their pooled client connection.

## Development

```bash
git clone https://github.com/avaazquezz/Qdrant-MCP.git
cd Qdrant-MCP
uv sync --dev
uv run pre-commit install
```

```bash
uv run ruff check .            # lint
uv run ruff format --check .   # formatting
uv run mypy .                  # type checking (strict)
uv run pytest                  # unit tests
uv run pytest -m integration   # integration tests — needs a running Qdrant (CI runs one as a Docker service)
```

If you add or change a tool, regenerate the table in [Available Tools](#available-tools) rather
than hand-editing it:

```bash
uv run python scripts/gen_tools_doc.py          # regenerate
uv run python scripts/gen_tools_doc.py --check  # verify, no changes (what CI runs)
```

## Versioning & Changelog

This project follows [Semantic Versioning](https://semver.org/). See
[CHANGELOG.md](CHANGELOG.md) for release notes and [ROADMAP.md](ROADMAP.md) for the phased
design history behind each version.

## License

[MIT](LICENSE)
