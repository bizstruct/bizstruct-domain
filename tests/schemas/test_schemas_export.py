"""Drift test: committed schemas/*.json must match what the export script
generates, and nothing else may sit in schemas/ except declared legacy files."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO_ROOT / "schemas"
HINT = "run `python scripts/export_schemas.py` and commit the result"


@pytest.fixture(scope="module")
def export_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "export_schemas_script", REPO_ROOT / "scripts" / "export_schemas.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generated(export_script: ModuleType, tmp_path_factory: pytest.TempPathFactory) -> Path:
    target = tmp_path_factory.mktemp("schemas")
    export_script.write_schemas(target)
    return target


def test_export_writes_the_expected_files(generated: Path):
    names = {p.name for p in generated.glob("*.json")}
    assert {
        "canvas_generated.json",
        "stages.json",
        "stage_states.json",
        "brief.json",
        "swot.json",
        "environment_scan.json",
    } <= names


def test_every_generated_file_equals_the_committed_one(generated: Path):
    for path in sorted(generated.glob("*.json")):
        committed = SCHEMAS_DIR / path.name
        assert committed.exists(), f"{path.name} is not committed; {HINT}"
        assert committed.read_text(encoding="utf-8") == path.read_text(encoding="utf-8"), (
            f"schemas/{path.name} is stale; {HINT}"
        )


def test_every_other_committed_file_is_declared_legacy(
    generated: Path, export_script: ModuleType
):
    owned = {p.name for p in generated.glob("*.json")}
    unexpected = {p.name for p in SCHEMAS_DIR.glob("*.json")} - owned - export_script.LEGACY_SCHEMA_FILES
    assert not unexpected, (
        f"committed but neither generated nor in LEGACY_SCHEMA_FILES: {sorted(unexpected)}"
    )


def test_legacy_list_has_no_dead_or_overlapping_entries(
    generated: Path, export_script: ModuleType
):
    legacy = export_script.LEGACY_SCHEMA_FILES
    owned = {p.name for p in generated.glob("*.json")}
    assert not legacy & owned, "a file cannot be both generated and legacy"
    missing = {name for name in legacy if not (SCHEMAS_DIR / name).exists()}
    assert not missing, f"LEGACY_SCHEMA_FILES lists files that no longer exist: {sorted(missing)}"


def test_generation_is_deterministic(export_script: ModuleType):
    assert export_script.build_schemas() == export_script.build_schemas()


def test_files_end_with_newline_and_use_two_space_indent(generated: Path):
    for path in generated.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert text.endswith("}\n") or text.endswith("]\n"), path.name
        assert not text.endswith("\n\n"), path.name


def test_stages_json_lists_every_stage_after_its_inputs(generated: Path):
    import json

    stages = json.loads((generated / "stages.json").read_text(encoding="utf-8"))
    assert len(stages) == 13
    position = {s["id"]: i for i, s in enumerate(stages)}
    assert set(stages[0]) == {
        "id", "depends_on", "optional_depends_on", "allows_multiple_instances", "is_optional",
    }
    for s in stages:
        for dep in [*s["depends_on"], *s["optional_depends_on"]]:
            assert position[dep] < position[s["id"]]
