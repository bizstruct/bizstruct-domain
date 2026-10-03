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
    Canvas,
    CanvasGenerated,
    CustomerScenario,
    EmpathyMap,
    EnvironmentScan,
    Errc,
    FutureScenario,
    Ideation,
    Patterns,
    Pitch,
    STAGE_REGISTRY,
    Storytelling,
    Swot,
    TeamInfo,
)
from bizstruct_domain.validate_model import ValidateModelResult
from bizstruct_domain.enums import StageErrorCode, StageStatus
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

# Generation-time contract (2-4 text-only cards per section), not a persisted
# shape. Exported because the 2-4 bound lives in its JSON Schema.
GENERATION_MODELS = {
    "canvas_generated": CanvasGenerated,
}

# Not a stage artifact: a side-channel task result of the previous design.
# Still owned here until Phase 3 decides its fate.
NON_ARTIFACT_MODELS = {
    "validate_model": ValidateModelResult,
}

# Committed schemas/*.json that this script no longer generates. They are
# leftovers of the previous design, kept (not deleted) so bizstruct-fe keeps
# building until it migrates; they do NOT track the code any more. The drift
# test requires every committed .json to be either generated or listed here.
# Phase 3 empties this set and deletes the files.
LEGACY_SCHEMA_FILES = frozenset(
    {
        "assessment.json",
        "chain.json",
        "hypotheses.json",
        "models_options.json",
        "scenario.json",
    }
)


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

    # Kept until Phase 3 resolves stage_machine.
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
