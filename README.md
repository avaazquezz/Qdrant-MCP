# Qdrant-MCP

MCP server that wraps the Qdrant vector database API as tools. See [ROADMAP.md](ROADMAP.md).

## Tools

| Tool | Toolset | Read-only | Destructive | Idempotent | Description |
|---|---|---|---|---|---|
| `qdrant_health_check` | `core` | ✅ | ❌ | ✅ | Confirms the configured Qdrant instance is reachable and responding. |
| `qdrant_collection_create` | `core` | ❌ | ❌ | ❌ | Creates a collection: single unnamed vector, or named/sparse vectors with quantization, multivectors, strict mode, and metadata. |
| `qdrant_collection_list` | `core` | ✅ | ❌ | ✅ | Lists every collection name in the configured Qdrant instance. |
| `qdrant_collection_info` | `core` | ✅ | ❌ | ✅ | Returns full config and status of one collection. |
| `qdrant_collection_update` | `core` | ❌ | ❌ | ✅ | Updates optimizer/HNSW/collection/vector params, quantization, strict mode on an existing collection. |
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
| `qdrant_payload_set` | `payload` | ❌ | ❌ | ✅ | Merges fields into the payload of selected points. |
| `qdrant_payload_overwrite` | `payload` | ❌ | ✅ | ✅ | Replaces the entire payload of selected points. |
| `qdrant_payload_delete` | `payload` | ❌ | ✅ | ✅ | Deletes specific payload keys from selected points. |
| `qdrant_payload_clear` | `payload` | ❌ | ✅ | ✅ | Wipes the entire payload of selected points, keeping their vectors. |
| `qdrant_payload_facet` | `payload` | ✅ | ❌ | ✅ | Counts distinct values of a payload field. |
| `qdrant_payload_index_create` | `payload` | ❌ | ❌ | ✅ | Creates a payload index on a field, from a simple type or a detailed params object. |
| `qdrant_payload_index_delete` | `payload` | ❌ | ✅ | ✅ | Deletes a payload index. |
| `qdrant_collection_vector_create` | `payload` | ❌ | ❌ | ✅ | Adds a new named vector (dense or sparse) to an existing collection. Requires Qdrant ≥ v1.19.0-era server. |
| `qdrant_collection_vector_delete` | `payload` | ❌ | ✅ | ✅ | Removes a named vector from an existing collection. Same server requirement as `_create`. |
| `qdrant_points_batch_update` | `payload` | ❌ | ✅ | ❌ | Runs multiple point operations atomically in one call. |
| `qdrant_vectors_update` | `payload` | ❌ | ✅ | ✅ | Replaces the vector(s) of existing points by id. |
| `qdrant_vectors_delete` | `payload` | ❌ | ✅ | ✅ | Removes specific named vectors from selected points. |
