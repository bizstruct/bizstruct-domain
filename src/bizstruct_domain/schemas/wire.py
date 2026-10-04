"""Wire contract between bizstruct-be and bizstruct-ml (ADR-0011).

The unit of work is a stage ROW: be creates rows, assigns row ids and records,
in `refs`, which rows each row draws from. ml receives a `QueueMessage`, reads
the `ProjectSnapshot`, generates, checks consistency and answers with a
`StageResult`. ml never writes statuses; be applies the stage-machine
transitions. Everything here is snake_case and pure: no I/O.
"""

import uuid
from collections import Counter
from collections.abc import Collection, Iterable, Sequence
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .brief import Brief
from .canvas import Canvas
from .chain import STAGE_REGISTRY
from .consistency import ConsistencyReport
from .customer_scenario import CustomerScenario
from .empathy_map import EmpathyMap
from .enums import Stage, StageErrorCode, StageStatus
from .errc import Errc
from .fields import SanitizedModel
from .future_scenario import FutureScenario
from .generation import GENERATION_CONTRACTS
from .ideation import Ideation
from .optional_inputs import BusinessCase, EnvironmentScan, TeamInfo
from .pattern import Patterns
from .pitch import Pitch
from .storytelling import Storytelling
from .swot import Swot


class ArtifactType(StrEnum):
    """The 14 persisted artifact models. `swot` and `errc` both belong to the
    `swot_errc_cycle` stage."""
    BRIEF = "brief"
    EMPATHY_MAP = "empathy_map"
    CUSTOMER_SCENARIO = "customer_scenario"
    IDEATION = "ideation"
    PATTERNS = "patterns"
    CANVAS = "canvas"
    SWOT = "swot"
    ERRC = "errc"
    STORYTELLING = "storytelling"
    FUTURE_SCENARIO = "future_scenario"
    PITCH = "pitch"
    TEAM_INFO = "team_info"
    BUSINESS_CASE = "business_case"
    ENVIRONMENT_SCAN = "environment_scan"


ARTIFACT_STAGE: dict[ArtifactType, Stage] = {
    ArtifactType.BRIEF: Stage.BRIEF,
    ArtifactType.EMPATHY_MAP: Stage.EMPATHY_MAP,
    ArtifactType.CUSTOMER_SCENARIO: Stage.CUSTOMER_SCENARIO,
    ArtifactType.IDEATION: Stage.IDEATION,
    ArtifactType.PATTERNS: Stage.PATTERNS,
    ArtifactType.CANVAS: Stage.CANVAS,
    ArtifactType.SWOT: Stage.SWOT_ERRC_CYCLE,
    ArtifactType.ERRC: Stage.SWOT_ERRC_CYCLE,
    ArtifactType.STORYTELLING: Stage.STORYTELLING,
    ArtifactType.FUTURE_SCENARIO: Stage.FUTURE_SCENARIO,
    ArtifactType.PITCH: Stage.PITCH,
    ArtifactType.TEAM_INFO: Stage.TEAM_INFO,
    ArtifactType.BUSINESS_CASE: Stage.BUSINESS_CASE,
    ArtifactType.ENVIRONMENT_SCAN: Stage.ENVIRONMENT_SCAN,
}

ARTIFACT_MODELS: dict[ArtifactType, type[BaseModel]] = {
    ArtifactType.BRIEF: Brief,
    ArtifactType.EMPATHY_MAP: EmpathyMap,
    ArtifactType.CUSTOMER_SCENARIO: CustomerScenario,
    ArtifactType.IDEATION: Ideation,
    ArtifactType.PATTERNS: Patterns,
    ArtifactType.CANVAS: Canvas,
    ArtifactType.SWOT: Swot,
    ArtifactType.ERRC: Errc,
    ArtifactType.STORYTELLING: Storytelling,
    ArtifactType.FUTURE_SCENARIO: FutureScenario,
    ArtifactType.PITCH: Pitch,
    ArtifactType.TEAM_INFO: TeamInfo,
    ArtifactType.BUSINESS_CASE: BusinessCase,
    ArtifactType.ENVIRONMENT_SCAN: EnvironmentScan,
}

