# Qdrant-MCP

MCP server that wraps the Qdrant vector database API as tools. See [ROADMAP.md](ROADMAP.md).

## Tools

| Tool | Toolset | Read-only | Destructive | Idempotent | Description |
|---|---|---|---|---|---|
| `qdrant_health_check` | `core` | ✅ | ❌ | ✅ | Confirms the configured Qdrant instance is reachable and responding. |
| `qdrant_collection_create` | `core` | ❌ | ❌ | ❌ | Creates a collection with a single unnamed vector (size + distance). |
| `qdrant_collection_list` | `core` | ✅ | ❌ | ✅ | Lists every collection name in the configured Qdrant instance. |
| `qdrant_collection_info` | `core` | ✅ | ❌ | ✅ | Returns full config and status of one collection. |
| `qdrant_collection_update` | `core` | ❌ | ❌ | ✅ | Updates optimizer/HNSW/collection params on an existing collection. |
| `qdrant_collection_delete` | `core` | ❌ | ✅ | ✅ | Deletes a collection and all its points; a no-op if it doesn't exist. |
| `qdrant_collection_exists` | `core` | ✅ | ❌ | ✅ | Checks whether a collection exists, without raising if it doesn't. |
| `qdrant_points_upsert` | `core` | ❌ | ✅ | ✅ | Inserts or replaces points (id + vector + payload) in a collection. |
| `qdrant_points_get` | `core` | ✅ | ❌ | ✅ | Retrieves points by id; unknown ids are simply omitted, not an error. |
| `qdrant_points_delete` | `core` | ❌ | ✅ | ✅ | Deletes points by id list or by payload filter (exactly one of the two). |
| `qdrant_points_scroll` | `core` | ✅ | ❌ | ✅ | Pages through all points in a collection, optionally filtered. |
| `qdrant_points_count` | `core` | ✅ | ❌ | ✅ | Counts points in a collection, optionally matching a filter. |
| `qdrant_query` | `core` | ✅ | ❌ | ✅ | Vector similarity search with an optional payload filter and limit. |
