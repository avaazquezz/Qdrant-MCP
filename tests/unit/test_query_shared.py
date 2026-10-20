"""Unit tests for the query-construction helpers: pure functions, no client."""

from __future__ import annotations

from typing import Any

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from qdrant_client.http.models import (
    Direction,
    FormulaQuery,
    Fusion,
    FusionQuery,
    Mmr,
    MultExpression,
    NearestQuery,
    OrderBy,
    OrderByQuery,
    Prefetch,
    ReadConsistencyType,
    Rrf,
    RrfQuery,
    Sample,
    SampleQuery,
    SearchParams,
    SparseVector,
    SumExpression,
)

from mcp_qdrant.tools.query_shared import (
    FormulaInput,
    MmrInput,
    PrefetchInput,
    WeightedRrfInput,
    build_consistency,
    build_prefetch_list,
    build_query_value,
)

# --- exactly one query mode --------------------------------------------------


def test_a_plain_vector_is_returned_as_is() -> None:
    assert build_query_value([0.1, 0.2], None) == [0.1, 0.2]
    assert build_query_value(7, None) == 7


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"query_vector": [0.1], "fusion": "rrf"},
        {"query_vector": [0.1], "sample": "random"},
        {"fusion": "rrf", "order_by": "price"},
        {"formula": FormulaInput(expression="$score"), "sample": "random"},
        {"query_vector": [0.1], "formula": FormulaInput(expression="$score"), "order_by": "p"},
    ],
)
def test_zero_or_several_query_modes_are_rejected(kwargs: dict[str, Any]) -> None:
    arguments = {"query_vector": None, "fusion": None, **kwargs}
    with pytest.raises(ToolError, match="exactly one of"):
        build_query_value(**arguments)


# --- mmr ----------------------------------------------------------------------


def test_mmr_wraps_the_vector_in_a_nearest_query() -> None:
    query = build_query_value([0.1, 0.2], None, mmr=MmrInput(diversity=0.7, candidates_limit=50))
    assert query == NearestQuery(nearest=[0.1, 0.2], mmr=Mmr(diversity=0.7, candidates_limit=50))


def test_mmr_with_no_options_uses_qdrants_defaults() -> None:
    query = build_query_value([0.1], None, mmr=MmrInput())
    assert query == NearestQuery(nearest=[0.1], mmr=Mmr())


def test_mmr_works_with_a_point_id_and_a_sparse_vector() -> None:
    sparse = SparseVector(indices=[1], values=[1.0])
    assert build_query_value(3, None, mmr=MmrInput(diversity=0.5)) == NearestQuery(
        nearest=3, mmr=Mmr(diversity=0.5)
    )
    assert build_query_value(sparse, None, mmr=MmrInput()) == NearestQuery(
        nearest=sparse, mmr=Mmr()
    )


@pytest.mark.parametrize("other", [{"fusion": "rrf"}, {"sample": "random"}, {"order_by": "p"}])
def test_mmr_without_a_query_vector_is_rejected(other: dict[str, Any]) -> None:
    arguments = {"query_vector": None, "fusion": None, **other}
    with pytest.raises(ToolError, match="`mmr` only applies"):
        build_query_value(**arguments, mmr=MmrInput())


# --- fusion ---------------------------------------------------------------------


def test_named_fusions_keep_building_the_original_fusion_query() -> None:
    assert build_query_value(None, "rrf") == FusionQuery(fusion=Fusion.RRF)
    assert build_query_value(None, "dbsf") == FusionQuery(fusion=Fusion.DBSF)


def test_weighted_rrf_builds_an_rrf_query() -> None:
    query = build_query_value(None, WeightedRrfInput(k=10, weights=[2.0, 1.0]))
    assert query == RrfQuery(rrf=Rrf(k=10, weights=[2.0, 1.0]))


def test_weighted_rrf_with_nothing_set_is_still_an_rrf_query() -> None:
    assert build_query_value(None, WeightedRrfInput()) == RrfQuery(rrf=Rrf(k=None, weights=None))


# --- sample / order_by -----------------------------------------------------------


def test_sample_builds_a_random_sample_query() -> None:
    assert build_query_value(None, None, sample="random") == SampleQuery(sample=Sample.RANDOM)


def test_order_by_accepts_a_key_or_a_full_spec() -> None:
    assert build_query_value(None, None, order_by="price") == OrderByQuery(order_by="price")
    spec = OrderBy(key="price", direction=Direction.DESC, start_from=25.0)
    assert build_query_value(None, None, order_by=spec) == OrderByQuery(order_by=spec)


# --- formula ---------------------------------------------------------------------


def test_formula_is_parsed_into_qdrants_expression_types() -> None:
    query = build_query_value(
        None,
        None,
        formula=FormulaInput(
            expression={"sum": ["$score", {"mult": [0.5, "popularity"]}]},
            defaults={"popularity": 0.0},
        ),
    )
    assert isinstance(query, FormulaQuery)
    assert isinstance(query.formula, SumExpression)
    assert query.formula.sum[0] == "$score"
    assert isinstance(query.formula.sum[1], MultExpression)
    assert query.defaults == {"popularity": 0.0}


