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
| `qdrant_query` | `core` | ✅ | ❌ | ✅ | Vector similarity search, with optional hybrid search (`fusion`+`prefetch`), `using`, and `lookup_from`. |
| `qdrant_query_batch` | `search` | ✅ | ❌ | ✅ | Runs multiple independent queries against one collection in a single round trip. |
| `qdrant_query_groups` | `search` | ✅ | ❌ | ✅ | Vector query grouped by a payload field, up to N hits per group. |
| `qdrant_recommend` | `search` | ✅ | ❌ | ✅ | Finds points similar to positive examples and dissimilar to negative ones. |
| `qdrant_recommend_batch` | `search` | ✅ | ❌ | ✅ | Runs multiple independent recommend queries in a single round trip. |
| `qdrant_recommend_groups` | `search` | ✅ | ❌ | ✅ | Recommend query grouped by a payload field. |
| `qdrant_discover` | `search` | ✅ | ❌ | ✅ | Ranks points by fit to a target within positive/negative context pairs. |
| `qdrant_discover_batch` | `search` | ✅ | ❌ | ✅ | Runs multiple independent discover queries in a single round trip. |
| `qdrant_distance_matrix_pairs` | `search` | ✅ | ❌ | ✅ | Pairwise distance matrix between a random sample of points. |
| `qdrant_distance_matrix_offsets` | `search` | ✅ | ❌ | ✅ | Same distance matrix, in a compact offset-encoded shape. |
