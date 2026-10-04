"""Contract this package offers its consumers (bizstruct-be, bizstruct-ml,
bizstruct-fe via schemas/).

Pins the stage ids and the shape of a stage definition, so a change to any
of them is a deliberate edit here and a version bump, not a silent drift
that consumers find at runtime. (Which JSON files exist is pinned by
tests/schemas/test_schemas_export.py; enum values by test_schemas_enums.py.)

Boundary (ADR-0009). None of these belong in this package:
- multiplicity: how many instances of a stage a project has and how they link;
- the SWOT/ERRC loop's iteration count and stopping rule (orchestration; the
  graph has ONE swot_errc_cycle node);
- product tiers or modes: there is one full graph;
- presentation: stage titles (localised) and user gates (a property of the
  traversal strategy) live in bizstruct-fe / bizstruct-be.
"""

import bizstruct_domain
from bizstruct_domain.schemas import STAGE_REGISTRY, Stage, StageDefinition

EXPECTED_STAGE_IDS = {
    "brief",
    "empathy_map",
    "customer_scenario",
    "ideation",
    "patterns",
    "canvas",
    "swot_errc_cycle",
    "storytelling",
    "future_scenario",
    "pitch",
    "team_info",
    "business_case",
    "environment_scan",
}

REMOVED_STAGE_IDS = {
    "value_map", "models_options", "assessment", "errc", "hypotheses", "scenario",
    "architecture", "what_if",
}

REMOVED_NAMES = (
    "STAGES", "topological_order", "validate_dag", "StageMode", "stages_for_mode",
    "Architecture", "WhatIf", "WhatIfGenerated", "Scenario", "Hypotheses", "Hypothesis",
    "ModelsOptions", "BusinessModelOption", "Assessment", "ERRC", "ERRCGenerated",
    "CostItem", "MarketBenchmark", "ScenarioQuestion", "FutureScenarioCase",
)


def test_stage_ids_are_exactly_the_contract():
    assert {s.value for s in Stage} == EXPECTED_STAGE_IDS
    assert {s.value for s in STAGE_REGISTRY.stages} == EXPECTED_STAGE_IDS


def test_removed_stage_ids_are_gone():
    assert not REMOVED_STAGE_IDS & {s.value for s in Stage}


def test_removed_names_are_not_exported():
    for name in REMOVED_NAMES:
        assert not hasattr(bizstruct_domain, name), name


def test_removed_modules_are_gone():
    import importlib

    for module in ("blocks", "chain", "enums", "sanitize", "validate_model"):
        try:
            importlib.import_module(f"bizstruct_domain.{module}")
        except ModuleNotFoundError:
            continue
        raise AssertionError(f"bizstruct_domain.{module} should not exist")


def test_stage_definition_is_structure_only():
    # Titles (localised presentation) and gates (traversal strategy) stay in
    # the consumers; there is no mode, tier or multiplicity field either.
    assert set(StageDefinition.model_fields) == {
        "id", "depends_on", "optional_depends_on", "allows_multiple_instances", "is_optional",
    }


def test_swot_errc_loop_is_one_node():
    assert "swot" not in {s.value for s in Stage}
    assert "errc" not in {s.value for s in Stage}
    assert Stage.SWOT_ERRC_CYCLE in STAGE_REGISTRY.stages


def test_version_matches_between_package_and_pyproject():
    import tomllib
    from pathlib import Path

    pyproject = tomllib.loads((Path(__file__).resolve().parent.parent / "pyproject.toml").read_text())
    assert bizstruct_domain.__version__ == pyproject["project"]["version"] == "0.14.0"
