"""`qdrant_collection_doctor` (Fase 20, toolset `admin`): reads one collection's info and the
server's aliases, and turns what Qdrant reports into findings that each carry the exact tool call
acting on them — the Qdrant knowledge (status colors, indexing threshold, memory math, text
contract) lives here instead of in the model. Read-only: it never applies a fix itself.

Every rule reports only what those two reads show; when a rule can't tell, it stays silent.
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    AliasDescription,
    CollectionInfo,
    CollectionStatus,
    Datatype,
    Memory,
    OptimizersStatusOneOf1,
    TextIndexParams,
    VectorParams,
)

from mcp_qdrant.tools.collections import dense_vector_size
from mcp_qdrant.tools.errors import call_qdrant
from mcp_qdrant.tools.registry import ToolRegistry
from mcp_qdrant.tools.text_shared import METADATA_KEY, contract_from_metadata

# Unquantized dense vectors kept in RAM above this size get a quantization hint.
MEMORY_HINT_BYTES = 1 << 30
ALIAS_PLACEHOLDER = "<name your clients will use>"
# Always evaluated; "text_contract" is added when the collection declares one.
ALWAYS_CHECKED = ("status", "unindexed", "memory", "aliases")

# https://qdrant.tech/documentation/capacity-planning/ — None is Qdrant's default, float32.
_BYTES_PER_DIM: dict[Datatype | None, float] = {
    None: 4,
    Datatype.FLOAT32: 4,
    Datatype.FLOAT16: 2,
    Datatype.TURBO16: 2,
    Datatype.UINT8: 1,
    Datatype.TURBO8: 1,
    Datatype.TURBO4: 0.5,
}

_DOCTOR_ANNOTATIONS = ToolAnnotations(
    title="Diagnose a Qdrant collection",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


class DoctorFix(BaseModel):
    tool: str
    arguments: dict[str, Any]


class DoctorFinding(BaseModel):
    rule: str
    severity: Literal["error", "warning", "info"]
    finding: str
    evidence: dict[str, Any]
    fix: DoctorFix | None


class DoctorReport(BaseModel):
    collection: str
    status: str
    points_count: int | None
    findings: list[DoctorFinding]
    checked: list[str]


def _dense_vectors(info: CollectionInfo) -> dict[str, VectorParams]:
    """Every entry of `vectors` (multivectors included), "" for the unnamed vector."""
    vectors = info.config.params.vectors
    if isinstance(vectors, VectorParams):
        return {"": vectors}
    return vectors or {}


def _status(name: str, info: CollectionInfo) -> DoctorFinding | None:
    evidence = info.model_dump(mode="json", include={"status", "optimizer_status"})
    progress = DoctorFix(
        tool="qdrant_collection_optimizations", arguments={"collection_name": name}
    )
    if info.status == CollectionStatus.YELLOW:
        return DoctorFinding(
            rule="status",
            severity="info",
            finding="Qdrant is optimizing this collection (status yellow).",
            evidence=evidence,
            fix=progress,
        )
    if info.status == CollectionStatus.GREY:
        # Qdrant's docs trigger them with exactly this empty optimizers update:
        # https://qdrant.tech/documentation/manage-data/collections/ ("Grey Collection Status").
        return DoctorFinding(
            rule="status",
            severity="warning",
            finding=(
                "Optimizations are pending but paused (status grey), normally after a Qdrant "
                "restart. Any update restarts them; the fix is an empty one that changes "
                "nothing else."
            ),
            evidence=evidence,
            fix=DoctorFix(
                tool="qdrant_collection_update",
                arguments={"collection_name": name, "optimizers_config": {}},
            ),
        )
    if info.status == CollectionStatus.RED:
        optimizer = info.optimizer_status
        error = f": {optimizer.error}" if isinstance(optimizer, OptimizersStatusOneOf1) else "."
        return DoctorFinding(
            rule="status",
            severity="error",
            finding=f"An optimization failed and Qdrant did not recover (status red){error}",
            evidence=evidence,
            fix=progress,
        )
    return None


def _unindexed(info: CollectionInfo) -> DoctorFinding | None:
    # ponytail: `indexed_vectors_count` sums dense AND sparse vectors (verified on 1.20: 5000
    # points with one dense and one sparse vector report 5000 before the dense index exists and
    # 10000 after), so a collection with sparse vectors never reaches 0 and this rule can't fire
    # for it. Telling dense apart would need per-segment telemetry.
    points = info.points_count or 0
    if not (points and info.indexed_vectors_count == 0 and _dense_vectors(info)):
        return None
    threshold = info.config.optimizer_config.indexing_threshold
    if threshold == 0:
        why = "Vector indexing is disabled (`indexing_threshold` is 0)."
    else:
        why = (
            "That's normal while each segment holds less than `indexing_threshold` "
            f"({threshold} KB) of vectors; for a large collection, lower that threshold "
            "(`optimizers_config` in `qdrant_collection_update`)."
        )
    return DoctorFinding(
        rule="unindexed",
        severity="info",
        finding=(
            "No vector (HNSW) index is built yet, so every vector search scans all "
            f"{points} points exactly. {why}"
        ),
        evidence={
            "points_count": points,
            "indexed_vectors_count": info.indexed_vectors_count,
            "indexing_threshold": threshold,
        },
        fix=None,
    )


def _memory(name: str, info: CollectionInfo) -> DoctorFinding | None:
    """Dense vectors held in RAM unquantized, sized as in Qdrant's capacity planning:
    points x replication_factor x dimensions x bytes per dimension, per vector."""
    if info.config.quantization_config is not None:
        return None
    points = info.points_count or 0
    replicas = info.config.params.replication_factor or 1
    by_vector: dict[str, int] = {}
    for vector_name, params in _dense_vectors(info).items():
        # `memory` overrides the deprecated `on_disk` when both are set (Qdrant's API schema).
        tier = params.memory or (Memory.COLD if params.on_disk else Memory.CACHED)
        # A multivector's size depends on its tokens per point, which the config doesn't say.
        if params.multivector_config or params.quantization_config or tier == Memory.COLD:
            continue
        by_vector[vector_name] = int(
            points * replicas * params.size * _BYTES_PER_DIM[params.datatype]
        )
    total = sum(by_vector.values())
    if total < MEMORY_HINT_BYTES:
        return None
    return DoctorFinding(
        rule="memory",
        severity="info",
        finding=(
            f"Up to ~{total / (1 << 30):.1f} GiB of dense vectors stay in RAM unquantized. "
            "Scalar int8 quantization keeps a copy at 1 byte per dimension (4x smaller than "
            "float32) in RAM, at some accuracy cost you can measure with "
            "`qdrant_search_quality_eval`."
        ),
        evidence={
            "bytes_by_vector": by_vector,
            "total_bytes": total,
            "points_count": points,
            "replication_factor": replicas,
        },
        fix=DoctorFix(
            tool="qdrant_collection_update",
            arguments={
                "collection_name": name,
                "quantization_config": {"scalar": {"type": "int8", "always_ram": True}},
            },
        ),
    )


def _aliases(name: str, aliases: list[AliasDescription]) -> DoctorFinding | None:
    # Matched on both sides because `name` may itself be an alias: get_collection resolves it,
    # but get_collection_aliases on an alias name answers an empty list (verified on 1.20).
    if any(name in (alias.alias_name, alias.collection_name) for alias in aliases):
        return None
    return DoctorFinding(
        rule="aliases",
        severity="info",
        finding=(
            "No alias points to this collection, so clients address it by its own name: "
            "switching them to a rebuilt collection (`qdrant_collection_copy` + "
            "`qdrant_alias_update`) would need a client change. In the fix, replace "
            f"{ALIAS_PLACEHOLDER!r} with the alias name your clients will use."
        ),
        evidence={"aliases": []},
        fix=DoctorFix(
            tool="qdrant_alias_update",
            arguments={
                "operations": [
                    {"create_alias": {"collection_name": name, "alias_name": ALIAS_PLACEHOLDER}}
                ]
            },
        ),
    )


def _text_contract(name: str, info: CollectionInfo) -> list[DoctorFinding]:
    metadata = info.config.metadata or {}
    try:
        contract = contract_from_metadata(metadata, name)
    except ToolError as exc:
        return [
            DoctorFinding(
                rule="text_contract",
                severity="error",
                finding=str(exc),
                evidence={METADATA_KEY: metadata.get(METADATA_KEY)},
                fix=None,
            )
        ]
    if contract is None:
        return []
    findings = [
        DoctorFinding(
            rule="text_contract",
            severity="error",
            finding=(
                f"Text model {model} is declared for vector {vector!r}, which is not a single "
                "dense vector of this collection, so text upserts and `query_text` on it fail. "
                "The fix removes the declaration."
            ),
            evidence={"vector": vector, "model": model, "vectors": sorted(_dense_vectors(info))},
            fix=DoctorFix(
                tool="qdrant_collection_update",
                arguments={"collection_name": name, "text_models": {vector: None}},
            ),
        )
        for vector, model in contract.models.items()
        if dense_vector_size(info, vector) is None
    ]
    field = contract.text_field
    index = info.payload_schema.get(field)
    if not (
        index is not None and isinstance(index.params, TextIndexParams) and index.params.scoring
    ):
        replaces = (
            f" Creating it replaces the current `{index.data_type.value}` index on {field!r}."
            if index is not None
            else ""
        )
        findings.append(
            DoctorFinding(
                rule="text_contract",
                severity="info",
                finding=(
                    f"`bm25_query` can't rank this collection: its text field {field!r} has no "
                    "`text` index with BM25 `scoring`. Adding a `stemmer` for the collection's "
                    'language ({"type": "snowball", "language": "<language>"}) to `field_schema` '
                    f"improves matching.{replaces}"
                ),
                evidence={
                    "text_field": field,
                    "index_type": index.data_type.value if index is not None else None,
                },
                fix=DoctorFix(
                    tool="qdrant_payload_index_create",
                    arguments={
                        "collection_name": name,
                        "field_name": field,
                        "field_schema": {
                            "type": "text",
                            "tokenizer": "multilingual",
                            "lowercase": True,
                            "ascii_folding": True,
                            "scoring": True,
                        },
                    },
                ),
            )
        )
    return findings


def register(registry: ToolRegistry, client: AsyncQdrantClient) -> None:
    async def qdrant_collection_doctor(collection_name: str) -> DoctorReport:
        """Diagnose one collection (or alias): read-only checks that each come with the exact
        tool call that acts on them, so you don't have to know Qdrant's internals.

        Rules (`rule` in each finding):
        - `status`: the collection isn't green — yellow (optimizing), grey (optimizations
          paused, usually after a restart) or red (an optimization failed; the error is in
          `evidence`).
        - `unindexed`: it has points but no vector (HNSW) index yet, so searches scan every
          point. Collections with sparse vectors are never flagged here.
        - `memory`: at least 1 GiB of dense vectors held in RAM without quantization
          (multivectors, on-disk/cold and quantized vectors don't count).
        - `aliases`: no alias points to it, so a rebuild-and-switch would need a client change.
        - `text_contract`: only for collections that declare text search (`text_models`): a
          declared model on a vector that isn't a single dense vector, a text field without a
          BM25 index, or malformed metadata.

        `checked` lists the rules evaluated: always the first four, plus `text_contract` when
        the collection declares one. A report with no findings means none of these rules fired,
        not that the collection is optimally configured.

        Each finding has a `severity` (error, warning, info), a plain-language `finding`, the
        numbers it is based on (`evidence`) and, when one exists, a `fix`: a call to another
        tool of this server, with arguments it accepts as is — except `aliases`, whose alias
        name is a placeholder to choose. Nothing is applied: calling the fix is up to you.

        Example: {"collection_name": "docs"}
        """
        info = await call_qdrant(lambda: client.get_collection(collection_name))
        aliases = await call_qdrant(lambda: client.get_aliases())
        rules = (
            _status(collection_name, info),
            _unindexed(info),
            _memory(collection_name, info),
            _aliases(collection_name, aliases.aliases),
        )
        findings = [finding for finding in rules if finding is not None]
        checked = list(ALWAYS_CHECKED)
        if METADATA_KEY in (info.config.metadata or {}):
            findings += _text_contract(collection_name, info)
            checked.append("text_contract")
        return DoctorReport(
            collection=collection_name,
            status=info.status.value,
            points_count=info.points_count,
            findings=findings,
            checked=checked,
        )

    registry.register(qdrant_collection_doctor, toolset="admin", annotations=_DOCTOR_ANNOTATIONS)
