# Qdrant-MCP

<!-- mcp-name: io.github.avaazquezz/mcp-qdrant -->

MCP server that wraps the Qdrant vector database API as tools. See [ROADMAP.md](ROADMAP.md).

## Tools

Generated from the live tool registry — run `uv run python scripts/gen_tools_doc.py` after adding or changing a tool.

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

## Configuration

Environment variables: `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_LOCAL_PATH` (exactly one
of `QDRANT_URL`/`QDRANT_LOCAL_PATH`), `QDRANT_MCP_READ_ONLY`, `QDRANT_MCP_TRANSPORT`
(`stdio` default, or `streamable-http`), `QDRANT_MCP_TOOLSETS` (comma-separated;
default `core` only — opt in to `search`, `payload`, `snapshots`, `observability`
explicitly), `QDRANT_MCP_BYO` (see below — mutually exclusive with
`QDRANT_URL`/`QDRANT_LOCAL_PATH`).

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

Or double-click the `.mcpb` bundle attached to a [release](https://github.com/avaazquezz/Qdrant-MCP/releases) — Claude Desktop prompts for the same settings through its own UI, no JSON to edit.

### Remote (`streamable-http`) — e.g. a custom connector in Claude.ai

`QDRANT_MCP_SHARED_SECRET` is **required** in this mode — the server refuses to start
as `streamable-http` without one, to avoid serving an unauthenticated endpoint over the
network (verified hands-on: an open `streamable-http` server is trivially usable by
anyone with the URL).

```bash
QDRANT_URL=http://localhost:6333 \
QDRANT_MCP_TRANSPORT=streamable-http \
QDRANT_MCP_HTTP_HOST=0.0.0.0 \
QDRANT_MCP_SHARED_SECRET=<a long random secret> \
mcp-qdrant
```

In Claude.ai (**Customize → Connectors → Add custom connector**, verified hands-on
against a real account): enter the server's HTTPS URL, then on the detected
authentication screen choose **"None"** and add a **Request header** —
`Authorization` → `Bearer <the same secret>`.

### Public "bring your own Qdrant" instance (`QDRANT_MCP_BYO`)

A `streamable-http` deployment can run with **no backing Qdrant of its own** — every
caller supplies their *own* Qdrant instance (their own Qdrant Cloud account, their
company's self-hosted Qdrant, whatever) per request, instead of using one the operator
hosts and pays for. Isolation between callers is automatic — each one talks to their own
database — so there's no shared secret, no per-user account, and no data at rest on this
server.

```bash
QDRANT_MCP_BYO=1 \
QDRANT_MCP_TRANSPORT=streamable-http \
QDRANT_MCP_HTTP_HOST=0.0.0.0 \
mcp-qdrant
```

Two request headers, reused for a different purpose than their name suggests — verified
hands-on that Claude.ai's custom-connector "Request headers" UI rejects made-up header
names outright unless Anthropic has approved them, so this reuses two pre-approved ones
instead of inventing `X-Qdrant-Url`/`X-Qdrant-Api-Key`:

- `Authorization` (**required**) — your Qdrant URL, e.g. `https://xyz.cloud.qdrant.io:6333`.
  Sent verbatim, no `Bearer` prefix needed.
- `x-api-key` (optional) — your Qdrant API key, if your instance needs one.

In Claude.ai: **Add custom connector** → authentication **"None"** → add both as
**Request headers**. Your Qdrant must be reachable from the public internet — an SSRF
guard rejects any URL that resolves to a private/internal/loopback address.