# Fixed namespace of derived artifact ids. Changing it changes every id.
ARTIFACT_ID_NAMESPACE = uuid.UUID("5f0e6c3a-8d3b-5a58-9c1e-2b7a4d9f6e10")


# --------------------------------------------------------------------------- models


class ArtifactRecord(SanitizedModel):
    """One persisted artifact on the wire: its id, its type and its data."""
    id: str = Field(
        ...,
        description="Artifact id; derived with `derive_artifact_id`.",
        examples=["0b1a2c3d-4e5f-5a6b-8c7d-9e0f1a2b3c4d"],
    )
    type: ArtifactType = Field(
        ...,
        description="Which persisted model `data` follows.",
        examples=[ArtifactType.CANVAS],
    )
    data: dict[str, Any] = Field(
        ...,
        description="The artifact as the persisted model dumps it (validate with `parse_artifact`).",
        examples=[{"id": "0b1a2c3d", "persona_name": "Tech-Savvy Millennial"}],
    )


class StageRow(SanitizedModel):
    """A stage row as be keeps it: state plus the artifacts it produced."""
    id: str = Field(
        ...,
        description="Row id, assigned by be.",
        examples=["row_empathy_map_0"],
    )
    stage: Stage = Field(
        ...,
        description="The stage this row is an instance of.",
        examples=[Stage.EMPATHY_MAP],
    )
    instance_index: int = Field(
        default=0,
        ge=0,
        description="0-based order among rows of the same stage under the same parent; "
                     "for empathy_map, row k covers Brief.customer_segment_candidates[k].",
        examples=[0, 1],
    )
    status: StageStatus = Field(
        ...,
        description="Current status; only be changes it.",
        examples=[StageStatus.PENDING],
    )
    attempt_id: str | None = Field(
        default=None,
        description="Id of the current attempt, issued by be on every attempt of its own.",
        examples=["attempt_001"],
    )
    refs: dict[Stage, list[str]] = Field(
        default_factory=dict,
        description="Upstream stage -> ids of the rows this row draws from.",
        examples=[{"empathy_map": ["row_empathy_map_0"]}],
    )
    artifacts: list[ArtifactRecord] = Field(
        default_factory=list,
        description="Artifacts this row produced (empty until it has a result).",
        examples=[[ArtifactRecord(id="a1", type=ArtifactType.TEAM_INFO, data={"id": "a1"})]],
    )
    consistency: ConsistencyReport | None = Field(
        default=None,
        description="The last consistency report for this row, if any.",
        examples=[ConsistencyReport(score=5)],
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description="How many retries be has counted for this row.",
        examples=[0, 1],
    )
    error_code: StageErrorCode | None = Field(
        default=None,
        description="Why the row is in ERROR, if it is.",
        examples=[StageErrorCode.GENERATION_FAILED],
    )
    error: str | None = Field(
        default=None,
        description="Human-readable error text, if any.",
        examples=["Generated content failed validation."],
    )
    started_at: datetime | None = Field(
        default=None,
        description="When the current attempt started.",
        examples=["2026-10-04T12:00:00Z"],
    )
    finished_at: datetime | None = Field(
        default=None,
        description="When the row last finished.",
        examples=["2026-10-04T12:01:30Z"],
    )


class ProjectSnapshot(SanitizedModel):
    """What ml (and the experiment tool) reads: project fields and all rows."""
    project_id: str = Field(
        ...,
        description="Project id.",
        examples=["project_001"],
    )
    idea: str = Field(
        ...,
        description="The user's business idea.",
        examples=["A platform that connects local farmers with consumers."],
    )
    language: str = Field(
        ...,
        description="Generation language of the project ('uk' or 'en').",
        examples=["en"],
    )
    enabled_optional: list[Stage] = Field(
        default_factory=list,
        description="Optional stages enabled for this project; the only place this is carried.",
        examples=[[Stage.ENVIRONMENT_SCAN, Stage.TEAM_INFO]],
    )
    rows: list[StageRow] = Field(
        default_factory=list,
        description="All rows of the project (or, with ?row=<id>, that row and the closure of its refs).",
        examples=[[StageRow(id="row_brief", stage=Stage.BRIEF, status=StageStatus.DONE)]],
    )


