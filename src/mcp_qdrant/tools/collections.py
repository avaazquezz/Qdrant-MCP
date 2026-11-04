"""The `core` toolset: collection CRUD (create/list/info/update/delete/exists)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    CollectionInfo,
    CollectionsResponse,
    Disabled,
    Distance,
    Language,
    Snowball,
    SnowballLanguage,
    SnowballParams,
    TextIndexParams,
    TextIndexType,
    TokenizerType,
    VectorParams,
)

from mcp_qdrant import embeddings
from mcp_qdrant.tools.errors import call_qdrant
from mcp_qdrant.tools.registry import ToolRegistry
from mcp_qdrant.tools.schemas import (
    CollectionParamsDiffInput,
    HnswConfigDiffInput,
    OptimizersConfigDiffInput,
    QuantizationConfigInput,
    SparseVectorParamsMapInput,
    StrictModeConfigInput,
    VectorParamsDiffMapInput,
    VectorParamsMapInput,
)
from mcp_qdrant.tools.text_shared import (
    DEFAULT_TEXT_FIELD,
    METADATA_KEY,
    TextContract,
    contract_from_metadata,
)

# The named vector `text_model` creates.
TEXT_VECTOR = "dense"
_STOPWORDS = {language.value for language in Language}


def _bm25_index(language: SnowballLanguage) -> TextIndexParams:
    """A text index ranked by BM25 (Qdrant 1.20 `scoring`), tokenized for one language: words
    reduced to their stem, accents folded, stopwords dropped — verified that `viviendas` then
    matches `vivienda` and `jovenes` matches `jóvenes`."""
    return TextIndexParams(
        type=TextIndexType.TEXT,
        tokenizer=TokenizerType.MULTILINGUAL,
        lowercase=True,
        ascii_folding=True,
        stemmer=SnowballParams(type=Snowball.SNOWBALL, language=language),
        stopwords=Language(language.value) if language.value in _STOPWORDS else None,
        scoring=True,
    )


def _dense_size(info: CollectionInfo, vector_name: str) -> int | None:
    """Size of a single-vector dense vector ("" = the unnamed one); None if there's no such
    vector, or it's a multivector (a text model makes one vector per text)."""
    vectors = info.config.params.vectors
    params = vectors if isinstance(vectors, VectorParams) and vector_name == "" else None
    if isinstance(vectors, dict):
        params = vectors.get(vector_name)
    if params is None or params.multivector_config is not None:
        return None
    return params.size


