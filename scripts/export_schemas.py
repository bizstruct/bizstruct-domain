#!/usr/bin/env python3
"""Export JSON Schemas for all block models, plus the generation chain.

Writes schemas/<block>.json for every model in bizstruct_domain.blocks, and
schemas/chain.json for STAGES. Output is idempotent (stable key order,
indent=2, trailing newline) so re-running with no code changes produces no
git diff.
"""

import json
from pathlib import Path

from bizstruct_domain.blocks.architecture import Architecture
from bizstruct_domain.blocks.empathy_map import EmpathyMap
from bizstruct_domain.blocks.scenario import Scenario
from bizstruct_domain.blocks.pitch import Pitch
from bizstruct_domain.blocks.hypotheses import Hypotheses
from bizstruct_domain.blocks.models_options import ModelsOptions
from bizstruct_domain.blocks.canvas import Canvas
from bizstruct_domain.validate_model import ValidateModelResult
from bizstruct_domain.chain import STAGES

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"

BLOCK_MODELS = {
    "architecture": Architecture,
    "empathy_map": EmpathyMap,
    "scenario": Scenario,
    "pitch": Pitch,
    "hypotheses": Hypotheses,
    "models_options": ModelsOptions,
    # The persisted/CRUD shape (no per-section card-count constraint) — what
    # the frontend actually reads and writes. CanvasGenerated (2-4 cards per
    # section, generation-time only) isn't exported: it's an internal
    # contract between bizstruct-ml and bizstruct-be's hook, both of which
    # import it directly from this package rather than through the JSON
    # Schema sync.
    "canvas": Canvas,
}

# Not a chain stage (not in STAGES) — a side-channel task result. Exported
# the same way so bizstruct-fe can generate types for it too.
NON_BLOCK_MODELS = {
    "validate_model": ValidateModelResult,
}


def _write_json(path: Path, data: object) -> None:
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> None:
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)

    for name, model in {**BLOCK_MODELS, **NON_BLOCK_MODELS}.items():
        schema = model.model_json_schema()
        _write_json(SCHEMAS_DIR / f"{name}.json", schema)
        print(f"wrote schemas/{name}.json")

    chain_data = [stage.model_dump(mode="json") for stage in STAGES]
    _write_json(SCHEMAS_DIR / "chain.json", chain_data)
    print("wrote schemas/chain.json")


if __name__ == "__main__":
    main()