class RowTarget(SanitizedModel):
    """One row a queue message asks ml to work on."""
    stage_row_id: str = Field(
        ...,
        description="The row to generate.",
        examples=["row_empathy_map_0"],
    )
    stage: Stage = Field(
        ...,
        description="The stage of that row (for routing and early dead-lettering).",
        examples=[Stage.EMPATHY_MAP],
    )
    attempt_id: str = Field(
        ...,
        description="The attempt this message belongs to; unchanged on redelivery.",
        examples=["attempt_001"],
    )


class QueueMessage(SanitizedModel):
    """be -> ml. The pipeline sends exactly one target; several are reserved for the agent phase."""
    project_id: str = Field(
        ...,
        description="Project id.",
        examples=["project_001"],
    )
    language: str = Field(
        ...,
        description="Generation language ('uk' or 'en'), for early trace attribution.",
        examples=["en"],
    )
    targets: list[RowTarget] = Field(
        ...,
        min_length=1,
        description="The rows to work on; at least one.",
        examples=[[RowTarget(stage_row_id="row_empathy_map_0", stage=Stage.EMPATHY_MAP, attempt_id="attempt_001")]],
    )


class StageFailure(SanitizedModel):
    """Why a row failed."""
    code: StageErrorCode = Field(
        ...,
        description="Failure code.",
        examples=[StageErrorCode.GENERATION_FAILED],
    )
    message: str = Field(
        ...,
        description="Human-readable explanation.",
        examples=["The model returned content that does not match the contract."],
    )


class StageResult(SanitizedModel):
    """ml -> be (hook). The final outcome of a row; ml never writes statuses."""
    project_id: str = Field(
        ...,
        description="Project id.",
        examples=["project_001"],
    )
    stage_row_id: str = Field(
        ...,
        description="The row this result is for.",
        examples=["row_empathy_map_0"],
    )
    attempt_id: str = Field(
        ...,
        description="The attempt this result belongs to.",
        examples=["attempt_001"],
    )
    status: Literal["success", "failed"] = Field(
        ...,
        description="Outcome of the generation.",
        examples=["success"],
    )
    artifacts: list[ArtifactRecord] = Field(
        default_factory=list,
        description="All artifacts of the row (for the cycle: every version). Required for success.",
        examples=[[ArtifactRecord(id="a1", type=ArtifactType.TEAM_INFO, data={"id": "a1"})]],
    )
    error: StageFailure | None = Field(
        default=None,
        description="Required for failed.",
        examples=[StageFailure(code=StageErrorCode.GENERATION_FAILED, message="Invalid output.")],
    )
    consistency: ConsistencyReport | None = Field(
        default=None,
        description="The final consistency report after ml's own retries.",
        examples=[ConsistencyReport(score=4)],
    )

    @model_validator(mode="after")
    def status_matches_payload(self) -> "StageResult":
        """
            Validates that a failed result carries an error and a successful one carries artifacts.
        """
        if self.status == "failed" and self.error is None:
            raise ValueError("A failed result requires an error.")
        if self.status == "success" and not self.artifacts:
            raise ValueError("A successful result requires at least one artifact.")
        return self


class StageEvent(SanitizedModel):
    """be -> fe via pubsub, published after be applied a transition."""
    type: Literal["stage_status"] = Field(
        default="stage_status",
        description="Event type.",
        examples=["stage_status"],
    )
    project_id: str = Field(
        ...,
        description="Project id.",
        examples=["project_001"],
    )
    stage_row_id: str = Field(
        ...,
        description="The row whose status changed.",
        examples=["row_empathy_map_0"],
    )
    stage: Stage = Field(
        ...,
        description="The stage of that row.",
        examples=[Stage.EMPATHY_MAP],
    )
    status: StageStatus = Field(
        ...,
        description="The row's new status.",
        examples=[StageStatus.DONE],
    )


class CanvasRowSpec(SanitizedModel):
    """One canvas row to create, derived from a Patterns group."""
    group_id: str = Field(
        ...,
        description="The Patterns group this canvas covers (becomes Canvas.group_id).",
        examples=["canvas_group_001"],
    )
    empathy_map_ids: list[str] = Field(
        ...,
        description="Artifact ids of the empathy maps in the group.",
        examples=[["empathy_map_001", "empathy_map_002"]],
    )