_CREATE_ANNOTATIONS = ToolAnnotations(
    title="Create Qdrant collection",
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)
_LIST_ANNOTATIONS = ToolAnnotations(
    title="List Qdrant collections",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_INFO_ANNOTATIONS = ToolAnnotations(
    title="Get Qdrant collection info",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_UPDATE_ANNOTATIONS = ToolAnnotations(
    title="Update Qdrant collection",
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_DELETE_ANNOTATIONS = ToolAnnotations(
    title="Delete Qdrant collection",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)
_EXISTS_ANNOTATIONS = ToolAnnotations(
    title="Check Qdrant collection existence",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


class CollectionDeleteResult(BaseModel):
    """True if the collection existed and was removed; False is a no-op, not
    an error (verified against a real Qdrant instance: DELETE on a missing
    collection returns 200/false, not 404)."""

    deleted: bool


class CollectionExistsResult(BaseModel):
    exists: bool


def register(registry: ToolRegistry, client: AsyncQdrantClient) -> None:
    async def qdrant_collection_create(
        collection_name: str,
        vector_size: Annotated[int, Field(gt=0)] | None = None,
        distance: Literal["Cosine", "Euclid", "Dot", "Manhattan"] = "Cosine",
        vectors: VectorParamsMapInput | None = None,
        sparse_vectors: SparseVectorParamsMapInput | None = None,
        quantization_config: QuantizationConfigInput | None = None,
        strict_mode_config: StrictModeConfigInput | None = None,
        metadata: dict[str, Any] | None = None,
        hnsw_config: HnswConfigDiffInput | None = None,
        optimizers_config: OptimizersConfigDiffInput | None = None,
        on_disk_payload: bool | None = None,
        text_model: str | None = None,
        text_language: SnowballLanguage | None = None,
        text_field: str = DEFAULT_TEXT_FIELD,
    ) -> CollectionInfo:
        """Create a collection: a single unnamed vector (`vector_size` +
        `distance`), one or more named vectors (`vectors`, each a full
        `VectorParams` — size, distance, and optionally its own
        `multivector_config` for ColBERT-style multi-vectors or
        `quantization_config`), or a text collection (`text_model`) — exactly
        one of the three. `sparse_vectors` defines sparse (keyword-style)
        vectors at creation time.

        Text: `text_model` (a fastembed model, e.g.
        `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384 dims,
        multilingual, downloaded on first use) creates a `dense` Cosine vector
        of the model's size and records the model in the collection's metadata,
        so `text` in `qdrant_points_upsert` and `query_text` in `qdrant_query`
        embed with it. `text_language` (e.g. "spanish") adds a BM25 index on
        `text_field` for `bm25_query`: stemmed, accent-folded, stopwords
        removed; given alone, it makes a keyword-only collection with no vectors.
        `quantization_config` (scalar/product/binary) and
        `strict_mode_config` apply to the whole collection.

        `hnsw_config` and `optimizers_config` set the index and optimizer
        parameters from the start (they can also be changed later with
        `qdrant_collection_update`); `on_disk_payload=true` keeps payloads
        on disk instead of in RAM, which can only be chosen here.

        Fails with a clear error if a collection with this name already exists.

        Example (simple): {"collection_name": "docs", "vector_size": 4, "distance": "Cosine"}
        Example (hybrid): {"collection_name": "docs", "vectors": {
            "dense": {"size": 4, "distance": "Cosine"}
        }, "sparse_vectors": {"sparse": {}}}
        Example (multitenant index, payload on disk): {"collection_name": "docs",
            "vector_size": 4, "hnsw_config": {"m": 0, "payload_m": 16},
            "on_disk_payload": true}
        Example (text, semantic + BM25): {"collection_name": "notes", "text_model":
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "text_language": "spanish"}
        """
        chosen = sum(v is not None for v in (vector_size, vectors, text_model))
        if chosen > 1 or (chosen == 0 and text_language is None):
            raise ToolError(
                "Provide exactly one of `vector_size`, `vectors` or `text_model` (or only "
                "`text_language`, for a keyword-only collection)."
            )
        vectors_config: VectorParams | dict[str, VectorParams] = {}
        if vector_size is not None:
            vectors_config = VectorParams(size=vector_size, distance=Distance(distance))
        elif vectors is not None:
            vectors_config = vectors
        models: dict[str, str] = {}
        if text_model is not None:
            model, size = embeddings.model_info(text_model)
            vectors_config = {TEXT_VECTOR: VectorParams(size=size, distance=Distance.COSINE)}
            models = {TEXT_VECTOR: model}
        if text_model is not None or text_language is not None:
            if metadata and METADATA_KEY in metadata:
                raise ToolError(
                    f"`metadata.{METADATA_KEY}` is written by `text_model`/`text_language`; "
                    "don't set it yourself."
                )
            contract = TextContract(text_field=text_field, models=models)
            metadata = {**(metadata or {}), METADATA_KEY: contract.model_dump()}
        await call_qdrant(
            lambda: client.create_collection(
                collection_name,
                vectors_config=vectors_config,
                sparse_vectors_config=sparse_vectors,
                quantization_config=quantization_config,
                strict_mode_config=strict_mode_config,
                metadata=metadata,
                hnsw_config=hnsw_config,
                optimizers_config=optimizers_config,
                on_disk_payload=on_disk_payload,
            )
        )
        if text_language is not None:
            try:
                await call_qdrant(
                    lambda: client.create_payload_index(
                        collection_name,
                        field_name=text_field,
                        field_schema=_bm25_index(text_language),
                        wait=True,
                    )
                )
            except ToolError as exc:
                raise ToolError(
                    f"Collection {collection_name!r} was created, but its BM25 index on "
                    f"{text_field!r} failed: {exc}. Create it with `qdrant_payload_index_create`."
                ) from exc
        return await call_qdrant(lambda: client.get_collection(collection_name))

    async def qdrant_collection_list() -> CollectionsResponse:
        """List every collection name in the configured Qdrant instance.

        Example: {}
        """
        return await call_qdrant(lambda: client.get_collections())

    async def qdrant_collection_info(collection_name: str) -> CollectionInfo:
        """Return full config and status of one collection.

        Fails with a clear error if the collection doesn't exist.

        Example: {"collection_name": "docs"}
        """
        return await call_qdrant(lambda: client.get_collection(collection_name))

    async def qdrant_collection_update(
        collection_name: str,
        optimizers_config: OptimizersConfigDiffInput | None = None,
        hnsw_config: HnswConfigDiffInput | None = None,
        collection_params: CollectionParamsDiffInput | None = None,
        vectors_config: VectorParamsDiffMapInput | None = None,
        quantization_config: QuantizationConfigInput | Literal["disabled"] | None = None,
        sparse_vectors_config: SparseVectorParamsMapInput | None = None,
        strict_mode_config: StrictModeConfigInput | None = None,
        text_models: dict[str, str] | None = None,
        text_field: str | None = None,
    ) -> CollectionInfo:
        """Update optimizer/HNSW/collection/vector params on an existing
        collection.

        `text_models` declares which fastembed model made each existing dense
        vector (`{"<vector name>": "<model>"}`, `""` for the unnamed vector), so
        `query_text` and `text` upserts work on a collection built elsewhere —
        it must be the model the stored vectors were made with, and its size
        must match the vector's. `text_field` names the payload field holding
        the text (default `text`). Both are kept in the collection's metadata.

        Only the fields you pass are changed; omitted ones keep their current
        value. `quantization_config="disabled"` turns quantization off.
        `vectors_config`/`sparse_vectors_config` only **adjust** named
        vectors that already exist (HNSW/quantization/index tuning) — they
        cannot add a new one; use `qdrant_collection_vector_create` for
        that, or this fails with Qdrant's own "Not existing vector name"
        error. Fails with a clear error if the collection doesn't exist.

        Example: {"collection_name": "docs", "optimizers_config": {"indexing_threshold": 10000}}
        """
        resolved_quantization = (
            Disabled.DISABLED if quantization_config == "disabled" else quantization_config
        )
        metadata = None
        if text_models is not None or text_field is not None:
            info = await call_qdrant(lambda: client.get_collection(collection_name))
            contract = contract_from_metadata(info.config.metadata, collection_name)
            contract = contract or TextContract()
            models = dict(contract.models)
            for vector_name, requested in (text_models or {}).items():
                model, size = embeddings.model_info(requested)
                actual = _dense_size(info, vector_name)
                if actual is None:
                    raise ToolError(
                        f"{collection_name!r} has no single dense vector named {vector_name!r} "
                        '("" is the unnamed vector).'
                    )
                if actual != size:
                    raise ToolError(
                        f"{model} makes {size}-dimensional vectors, but {vector_name!r} holds "
                        f"{actual}-dimensional ones: it can't be the model they were made with."
                    )
                models[vector_name] = model
            new = TextContract(text_field=text_field or contract.text_field, models=models)
            # Qdrant merges metadata only at the top level (verified), so the whole key is
            # rewritten.
            metadata = {METADATA_KEY: new.model_dump()}
        await call_qdrant(
            lambda: client.update_collection(
                collection_name,
                optimizers_config=optimizers_config,
                hnsw_config=hnsw_config,
                collection_params=collection_params,
                vectors_config=vectors_config,
                quantization_config=resolved_quantization,
                sparse_vectors_config=sparse_vectors_config,
                strict_mode_config=strict_mode_config,
                metadata=metadata,
            )
        )
        return await call_qdrant(lambda: client.get_collection(collection_name))

    async def qdrant_collection_delete(collection_name: str) -> CollectionDeleteResult:
        """Delete a collection and all its points; a no-op if it doesn't exist.

        Example: {"collection_name": "docs"}
        """
        deleted = await call_qdrant(lambda: client.delete_collection(collection_name))
        return CollectionDeleteResult(deleted=deleted)

    async def qdrant_collection_exists(collection_name: str) -> CollectionExistsResult:
        """Check whether a collection exists, without raising if it doesn't.

        Example: {"collection_name": "docs"}
        """
        exists = await call_qdrant(lambda: client.collection_exists(collection_name))
        return CollectionExistsResult(exists=exists)

    registry.register(qdrant_collection_create, toolset="core", annotations=_CREATE_ANNOTATIONS)
    registry.register(qdrant_collection_list, toolset="core", annotations=_LIST_ANNOTATIONS)
    registry.register(qdrant_collection_info, toolset="core", annotations=_INFO_ANNOTATIONS)
    registry.register(qdrant_collection_update, toolset="core", annotations=_UPDATE_ANNOTATIONS)
    registry.register(qdrant_collection_delete, toolset="core", annotations=_DELETE_ANNOTATIONS)
    registry.register(qdrant_collection_exists, toolset="core", annotations=_EXISTS_ANNOTATIONS)
