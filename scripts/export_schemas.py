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
from bizstruct_domain.chain import STAGES

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"

BLOCK_MODELS = {
    "architecture": Architecture,
    "empathy_map": EmpathyMap,
}


def _write_json(path: Path, data: object) -> None:
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> None:
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)

    for name, model in BLOCK_MODELS.items():
        schema = model.model_json_schema()
        _write_json(SCHEMAS_DIR / f"{name}.json", schema)
        print(f"wrote schemas/{name}.json")

    chain_data = [stage.model_dump(mode="json") for stage in STAGES]
    _write_json(SCHEMAS_DIR / "chain.json", chain_data)
    print("wrote schemas/chain.json")


if __name__ == "__main__":
    main()
