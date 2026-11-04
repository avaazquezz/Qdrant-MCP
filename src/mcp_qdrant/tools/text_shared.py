"""Text instead of vectors: the contract a collection declares, and turning text into what the
Query API takes. Shared by `qdrant_query*` (`query_text`, `bm25_query`), `qdrant_points_upsert`
(`text`) and `qdrant_collection_create`/`_update` (which write the contract). Not a toolset.

A collection declares in its own metadata (Qdrant ≥ 1.16) which model produced each dense vector
and which payload field holds the text:

    {"mcp_qdrant": {"text_field": "text", "models": {"dense": "<fastembed model>"}}}

The server never guesses a model: a query embedded with a different model than the stored vectors
returns plausible-looking garbage with no error. BM25 needs no model: Qdrant 1.20 ranks a payload
field with a `text` index that has `scoring` set, using that index's own tokenizer and stemmer.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ValidationError, field_validator
from qdrant_client import AsyncQdrantClient

from mcp_qdrant import embeddings
from mcp_qdrant.tools.errors import call_qdrant
from mcp_qdrant.tools.query_shared import PrefetchInput, VectorOrId

METADATA_KEY = "mcp_qdrant"
DEFAULT_TEXT_FIELD = "text"


class TextContract(BaseModel):
    text_field: str = DEFAULT_TEXT_FIELD
    models: dict[str, str] = {}

    @field_validator("text_field")
    @classmethod
    def _plain_key(cls, value: str) -> str:
        # Upserts write the text under this literal key, while a payload index (and BM25) reads
        # `a.b` as a nested path — so a dotted name could never be found (verified).
        if not value or "." in value or "[" in value:
            raise ValueError(
                f"`text_field` must be a plain top-level payload key (no `.` or `[`), got {value!r}"
            )
        return value


def new_contract(text_field: str, models: dict[str, str]) -> TextContract:
    try:
        return TextContract(text_field=text_field, models=models)
    except ValidationError as exc:
        raise ToolError(exc.errors()[0]["msg"].removeprefix("Value error, ")) from exc


def _declare_hint(collection: str) -> str:
    return (
        f"Declare it with `qdrant_collection_update` on {collection!r}: "
        '`text_models` ({"<vector name>": "<the model its vectors were made with>"}).'
    )


def contract_from_metadata(metadata: dict[str, Any] | None, collection: str) -> TextContract | None:
    raw = (metadata or {}).get(METADATA_KEY)
    if raw is None:
        return None
    try:
        return TextContract.model_validate(raw)
    except ValidationError as exc:
        raise ToolError(
            f"Collection {collection!r} has malformed `{METADATA_KEY}` metadata "
            f"({exc.error_count()} problem(s)): expected "
            "{'text_field': str, 'models': {vector: model}}."
        ) from exc


async def read_contract(client: AsyncQdrantClient, collection: str) -> TextContract | None:
    info = await call_qdrant(lambda: client.get_collection(collection))
    return contract_from_metadata(info.config.metadata, collection)


def qdrant_using(vector_name: str) -> str | None:
    """The unnamed vector is declared under "" and addressed by omitting `using`."""
    return vector_name or None


class TextResolver:
    """Resolves the text modes of one tool call against one collection. Reads the collection's
    contract at most once, and only if some text mode is actually used."""

    def __init__(self, client: AsyncQdrantClient, collection: str) -> None:
        self._client = client
        self._collection = collection
        self._contract: TextContract | None = None
        self._read = False

    async def contract(self) -> TextContract | None:
        if not self._read:
            self._contract = await read_contract(self._client, self._collection)
            self._read = True
        return self._contract

    async def _model_for(self, using: str | None) -> tuple[str, str]:
        contract = await self.contract()
        models = contract.models if contract else {}
        if using is not None:
            if using in models:
                return using, models[using]
            raise ToolError(
                f"Vector {using!r} of {self._collection!r} has no declared text model, so its "
                f"vectors can't be matched by text. {_declare_hint(self._collection)}"
            )
        if len(models) == 1:
            return next(iter(models.items()))
        if not models:
            raise ToolError(
                f"Collection {self._collection!r} declares no text model, so `query_text` can't "
                f"be embedded. {_declare_hint(self._collection)}"
            )
        raise ToolError(
            f"Collection {self._collection!r} declares text models for several vectors "
            f"({sorted(models)}): set `using` to pick one."
        )

    async def query_vector(self, text: str, using: str | None) -> tuple[list[float], str | None]:
        vector_name, model = await self._model_for(using)
        [vector] = await embeddings.embed(model, [text], is_query=True)
        return vector, qdrant_using(vector_name)

    async def bm25_field(self, using: str | None) -> str:
        if using is not None:
            return using
        contract = await self.contract()
        if contract is None:
            raise ToolError(
                "`bm25_query` needs `using`: the payload field whose `text` index has `scoring` "
                f"set (collection {self._collection!r} declares no text field)."
            )
        return contract.text_field

    async def resolve(
        self,
        query_vector: VectorOrId | None,
        query_text: str | None,
        bm25_query: str | None,
        using: str | None,
    ) -> tuple[VectorOrId | None, str | None]:
        """`query_text` becomes an embedded `query_vector` (and its vector name in `using`);
        `bm25_query` gets its text field in `using`. Other modes pass through."""
        if query_text is not None:
            if query_vector is not None:
                raise ToolError("Provide only one of `query_vector` or `query_text`.")
            return await self.query_vector(query_text, using)
        if bm25_query is not None:
            return query_vector, await self.bm25_field(using)
        return query_vector, using

    async def resolved_fields(
        self,
        query_vector: VectorOrId | None,
        query_text: str | None,
        bm25_query: str | None,
        using: str | None,
        prefetch: list[PrefetchInput] | None,
    ) -> dict[str, Any]:
        """The `model_copy(update=...)` that resolves a text-capable input item (a prefetch stage
        or a batch query): its own mode, then its nested stages."""
        query_vector, using = await self.resolve(query_vector, query_text, bm25_query, using)
        return {
            "query_vector": query_vector,
            "query_text": None,
            "using": using,
            "prefetch": await self.resolve_prefetch(prefetch),
        }

    async def resolve_prefetch(
        self, prefetch: list[PrefetchInput] | None
    ) -> list[PrefetchInput] | None:
        if prefetch is None:
            return None
        return [
            stage.model_copy(
                update=await self.resolved_fields(
                    stage.query_vector,
                    stage.query_text,
                    stage.bm25_query,
                    stage.using,
                    stage.prefetch,
                )
            )
            for stage in prefetch
        ]
