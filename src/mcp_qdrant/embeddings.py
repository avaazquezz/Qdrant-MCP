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

# ponytail: one lock serializes model loading and inference for every model; per-model locks if
# several streamable-http clients ever need to embed in parallel.
_lock = threading.Lock()
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
    nothing is downloaded to answer it."""
    models = _text_embedding().list_supported_models()
    return {m["model"].lower(): (m["model"], m["dim"]) for m in models}


def model_info(model: str) -> tuple[str, int]:
    """(canonical name, dimension) of a dense text model fastembed supports."""
    try:
        return _supported()[model.lower()]
    except KeyError:
        names = ", ".join(sorted(name for name, _ in _supported().values()))
        raise ToolError(
            f"{model!r} is not a text embedding model this server supports. Supported: {names}."
        ) from None


def _embed_sync(model: str, texts: list[str], is_query: bool) -> list[list[float]]:
    name, _ = model_info(model)
    with _lock:
        if name not in _loaded:
            _loaded[name] = _text_embedding()(model_name=name)
        instance = _loaded[name]
        # query_embed/passage_embed apply whatever query/document prefix the model expects.
        vectors = instance.query_embed(texts) if is_query else instance.passage_embed(texts)
        return [vector.tolist() for vector in vectors]


async def embed(model: str, texts: Sequence[str], *, is_query: bool) -> list[list[float]]:
    try:
        return await asyncio.to_thread(_embed_sync, model, list(texts), is_query)
    except ToolError:
        raise
    except Exception as exc:  # a failed model download, a corrupt cache, an ONNX runtime error
        raise ToolError(f"Embedding with {model!r} failed: {exc}") from exc
