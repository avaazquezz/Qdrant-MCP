# Qdrant-MCP

MCP server that wraps the Qdrant vector database API as tools. See [ROADMAP.md](ROADMAP.md).

## Tools

| Tool | Toolset | Read-only | Destructive | Idempotent | Description |
|---|---|---|---|---|---|
| `qdrant_health_check` | `core` | ✅ | ❌ | ✅ | Confirms the configured Qdrant instance is reachable and responding. |
