"""Contract this package offers its consumers (bizstruct-be, bizstruct-ml,
bizstruct-fe via schemas/).

Pins the stage ids, the id renames from ADR-0008, and the set of exported
block schemas, so a change to any of them is a deliberate edit here and a
version bump, not a silent drift that consumers find at runtime.

Boundary, also from ADR-0008. None of these belong in this package, and
they must not come back implicitly:
- multiplicity: how many instances of a stage a project has (per customer
  segment, one or N canvases after Patterns' A/B decision) and how they link;
- versioning of Canvas -> SWOT -> ERRC iterations and the loop's stopping
  rule (weighted Weaknesses + Threats);
- product tiers (Basic/Pro): which subset of the graph a project runs.
All of these are bizstruct-be/bizstruct-ml's job. The tests at the bottom
guard the obvious ways they could creep back in.
"""

import json
from pathlib import Path

import bizstruct_domain
from bizstruct_domain.chain import STAGES, Stage

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"

EXPECTED_STAGE_IDS = {
    "brief",
    "team_info",
    "business_case",
    "empathy_map",
    "environment_scan",
    "value_map",
    "customer_scenario",
    "ideation",
    "patterns",
    "models_options",
    "canvas",
    "assessment",
    "errc",
    "hypotheses",
    "scenario",
    "pitch",
}

# Stages that have a block model and hence an exported schema. brief,
# environment_scan and value_map don't have models yet.
EXPECTED_BLOCK_SCHEMAS = EXPECTED_STAGE_IDS - {"brief", "environment_scan", "value_map"}

REMOVED_STAGE_IDS = {"architecture", "what_if"}


def test_stage_ids_are_exactly_the_contract():
    assert {s.id for s in STAGES} == EXPECTED_STAGE_IDS


def test_removed_stage_ids_are_gone():
    # architecture -> ideation + patterns; what_if -> errc.
    assert not REMOVED_STAGE_IDS & {s.id for s in STAGES}


def test_exported_schemas_match_block_stages():
    exported = {p.stem for p in SCHEMAS_DIR.glob("*.json")}
    non_block = {"chain", "stage_states", "validate_model"}
    assert exported - non_block == EXPECTED_BLOCK_SCHEMAS


def test_chain_json_matches_stages():
    data = json.loads((SCHEMAS_DIR / "chain.json").read_text(encoding="utf-8"))
    assert data == [s.model_dump(mode="json") for s in STAGES]


def test_removed_names_are_not_exported():
    for name in ("Architecture", "WhatIf", "WhatIfAlternative", "WhatIfGenerated", "Scenario", "StageMode", "stages_for_mode"):
        assert not hasattr(bizstruct_domain, name), name


def test_stage_carries_no_mode_or_cardinality():
    forbidden = {"mode", "cardinality", "multiplicity", "tier"}
    assert not forbidden & set(Stage.model_fields)


def test_no_iteration_or_variant_model_is_exported():
    forbidden_words = ("Iteration", "Variant", "Version")
    leaked = [name for name in bizstruct_domain.__all__ if any(w in name for w in forbidden_words)]
    assert not leaked, leaked