# --------------------------------------------------------------------------- pure functions


def derive_artifact_id(stage_row_id: str, artifact_type: ArtifactType, index: int = 0) -> str:
    """Deterministic artifact id (uuid5 under `ARTIFACT_ID_NAMESPACE`).

    `index` is 0 for single-artifact rows. For `canvas` and `swot_errc_cycle`
    it is the canvas version: Canvas v1 belongs to the canvas row, v2..5 to the
    cycle row; a Swot uses `Swot.canvas_version`, an Errc `Errc.from_version`.
    Regeneration yields the same ids, so foreign keys stay valid.
    """
    if index < 0:
        raise ValueError("index must be >= 0.")
    name = f"{stage_row_id}:{ArtifactType(artifact_type).value}:{index}"
    return str(uuid.uuid5(ARTIFACT_ID_NAMESPACE, name))


def _refs_problems(stage: Stage, refs: dict[Stage, list[str]]) -> list[str]:
    definition = STAGE_REGISTRY.stages[stage]
    allowed = set(definition.depends_on) | set(definition.optional_depends_on)
    problems = [f"refs key '{key.value}' is not a dependency of {stage.value}" for key in refs if key not in allowed]
    problems += [
        f"{stage.value} requires at least one row of hard dependency '{dep.value}'"
        for dep in definition.depends_on
        if not refs.get(dep)
    ]
    return problems


def validate_row_refs(stage: Stage, refs: dict[Stage, list[str]]) -> None:
    """Raise ValueError unless every key of `refs` is a dependency of `stage`
    (hard or optional) and every hard dependency has a non-empty list."""
    problems = _refs_problems(stage, refs)
    if problems:
        raise ValueError("; ".join(problems))


def _graph_position() -> dict[Stage, int]:
    return {stage: i for i, stage in enumerate(STAGE_REGISTRY.topological_order())}


def _check_enabled(enabled_optional: Collection[Stage]) -> set[Stage]:
    enabled = set(enabled_optional)
    bad = {s for s in enabled if not STAGE_REGISTRY.stages[s].is_optional}
    if bad:
        raise ValueError(f"enabled_optional contains non-optional stages: {bad}")
    return enabled


def ready_rows(rows: Sequence[StageRow], enabled_optional: Collection[Stage] = ()) -> tuple[str, ...]:
    """Ids of the rows that can start now (ADR-0011).

    A row is ready when (1) it is PENDING; (2) its refs pass `validate_row_refs`;
    (3) every row referenced for a hard dependency exists, is of that stage and
    is DONE; (4) every ENABLED optional dependency has a non-empty ref list whose
    rows are all DONE (an enabled optional stage that is not DONE, or has no row
    yet, blocks its consumer); (5) an optional stage is only ready if enabled;
    (5b) a PENDING row of a stage with no GENERATION_CONTRACTS entry (team_info,
    user input) is never ready. A disabled optional stage has no row and is
    ignored as a dependency. Result: graph order, then input order.
    """
    enabled = _check_enabled(enabled_optional)
    by_id = {row.id: row for row in rows}
    position = _graph_position()

    def all_done(stage: Stage, ids: list[str]) -> bool:
        return bool(ids) and all(
            (target := by_id.get(i)) is not None and target.stage == stage and target.status == StageStatus.DONE
            for i in ids
        )

    ready: list[tuple[int, int, str]] = []
    for order, row in enumerate(rows):
        definition = STAGE_REGISTRY.stages[row.stage]
        if row.status != StageStatus.PENDING:
            continue
        if row.stage not in GENERATION_CONTRACTS:
            continue
        if definition.is_optional and row.stage not in enabled:
            continue
        if _refs_problems(row.stage, row.refs):
            continue
        if not all(all_done(dep, row.refs[dep]) for dep in definition.depends_on):
            continue
        if not all(all_done(dep, row.refs.get(dep, [])) for dep in definition.optional_depends_on if dep in enabled):
            continue
        ready.append((position[row.stage], order, row.id))
    return tuple(row_id for _, _, row_id in sorted(ready))


