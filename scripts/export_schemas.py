#!/usr/bin/env python3
"""Export JSON Schemas for the BMG domain model (bizstruct_domain.schemas).

Writes schemas/<artifact>.json per persisted artifact model,
schemas/canvas_generated.json for the generation-time canvas contract, and
schemas/stages.json for STAGE_REGISTRY. Output is idempotent (stable key
order, indent=2, trailing newline) so re-running with no code changes
produces no git diff.
"""

import json
from pathlib import Path

from bizstruct_domain.schemas import (
    Brief,
    BusinessCase,
    BusinessCaseGenerated,
    Canvas,
    CanvasGenerated,
    CustomerScenario,
    CustomerScenarioGenerated,
    EmpathyMap,
    EmpathyMapGenerated,
    EnvironmentScan,
    EnvironmentScanGenerated,
    Errc,
    ErrcGenerated,
    FutureScenario,
    FutureScenarioGenerated,
    Ideation,
    IdeationGenerated,
    Patterns,
    PatternsGenerated,
    Pitch,
    PitchGenerated,
    STAGE_REGISTRY,
    StageErrorCode,
    StageStatus,
    Storytelling,
    StorytellingGenerated,
    Swot,
    SwotGenerated,
    TeamInfo,
    ValidateModelResult,
)
from bizstruct_domain.stage_machine import STAGE_TRANSITIONS

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"

# Persisted/CRUD shapes: what the frontend reads and writes. Nested models
# (CanvasCard, SwotClusterResult, ...) travel inside these via $defs.
ARTIFACT_MODELS = {
    "brief": Brief,
    "empathy_map": EmpathyMap,
    "customer_scenario": CustomerScenario,
    "ideation": Ideation,
    "patterns": Patterns,
    "canvas": Canvas,
    "swot": Swot,
    "errc": Errc,
    "storytelling": Storytelling,
    "future_scenario": FutureScenario,
    "pitch": Pitch,
    "team_info": TeamInfo,
    "business_case": BusinessCase,
    "environment_scan": EnvironmentScan,
}

# Generation contracts: what the LLM writes (the response_format), one file per
# model of GENERATION_CONTRACTS. Brief is its own contract (brief.json).
GENERATION_MODELS = {
    "empathy_map_generated": EmpathyMapGenerated,
    "customer_scenario_generated": CustomerScenarioGenerated,
    "ideation_generated": IdeationGenerated,
    "patterns_generated": PatternsGenerated,
    "canvas_generated": CanvasGenerated,
    "swot_generated": SwotGenerated,
    "errc_generated": ErrcGenerated,
    "storytelling_generated": StorytellingGenerated,
    "future_scenario_generated": FutureScenarioGenerated,
    "pitch_generated": PitchGenerated,
    "business_case_generated": BusinessCaseGenerated,
    "environment_scan_generated": EnvironmentScanGenerated,
}

# Not a stage artifact: a side-channel task result (see schemas/validate_model.py).
NON_ARTIFACT_MODELS = {
    "validate_model": ValidateModelResult,
}

# Committed schemas/*.json that this script no longer generates. Empty since
# the old design was removed; the drift test fails on any committed .json that
# is neither generated nor listed here.
LEGACY_SCHEMA_FILES: frozenset[str] = frozenset()


def _dumps(data: object) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def build_schemas() -> dict[str, str]:
    """File name -> exact file content, for every schema this script owns."""
    files: dict[str, str] = {}

    models = {**ARTIFACT_MODELS, **GENERATION_MODELS, **NON_ARTIFACT_MODELS}
    for name, model in models.items():
        files[f"{name}.json"] = _dumps(model.model_json_schema())

    # Topological order is deterministic and lists every stage after its inputs.
    stages = [
        STAGE_REGISTRY.stages[stage_id].model_dump(mode="json")
        for stage_id in STAGE_REGISTRY.topological_order()
    ]
    files["stages.json"] = _dumps(stages)

    files["stage_states.json"] = _dumps(
        {
            "statuses": [status.value for status in StageStatus],
            "error_codes": [code.value for code in StageErrorCode],
            "transitions": [
                {"from": current.value, "to": target.value}
                for current, target in STAGE_TRANSITIONS
            ],
        }
    )
    return files


def write_schemas(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for name, content in build_schemas().items():
        (target / name).write_text(content, encoding="utf-8")
        print(f"wrote {target.name}/{name}")


def main() -> None:
    write_schemas(SCHEMAS_DIR)


if __name__ == "__main__":
    main()
