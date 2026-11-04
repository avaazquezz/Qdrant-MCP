"""What the server tells the model beyond each tool's own description (Fase 21).

- `instructions`: a short orientation the MCP client puts into the model's context for every
  conversation (verified: Claude Code quotes them verbatim), so every word costs context. Built
  from the enabled toolsets, so it never mentions a tool the model doesn't have.
- Prompts: guided workflows the user starts (in Claude Code, `/mcp__<server>__<prompt> args`,
  verified). Each is registered only when the tools it walks through are available and the
  server can write.
"""

from __future__ import annotations

from mcp.server import MCPServer

from mcp_qdrant.config import Settings


def instructions(settings: Settings) -> str:
    toolsets = set(settings.toolsets)
    lines = ["Qdrant MCP: one tool per Qdrant operation."]
    if "core" in toolsets:
        lines += [
            "- qdrant_collection_info shows a collection's vectors, payload indexes and, under "
            "metadata.mcp_qdrant, the text models it declares.",
            "- Search by plain text with qdrant_query: `query_text` (meaning; needs a declared "
            "model) or `bm25_query` (keywords; needs a text index with scoring); for hybrid, "
            'put one of each in `prefetch` with `fusion: "rrf"`. Otherwise pass a vector or a '
            "point id.",
        ]
    if toolsets & {"core", "search"}:
        lines.append(
            '- Ask only for the payload keys you need (`with_payload: ["title", ...]`). Results '
            "are capped per call: page with offset / next_page_offset."
        )
    if "admin" in toolsets:
        lines += [
            "- Before writing a filter, qdrant_payload_schema_infer lists the payload keys that "
            "really exist.",
            "- To diagnose or tune a collection: qdrant_collection_doctor, then "
            "qdrant_search_quality_eval to measure recall and latency.",
        ]
    if settings.read_only:
        lines.append("- This server is read-only: no tool here can write.")
    return "\n".join(lines)


def _tune_search(collection: str) -> str:
    return f"""Tune the search of the Qdrant collection `{collection}`, step by step:

1. Run qdrant_collection_doctor on it and summarize the findings.
2. Measure the current search with qdrant_search_quality_eval. Compare variants: `{{}}` (its
   current settings), `{{"hnsw_ef": 128}}`, and — if it is quantized —
   `{{"quantization": {{"rescore": true, "oversampling": 2.0}}}}`.
3. Propose the smallest change that improves recall or latency, with the measured numbers, and
   wait for my approval before changing anything.
4. If the change is a search parameter, it needs no rebuild: it goes in each query's
   `search_params`. HNSW and quantization settings change in place with qdrant_collection_update
   (the collection turns yellow while it rebuilds and keeps answering queries); measure again
   once it is green. Only a change qdrant_collection_update can't make needs a new collection:
   then follow a zero-downtime reindex (new collection, qdrant_collection_copy, measure,
   qdrant_alias_update)."""


def _zero_downtime_reindex(collection: str, alias: str) -> str:
    return f"""Rebuild the Qdrant collection `{collection}` without downtime, behind the alias
`{alias}`:

1. Read qdrant_collection_info on `{collection}` and ask me which settings the new collection
   should change. Propose a name for it (e.g. `{collection}_v2`).
2. Create it with qdrant_collection_create and those settings.
3. Copy the points with qdrant_collection_copy, calling it again with `offset=next_offset` until
   `done` is true. Compare the point counts (qdrant_points_count) of both collections.
4. Check the new collection with qdrant_search_quality_eval.
5. Ask for my approval, then point `{alias}` at the new collection with qdrant_alias_update (a
   single `create_alias` re-points an existing alias). If `{alias}` didn't exist, tell me that
   clients have to switch to it.
6. Keep `{collection}` until I confirm that everything works; don't delete it yourself."""


def _text_search_setup(collection: str, language: str) -> str:
    return f"""Set up plain-text search on the existing Qdrant collection `{collection}` (texts in
{language}):

1. Read qdrant_collection_info and one point (qdrant_points_scroll, limit 1) to find the payload
   key that holds the text.
2. Semantic search (`query_text`): ask me which embedding model produced its dense vectors —
   never guess, a different model returns plausible but wrong results. Declare it with
   qdrant_collection_update `text_models` (`""` for the unnamed vector); the size must match.
   Set `text_field` there too if the text isn't under `text`.
3. Keyword search (`bm25_query`): create a text index with BM25 scoring on that field with
   qdrant_payload_index_create, e.g. `field_schema`: `{{"type": "text", "tokenizer":
   "multilingual", "lowercase": true, "ascii_folding": true, "scoring": true, "stemmer":
   {{"type": "snowball", "language": "{language}"}}, "stopwords": "{language}"}}`.
4. Try both on a question in {language}, then a hybrid query (one `query_text` and one
   `bm25_query` stage in `prefetch`, `fusion: "rrf"`), and show me the results."""


def register_prompts(server: MCPServer[None], settings: Settings) -> None:
    if settings.read_only:
        return  # every workflow here ends in a write
    toolsets = set(settings.toolsets)
    if {"core", "admin"} <= toolsets:
        server.prompt(
            name="tune_search",
            title="Tune a collection's search",
            description="Diagnose, measure recall/latency, and propose the smallest improvement.",
        )(_tune_search)
        server.prompt(
            name="zero_downtime_reindex",
            title="Rebuild a collection without downtime",
            description="New collection, copy, measure, then switch the alias clients use.",
        )(_zero_downtime_reindex)
    if {"core", "payload"} <= toolsets:
        server.prompt(
            name="text_search_setup",
            title="Add text search to an existing collection",
            description="Declare its embedding model and add a BM25 index, then try both.",
        )(_text_search_setup)