def dependent_rows(row_id: str, rows: Sequence[StageRow]) -> tuple[str, ...]:
    """Ids of every row that depends on `row_id` through `refs` (hard or
    optional edges), transitively, excluding the row itself. Graph order, then
    input order. Raises ValueError for an unknown row id."""
    if all(row.id != row_id for row in rows):
        raise ValueError(f"unknown row id: '{row_id}'")
    referrers: dict[str, set[str]] = {}
    for row in rows:
        for ids in row.refs.values():
            for ref in ids:
                referrers.setdefault(ref, set()).add(row.id)
    seen: set[str] = set()
    frontier = {row_id}
    while frontier:
        nxt: set[str] = set()
        for current in frontier:
            for dependent in referrers.get(current, ()):
                if dependent not in seen and dependent != row_id:
                    seen.add(dependent)
                    nxt.add(dependent)
        frontier = nxt
    position = _graph_position()
    ordered = sorted(
        (position[row.stage], order, row.id) for order, row in enumerate(rows) if row.id in seen
    )
    return tuple(rid for _, _, rid in ordered)


_PER_SEGMENT = (Stage.CUSTOMER_SCENARIO, Stage.IDEATION)
_PER_CANVAS = (Stage.SWOT_ERRC_CYCLE, Stage.STORYTELLING, Stage.FUTURE_SCENARIO, Stage.PITCH)


def project_status(
    rows: Sequence[StageRow], enabled_optional: Collection[Stage] = ()
) -> Literal["completed", "failed", "running"]:
    """Project status derived from its rows (ADR-0011).

    `failed`: some row is ERROR (only a user action leaves ERROR). `completed`:
    no ERROR, every row DONE and the expansion is complete: brief, patterns and
    every enabled optional stage have exactly one row, empathy_map and canvas at
    least one, customer_scenario/ideation one per empathy_map row and the
    per-canvas stages one per canvas row (a disabled optional stage has none).
    `running`: everything else, including rows awaiting a user decision.
    """
    enabled = _check_enabled(enabled_optional)
    if any(row.status == StageStatus.ERROR for row in rows):
        return "failed"
    if not rows or any(row.status != StageStatus.DONE for row in rows):
        return "running"
    counts = Counter(row.stage for row in rows)
    n_maps, n_canvases = counts[Stage.EMPATHY_MAP], counts[Stage.CANVAS]
    expected: dict[Stage, int] = {Stage.BRIEF: 1, Stage.PATTERNS: 1}
    for optional in (Stage.TEAM_INFO, Stage.BUSINESS_CASE, Stage.ENVIRONMENT_SCAN):
        expected[optional] = 1 if optional in enabled else 0
    expected.update({stage: n_maps for stage in _PER_SEGMENT})
    expected.update({stage: n_canvases for stage in _PER_CANVAS})
    complete = n_maps >= 1 and n_canvases >= 1 and all(counts[s] == n for s, n in expected.items())
    return "completed" if complete else "running"


def canvas_rows_for(patterns: Patterns) -> list[CanvasRowSpec]:
    """One canvas row per Patterns group (one for unified_model, several for split_model)."""
    return [
        CanvasRowSpec(group_id=group.id, empathy_map_ids=list(group.empathy_map_ids))
        for group in patterns.groups
    ]


def row_of_artifact(rows: Iterable[StageRow], artifact_id: str) -> StageRow | None:
    """The row that holds the artifact with this id, or None."""
    for row in rows:
        if any(artifact.id == artifact_id for artifact in row.artifacts):
            return row
    return None


def parse_artifact(record: ArtifactRecord) -> BaseModel:
    """Validate `record.data` with the persisted model of `record.type`.

    Raises ValueError (pydantic's ValidationError is one) if the data is invalid
    or its `id` differs from `record.id`.
    """
    model = ARTIFACT_MODELS[record.type]
    parsed = model.model_validate(record.data)
    if "id" in model.model_fields and getattr(parsed, "id") != record.id:
        raise ValueError(f"record id '{record.id}' differs from the artifact's own id '{getattr(parsed, 'id')}'.")
    return parsed