def test_formula_accepts_whole_numbers_conditions_and_decay_functions() -> None:
    expressions: list[dict[str, Any] | float | str] = [
        {"mult": [2, "$score"]},
        3,
        "$score",
        {"key": "city", "match": {"value": "sf"}},
        {
            "exp_decay": {
                "x": {"datetime_key": "created_at"},
                "target": {"datetime": "2026-01-01T00:00:00Z"},
                "scale": 86400,
                "midpoint": 0.5,
            }
        },
        {"geo_distance": {"origin": {"lat": 40.4, "lon": -3.7}, "to": "location"}},
        {"div": {"left": 1, "right": "$score", "by_zero_default": 0}},
    ]
    for expression in expressions:
        query = build_query_value(None, None, formula=FormulaInput(expression=expression))
        assert isinstance(query, FormulaQuery), expression


@pytest.mark.parametrize(
    "expression",
    [
        {"bogus": 1},
        {"sum": "not-a-list"},
        {"sum": ["$score", {"nope": 1}]},
        {"mult": [1], "sum": [1]},
    ],
)
def test_an_invalid_formula_gets_one_readable_error_not_a_wall_of_union_errors(
    expression: dict[str, Any],
) -> None:
    with pytest.raises(ToolError) as excinfo:
        build_query_value(None, None, formula=FormulaInput(expression=expression))

    message = str(excinfo.value)
    assert "not a valid formula expression" in message
    assert "exp_decay" in message  # lists what is accepted
    assert "validation error" not in message  # no pydantic dump
    assert len(message) < 600


# --- prefetch --------------------------------------------------------------------


def test_prefetch_stage_forwards_every_field() -> None:
    (stage,) = (
        build_prefetch_list(
            [
                PrefetchInput(
                    query_vector=[0.1, 0.2],
                    using="dense",
                    limit=20,
                    score_threshold=0.5,
                    search_params=SearchParams(exact=True),
                )
            ]
        )
        or []
    )
    assert stage == Prefetch(
        query=[0.1, 0.2],
        using="dense",
        limit=20,
        score_threshold=0.5,
        params=SearchParams(exact=True),
    )


def test_prefetch_none_stays_none() -> None:
    assert build_prefetch_list(None) is None


def test_prefetch_stages_nest_and_a_stage_can_be_a_fusion_of_its_children() -> None:
    sparse = SparseVector(indices=[1], values=[1.0])
    (outer,) = (
        build_prefetch_list(
            [
                PrefetchInput(
                    fusion="rrf",
                    limit=50,
                    prefetch=[
                        PrefetchInput(query_vector=[0.1, 0.2], using="dense", limit=100),
                        PrefetchInput(query_vector=sparse, using="sparse", limit=100),
                    ],
                )
            ]
        )
        or []
    )

    assert outer.query == FusionQuery(fusion=Fusion.RRF)
    assert outer.limit == 50
    assert outer.prefetch is not None and not isinstance(outer.prefetch, Prefetch)
    assert [p.using for p in outer.prefetch] == ["dense", "sparse"]
    assert outer.prefetch[1].query == sparse


def test_prefetch_nests_more_than_two_levels_deep() -> None:
    leaf = PrefetchInput(query_vector=[0.1], limit=10)
    middle = PrefetchInput(fusion="dbsf", prefetch=[leaf])
    top = PrefetchInput(fusion="rrf", prefetch=[middle])

    (built,) = build_prefetch_list([top]) or []

    assert isinstance(built.prefetch, list)
    inner = built.prefetch[0]
    assert isinstance(inner.prefetch, list)
    assert inner.prefetch[0].query == [0.1]


def test_a_prefetch_stage_needs_exactly_one_of_query_vector_or_fusion() -> None:
    with pytest.raises(ToolError, match="exactly one of"):
        build_prefetch_list([PrefetchInput(using="dense")])
    with pytest.raises(ToolError, match="exactly one of"):
        build_prefetch_list([PrefetchInput(query_vector=[0.1], fusion="rrf")])


def test_a_stage_error_inside_a_nested_prefetch_is_not_swallowed() -> None:
    with pytest.raises(ToolError, match="exactly one of"):
        build_prefetch_list([PrefetchInput(fusion="rrf", prefetch=[PrefetchInput()])])


# --- consistency -------------------------------------------------------------------


def test_consistency_passes_counts_through_and_maps_names_to_the_enum() -> None:
    assert build_consistency(None) is None
    assert build_consistency(2) == 2
    assert build_consistency("majority") == ReadConsistencyType.MAJORITY
    assert build_consistency("quorum") == ReadConsistencyType.QUORUM
    assert build_consistency("all") == ReadConsistencyType.ALL
