"""Local text embeddings with fastembed, from the optional `embeddings` extra.

fastembed is imported lazily, so the server starts and every tool that doesn't take text works
without the extra. Inference is CPU-bound and synchronous, and the first use of a model downloads
it (hundreds of MB), so it runs in a worker thread: on the event loop it would stall every other
request the server is handling.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Sequence
from functools import cache
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

MISSING_EXTRA = (
    "Text embeddings need the optional `embeddings` extra: run the server as "
    "`uvx --from 'mcp-qdrant[embeddings]' mcp-qdrant` or install `mcp-qdrant[embeddings]` "
    "(the Docker image and the .mcpb bundle include it)."
)
# fastembed's catalog says so in each model's description. It doesn't add those prefixes itself
# (verified on 0.9.1), and without them such models (e5, nomic, snowflake, ...) embed queries and
# documents into spaces that don't line up — so they're refused rather than silently degraded.
_NEEDS_PREFIXES = "Prefixes for queries/documents: necessary"

# One lock per model: loading (a first-use download) and inference are serialized per model, so a
# slow download of one model doesn't hold up queries against another that's already loaded.
_locks_guard = threading.Lock()
_locks: dict[str, threading.Lock] = {}
_loaded: dict[str, Any] = {}


def _text_embedding() -> Any:
    try:
        from fastembed import TextEmbedding
    except ImportError:
        raise ToolError(MISSING_EXTRA) from None
    return TextEmbedding


@cache
def _supported() -> dict[str, tuple[str, int]]:
    """Lower-cased model name → (canonical name, dimension), from fastembed's own catalog —
    nothing is downloaded to answer it. Models that need query/document prefixes are left out."""
    models = _text_embedding().list_supported_models()
    return {
        m["model"].lower(): (m["model"], m["dim"])
        for m in models
        if _NEEDS_PREFIXES not in m["description"]
    }


def model_info(model: str) -> tuple[str, int]:
    """(canonical name, dimension) of a dense text model this server can use."""
    try:
        return _supported()[model.lower()]
    except KeyError:
        names = ", ".join(sorted(name for name, _ in _supported().values()))
        raise ToolError(
            f"{model!r} is not a text embedding model this server supports (models that need "
            f"query/document prefixes, like e5 or nomic, are excluded). Supported: {names}."
        ) from None


def _lock_for(name: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(name, threading.Lock())


def _check_fits(instance: Any, name: str, texts: list[str]) -> None:
    """Refuse a text the model can't read whole: its tokenizer would silently cut it, and the
    vector would ignore the end of it (verified: two texts differing only past the limit got
    identical vectors)."""
    # ponytail: only models with a Hugging Face tokenizer are checked (all of fastembed's
    # transformer models); a model without one embeds whatever it reads.
    tokenizer = getattr(getattr(instance, "model", None), "tokenizer", None)
    if tokenizer is None:
        return
    for index, text in enumerate(texts):
        if tokenizer.encode(text).overflowing:
            limit = tokenizer.truncation["max_length"]
            raise ToolError(
                f"Text {index} is longer than {name} reads ({limit} tokens): the end would be "
                "silently left out of its vector. Split it into several points, or shorten it."
            )


def _embed_sync(model: str, texts: list[str], is_query: bool) -> list[list[float]]:
    name, _ = model_info(model)
    with _lock_for(name):
        if name not in _loaded:
            _loaded[name] = _text_embedding()(model_name=name)
        instance = _loaded[name]
        _check_fits(instance, name, texts)
        vectors = instance.query_embed(texts) if is_query else instance.passage_embed(texts)
        return [vector.tolist() for vector in vectors]


async def embed(model: str, texts: Sequence[str], *, is_query: bool) -> list[list[float]]:
    if any(not text.strip() for text in texts):
        raise ToolError("Text to embed is empty: there is nothing to search or store by meaning.")
    try:
        return await asyncio.to_thread(_embed_sync, model, list(texts), is_query)
    except ToolError:
        raise
    except Exception as exc:  # a failed model download, a corrupt cache, an ONNX runtime error
        raise ToolError(f"Embedding with {model!r} failed: {exc}") from exc
