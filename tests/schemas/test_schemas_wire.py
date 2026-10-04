"""Wire contract (schemas/wire.py, ADR-0011)."""

import subprocess
import sys
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

import schema_builders as b
import bizstruct_domain.schemas.wire as wire
from bizstruct_domain.schemas import (
    ARTIFACT_MODELS,
    ARTIFACT_STAGE,
    GENERATION_CONTRACTS,
    ArtifactRecord,
    ArtifactType,
    CanvasGroup,
    ConsistencyReport,
    ProjectSnapshot,
    QueueMessage,
    RowTarget,
    SanitizedModel,
    SegmentRelationType,
    Stage,
    StageEvent,
    StageFailure,
    StageResult,
    StageRow,
    StageStatus,
    StageErrorCode,
    canvas_rows_for,
    dependent_rows,
    derive_artifact_id,
    parse_artifact,
    project_status,
    ready_rows,
    row_of_artifact,
    validate_row_refs,
)
from bizstruct_domain.schemas.enums import CanvasBranch
from bizstruct_domain.schemas.optional_inputs import TeamInfo, TeamMember
from test_schemas_generation import GENERATED, CONTRACTS

D, P, R, E = StageStatus.DONE, StageStatus.PENDING, StageStatus.RUNNING, StageStatus.ERROR
S = Stage


# --------------------------------------------------------------------------- project fixture


def make_rows(
    n_segments: int = 2,
    groups: tuple[tuple[int, ...], ...] = ((0,), (1,)),
    enabled: frozenset[Stage] = frozenset(),
    status: dict[str, StageStatus] | None = None,
    default: StageStatus = D,
) -> list[StageRow]:
    """A whole project laid out as ADR-0011 prescribes; every row `default`, except `status` overrides."""
    status = status or {}
    rows: list[StageRow] = []

    def add(id: str, stage: Stage, refs: dict[Stage, list[str]], index: int = 0) -> None:
        rows.append(StageRow(id=id, stage=stage, instance_index=index, status=status.get(id, default), refs=refs))

    add("brief", S.BRIEF, {})
    segments = range(n_segments)
    for i in segments:
        add(f"em-{i}", S.EMPATHY_MAP, {S.BRIEF: ["brief"]}, i)
    for i in segments:
        add(f"cs-{i}", S.CUSTOMER_SCENARIO, {S.EMPATHY_MAP: [f"em-{i}"]}, i)
        add(f"id-{i}", S.IDEATION, {S.EMPATHY_MAP: [f"em-{i}"]}, i)
    add("patterns", S.PATTERNS, {
        S.CUSTOMER_SCENARIO: [f"cs-{i}" for i in segments],
        S.IDEATION: [f"id-{i}" for i in segments],
    })
    for g, members in enumerate(groups):
        add(f"cv-{g}", S.CANVAS, {
            S.BRIEF: ["brief"],
            S.EMPATHY_MAP: [f"em-{i}" for i in members],
            S.CUSTOMER_SCENARIO: [f"cs-{i}" for i in members],
            S.IDEATION: [f"id-{i}" for i in members],
            S.PATTERNS: ["patterns"],
        }, g)
    if S.ENVIRONMENT_SCAN in enabled:
        add("env", S.ENVIRONMENT_SCAN, {S.BRIEF: ["brief"]})
    if S.BUSINESS_CASE in enabled:
        add("bc", S.BUSINESS_CASE, {S.BRIEF: ["brief"]})
    if S.TEAM_INFO in enabled:
        add("team", S.TEAM_INFO, {})
    for g in range(len(groups)):
        cycle = {S.CANVAS: [f"cv-{g}"]}
        if S.ENVIRONMENT_SCAN in enabled:
            cycle[S.ENVIRONMENT_SCAN] = ["env"]
        add(f"cy-{g}", S.SWOT_ERRC_CYCLE, cycle, g)
        add(f"st-{g}", S.STORYTELLING, {S.SWOT_ERRC_CYCLE: [f"cy-{g}"]}, g)
        add(f"fs-{g}", S.FUTURE_SCENARIO, {S.SWOT_ERRC_CYCLE: [f"cy-{g}"]}, g)
        pitch = {S.STORYTELLING: [f"st-{g}"], S.SWOT_ERRC_CYCLE: [f"cy-{g}"]}
        if S.TEAM_INFO in enabled:
            pitch[S.TEAM_INFO] = ["team"]
        if S.BUSINESS_CASE in enabled:
            pitch[S.BUSINESS_CASE] = ["bc"]
        add(f"pi-{g}", S.PITCH, pitch, g)
    return rows


ALL_OPTIONAL = frozenset({S.ENVIRONMENT_SCAN, S.BUSINESS_CASE, S.TEAM_INFO})


# --------------------------------------------------------------------------- ids


class TestDeriveArtifactId:
    def test_deterministic(self):
        assert derive_artifact_id("row", ArtifactType.CANVAS, 1) == derive_artifact_id("row", ArtifactType.CANVAS, 1)

    def test_default_index_is_zero(self):
        assert derive_artifact_id("row", ArtifactType.PITCH) == derive_artifact_id("row", ArtifactType.PITCH, 0)

    def test_differs_per_row_type_and_index(self):
        ids = {
            derive_artifact_id("row-a", ArtifactType.CANVAS, 1),
            derive_artifact_id("row-b", ArtifactType.CANVAS, 1),
            derive_artifact_id("row-a", ArtifactType.SWOT, 1),
            derive_artifact_id("row-a", ArtifactType.CANVAS, 2),
        }
        assert len(ids) == 4

    def test_cycle_artifacts_of_different_versions_differ(self):
        swots = {derive_artifact_id("cy", ArtifactType.SWOT, v) for v in range(1, 6)}
        errcs = {derive_artifact_id("cy", ArtifactType.ERRC, v) for v in range(1, 5)}
        canvases = {derive_artifact_id("cy", ArtifactType.CANVAS, v) for v in range(2, 6)}
        assert len(swots | errcs | canvases) == 5 + 4 + 4

    def test_negative_index_rejected(self):
        with pytest.raises(ValueError):
            derive_artifact_id("row", ArtifactType.CANVAS, -1)

    def test_pinned_value_is_the_same_across_processes(self):
        # A fixed value guards the namespace and the name format; running it in
        # fresh interpreters with different hash seeds shows it is process-independent.
        expected = derive_artifact_id("row_1", ArtifactType.CANVAS, 3)
        code = (
            "from bizstruct_domain.schemas import derive_artifact_id, ArtifactType;"
            "print(derive_artifact_id('row_1', ArtifactType.CANVAS, 3))"
        )
        for seed in ("0", "1", "random"):
            out = subprocess.run(
                [sys.executable, "-c", code], capture_output=True, text=True, check=True,
                env={"PYTHONHASHSEED": seed, "PATH": "", "PYTHONPATH": ":".join(sys.path)},
            ).stdout.strip()
            assert out == expected
        assert expected == "f5b0a0e1-3ccc-5870-ad43-e10e9961170e"

    def test_result_is_a_uuid_string(self):
        import uuid

        assert str(uuid.UUID(derive_artifact_id("r", ArtifactType.BRIEF))) == derive_artifact_id("r", ArtifactType.BRIEF)


# --------------------------------------------------------------------------- refs


class TestValidateRowRefs:
    def test_valid_refs(self):
        validate_row_refs(S.CUSTOMER_SCENARIO, {S.EMPATHY_MAP: ["em-0"]})
        validate_row_refs(S.BRIEF, {})

    def test_key_outside_dependencies_rejected(self):
        with pytest.raises(ValueError, match="not a dependency"):
            validate_row_refs(S.CUSTOMER_SCENARIO, {S.EMPATHY_MAP: ["em-0"], S.CANVAS: ["cv"]})

    def test_empty_hard_dependency_rejected(self):
        with pytest.raises(ValueError, match="requires at least one row"):
            validate_row_refs(S.CUSTOMER_SCENARIO, {S.EMPATHY_MAP: []})

    def test_missing_hard_dependency_rejected(self):
        with pytest.raises(ValueError, match="requires at least one row"):
            validate_row_refs(S.CANVAS, {S.BRIEF: ["brief"]})

    def test_optional_dependencies_may_be_absent_or_present(self):
        base = {S.CANVAS: ["cv-0"]}
        validate_row_refs(S.SWOT_ERRC_CYCLE, base)
        validate_row_refs(S.SWOT_ERRC_CYCLE, {**base, S.ENVIRONMENT_SCAN: ["env"]})

    def test_optional_key_for_the_wrong_stage_rejected(self):
        with pytest.raises(ValueError, match="not a dependency"):
            validate_row_refs(S.STORYTELLING, {S.SWOT_ERRC_CYCLE: ["cy"], S.TEAM_INFO: ["t"]})

    def test_every_row_of_the_fixture_has_valid_refs(self):
        for row in make_rows(enabled=ALL_OPTIONAL):
            validate_row_refs(row.stage, row.refs)


# --------------------------------------------------------------------------- ready_rows


class TestReadyRowsMultiInstance:
    @staticmethod
    def _segments_partly_done() -> list[StageRow]:
        # segment 0 finished its empathy map; segment 1's is still PENDING
        return make_rows(
            groups=((0, 1),),
            status={"em-1": P, "cs-0": P, "id-0": P, "cs-1": P, "id-1": P, "patterns": P,
                    "cv-0": P, "cy-0": P, "st-0": P, "fs-0": P, "pi-0": P},
        )

    def test_first_segments_scenario_is_ready_while_patterns_is_not(self):
        ready = ready_rows(self._segments_partly_done())
        assert "cs-0" in ready and "id-0" in ready
        assert "patterns" not in ready

    def test_second_segment_waits_for_its_own_empathy_map(self):
        ready = ready_rows(self._segments_partly_done())
        assert "em-1" in ready  # PENDING with the brief DONE
        assert "cs-1" not in ready and "id-1" not in ready

    def test_order_is_graph_order_then_input_order(self):
        assert ready_rows(self._segments_partly_done()) == ("em-1", "cs-0", "id-0")

    def test_patterns_needs_every_segments_scenario_and_ideation(self):
        rows = make_rows(status={"patterns": P, "cv-0": P, "cv-1": P, "cy-0": P, "cy-1": P,
                                 "st-0": P, "st-1": P, "fs-0": P, "fs-1": P, "pi-0": P, "pi-1": P, "id-1": P})
        assert "patterns" not in ready_rows(rows)
        assert "id-1" in ready_rows(rows)
        done = make_rows(status={"patterns": P, "cv-0": P, "cv-1": P, "cy-0": P, "cy-1": P,
                                 "st-0": P, "st-1": P, "fs-0": P, "fs-1": P, "pi-0": P, "pi-1": P})
        assert ready_rows(done)[0:1] == ("patterns",)

    def test_only_pending_rows_are_ready(self):
        rows = make_rows(default=D)
        assert ready_rows(rows) == ()
        assert ready_rows(make_rows(status={"em-0": R})) == ()

    @pytest.mark.parametrize("blocker", [R, E, StageStatus.AWAITING_DECISION, StageStatus.NEEDS_RETRY])
    def test_a_dependency_that_is_not_done_blocks(self, blocker):
        rows = make_rows(status={"em-0": blocker, "cs-0": P})
        assert "cs-0" not in ready_rows(rows)

    def test_missing_referenced_row_blocks(self):
        rows = [r for r in make_rows(status={"cs-0": P}) if r.id != "em-0"]
        assert "cs-0" not in ready_rows(rows)

    def test_a_dangling_ref_blocks_even_when_the_stage_has_other_done_rows(self):
        rows = make_rows(status={"patterns": P})
        next(r for r in rows if r.id == "patterns").refs[S.IDEATION] = ["id-0", "id-ghost"]
        assert "patterns" not in ready_rows(rows)

    def test_referenced_row_of_the_wrong_stage_blocks(self):
        rows = make_rows(status={"cs-0": P})
        row = next(r for r in rows if r.id == "cs-0")
        row.refs = {S.EMPATHY_MAP: ["brief"]}  # a brief row is not an empathy map
        assert "cs-0" not in ready_rows(rows)

    def test_invalid_refs_block(self):
        rows = make_rows(status={"cs-0": P})
        next(r for r in rows if r.id == "cs-0").refs = {}
        assert "cs-0" not in ready_rows(rows)

    def test_the_brief_row_is_ready_when_pending(self):
        assert ready_rows([StageRow(id="brief", stage=S.BRIEF, status=P)]) == ("brief",)


class TestReadyRowsSplitModel:
    def test_two_canvases_progress_independently(self):
        rows = make_rows(status={
            "cy-0": D, "st-0": P, "fs-0": P, "pi-0": P,        # canvas 0 got further
            "cy-1": P, "st-1": P, "fs-1": P, "pi-1": P,        # canvas 1's cycle can start
        })
        ready = ready_rows(rows)
        assert set(ready) == {"st-0", "fs-0", "cy-1"}
        assert "pi-0" not in ready  # needs storytelling 0 DONE

    def test_a_canvas_with_a_pending_cycle_does_not_block_the_other(self):
        rows = make_rows(status={"cy-0": P, "st-0": P, "fs-0": P, "pi-0": P})
        assert "cy-0" in ready_rows(rows)

    def test_pitch_needs_the_storytelling_and_cycle_of_its_own_canvas(self):
        rows = make_rows(status={"pi-1": P, "st-1": P})
        ready = ready_rows(rows)
        assert "st-1" in ready and "pi-1" not in ready
        assert "pi-1" in ready_rows(make_rows(status={"pi-1": P}))

    def test_canvas_waits_for_the_group_members_only(self):
        rows = make_rows(
            groups=((0,), (1,)),
            status={"cv-0": P, "cv-1": P, "cy-0": P, "cy-1": P, "st-0": P, "st-1": P,
                    "fs-0": P, "fs-1": P, "pi-0": P, "pi-1": P, "id-1": P},
        )
        ready = ready_rows(rows)
        assert "cv-0" in ready and "cv-1" not in ready  # group 1's ideation (id-1) is PENDING


class TestReadyRowsOptional:
    @staticmethod
    def _cycle_pending(enabled, env_status: StageStatus | None):
        status = {"cy-0": P, "cy-1": P, "st-0": P, "st-1": P, "fs-0": P, "fs-1": P, "pi-0": P, "pi-1": P}
        if env_status is not None:
            status["env"] = env_status
        return make_rows(enabled=enabled, status=status)

    def test_disabled_optional_stage_is_ignored(self):
        assert {"cy-0", "cy-1"} <= set(ready_rows(self._cycle_pending(frozenset(), None)))

    def test_enabled_optional_dependency_not_done_blocks_its_consumer(self):
        rows = self._cycle_pending(frozenset({S.ENVIRONMENT_SCAN}), P)
        ready = ready_rows(rows, {S.ENVIRONMENT_SCAN})
        assert "env" in ready and "cy-0" not in ready

    def test_enabled_optional_dependency_done_unblocks(self):
        rows = self._cycle_pending(frozenset({S.ENVIRONMENT_SCAN}), D)
        assert {"cy-0", "cy-1"} <= set(ready_rows(rows, {S.ENVIRONMENT_SCAN}))

    def test_enabled_optional_stage_without_a_row_blocks_the_consumer(self):
        rows = self._cycle_pending(frozenset(), None)  # no env row, but enabled
        assert "cy-0" not in ready_rows(rows, {S.ENVIRONMENT_SCAN})

    def test_consumer_that_does_not_reference_an_enabled_optional_stage_is_blocked(self):
        rows = self._cycle_pending(frozenset({S.ENVIRONMENT_SCAN}), D)
        next(r for r in rows if r.id == "cy-0").refs = {S.CANVAS: ["cv-0"]}
        assert "cy-0" not in ready_rows(rows, {S.ENVIRONMENT_SCAN})

    def test_optional_stage_row_is_not_ready_unless_enabled(self):
        rows = make_rows(enabled=frozenset({S.ENVIRONMENT_SCAN}), status={"env": P})
        assert "env" not in ready_rows(rows)
        assert "env" in ready_rows(rows, {S.ENVIRONMENT_SCAN})

    def test_non_optional_stage_in_enabled_optional_raises(self):
        with pytest.raises(ValueError, match="non-optional"):
            ready_rows(make_rows(), {S.CANVAS})

    def test_pending_team_info_row_is_never_ready(self):
        # user input: no GENERATION_CONTRACTS entry (rule 5b), even if enabled
        assert S.TEAM_INFO not in GENERATION_CONTRACTS
        rows = make_rows(enabled=frozenset({S.TEAM_INFO}), status={"team": P})
        assert "team" not in ready_rows(rows, {S.TEAM_INFO})

    def test_done_team_info_row_unblocks_pitch_when_enabled(self):
        pitch_pending = {"pi-0": P, "pi-1": P}
        rows = make_rows(enabled=frozenset({S.TEAM_INFO}), status={**pitch_pending, "team": D})
        assert {"pi-0", "pi-1"} <= set(ready_rows(rows, {S.TEAM_INFO}))

    def test_enabled_team_info_without_a_row_blocks_pitch(self):
        rows = make_rows(status={"pi-0": P, "pi-1": P})
        assert ready_rows(rows, {S.TEAM_INFO}) == ()

    def test_pending_team_info_blocks_pitch(self):
        rows = make_rows(enabled=frozenset({S.TEAM_INFO}), status={"pi-0": P, "team": P})
        assert "pi-0" not in ready_rows(rows, {S.TEAM_INFO})

    def test_business_case_waits_for_the_brief_and_blocks_pitch_until_done(self):
        rows = make_rows(enabled=frozenset({S.BUSINESS_CASE}), status={"bc": P, "pi-0": P})
        ready = ready_rows(rows, {S.BUSINESS_CASE})
        assert "bc" in ready and "pi-0" not in ready


# --------------------------------------------------------------------------- dependents


class TestDependentRows:
    def test_empathy_map_row_staleness_reaches_its_segment_and_everything_after_patterns(self):
        rows = make_rows()
        dependents = dependent_rows("em-0", rows)
        assert set(dependents) == {"cs-0", "id-0", "patterns", "cv-0", "cv-1", "cy-0", "cy-1",
                                   "st-0", "st-1", "fs-0", "fs-1", "pi-0", "pi-1"}
        assert "em-1" not in dependents and "cs-1" not in dependents

    def test_leaf_row_has_no_dependents(self):
        assert dependent_rows("pi-0", make_rows()) == ()

    def test_split_canvases_do_not_depend_on_each_other(self):
        dependents = dependent_rows("cv-0", make_rows())
        assert set(dependents) == {"cy-0", "st-0", "fs-0", "pi-0"}

    def test_optional_edges_count(self):
        rows = make_rows(enabled=ALL_OPTIONAL)
        assert set(dependent_rows("env", rows)) == {"cy-0", "cy-1", "st-0", "st-1", "fs-0", "fs-1", "pi-0", "pi-1"}
        assert set(dependent_rows("team", rows)) == {"pi-0", "pi-1"}

    def test_result_excludes_the_row_itself_and_is_in_graph_order(self):
        rows = make_rows()
        dependents = dependent_rows("brief", rows)
        assert "brief" not in dependents
        stage_of = {r.id: r.stage for r in rows}
        positions = [_topological(stage_of[rid]) for rid in dependents]
        assert positions == sorted(positions) and positions

    def test_unknown_row_raises(self):
        with pytest.raises(ValueError, match="unknown row id"):
            dependent_rows("nope", make_rows())

    def test_a_cycle_in_refs_does_not_loop_and_never_lists_the_row_itself(self):
        a = StageRow(id="a", stage=S.EMPATHY_MAP, status=D, refs={S.BRIEF: ["b"]})
        b_ = StageRow(id="b", stage=S.BRIEF, status=D, refs={S.EMPATHY_MAP: ["a"]})
        assert dependent_rows("a", [a, b_]) == ("b",)
        assert dependent_rows("b", [a, b_]) == ("a",)


def _topological(stage: Stage) -> int:
    from bizstruct_domain.schemas import STAGE_REGISTRY

    return STAGE_REGISTRY.topological_order().index(stage)


# --------------------------------------------------------------------------- project_status


class TestProjectStatus:
    def test_all_rows_done_and_complete(self):
        assert project_status(make_rows()) == "completed"

    def test_complete_with_all_optional_stages_enabled(self):
        assert project_status(make_rows(enabled=ALL_OPTIONAL), ALL_OPTIONAL) == "completed"

    def test_unified_model_single_canvas_completes(self):
        assert project_status(make_rows(groups=((0, 1),))) == "completed"

    def test_three_segments_split_in_three(self):
        rows = make_rows(n_segments=3, groups=((0,), (1,), (2,)))
        assert project_status(rows) == "completed"

    def test_any_error_row_means_failed(self):
        assert project_status(make_rows(status={"fs-1": E})) == "failed"

    def test_failed_wins_over_running(self):
        assert project_status(make_rows(status={"em-0": E, "cs-0": P})) == "failed"

    @pytest.mark.parametrize("state", [P, R, StageStatus.AWAITING_DECISION, StageStatus.NEEDS_RETRY,
                                       StageStatus.CONSISTENCY_CHECK])
    def test_a_row_that_is_not_done_means_running(self, state):
        assert project_status(make_rows(status={"pi-1": state})) == "running"

    def test_no_rows_is_running(self):
        assert project_status([]) == "running"

    def test_only_the_brief_done_is_not_complete(self):
        assert project_status([StageRow(id="brief", stage=S.BRIEF, status=D)]) == "running"

    def test_a_missing_per_canvas_row_means_running(self):
        rows = [r for r in make_rows() if r.id != "pi-1"]
        assert project_status(rows) == "running"

    def test_a_missing_per_segment_row_means_running(self):
        rows = [r for r in make_rows() if r.id != "id-1"]
        assert project_status(rows) == "running"

    def test_enabled_optional_stage_without_a_row_means_running(self):
        assert project_status(make_rows(), {S.ENVIRONMENT_SCAN}) == "running"

    def test_a_row_of_a_disabled_optional_stage_is_not_complete(self):
        assert project_status(make_rows(enabled=frozenset({S.TEAM_INFO}))) == "running"

    def test_duplicate_single_instance_row_is_not_complete(self):
        rows = make_rows()
        rows.append(StageRow(id="patterns-2", stage=S.PATTERNS, status=D, refs=rows[0].refs))
        assert project_status(rows) == "running"

    def test_non_optional_enabled_stage_raises(self):
        with pytest.raises(ValueError, match="non-optional"):
            project_status(make_rows(), {S.PITCH})


# --------------------------------------------------------------------------- patterns -> canvas rows, artifact rows


class TestCanvasRowsFor:
    def test_unified_model_one_row(self):
        patterns = b.patterns(groups=[CanvasGroup(id="g1", empathy_map_ids=["em-a", "em-b"],
                                                  relation_type=SegmentRelationType.SEGMENTED)])
        assert patterns.branch_decision is CanvasBranch.UNIFIED_MODEL
        specs = canvas_rows_for(patterns)
        assert [(s.group_id, s.empathy_map_ids) for s in specs] == [("g1", ["em-a", "em-b"])]

    def test_split_model_one_row_per_group_in_order(self):
        patterns = b.patterns(
            groups=[
                CanvasGroup(id="g1", empathy_map_ids=["em-a"], relation_type=SegmentRelationType.SEGMENTED),
                CanvasGroup(id="g2", empathy_map_ids=["em-b", "em-c"], relation_type=SegmentRelationType.MULTI_SIDED),
            ],
            branch_decision=CanvasBranch.SPLIT_MODEL,
        )
        specs = canvas_rows_for(patterns)
        assert [(s.group_id, s.empathy_map_ids) for s in specs] == [("g1", ["em-a"]), ("g2", ["em-b", "em-c"])]

    def test_specs_do_not_alias_the_patterns_lists(self):
        patterns = b.patterns(groups=[CanvasGroup(id="g1", empathy_map_ids=["em-a"],
                                                  relation_type=SegmentRelationType.SEGMENTED)])
        canvas_rows_for(patterns)[0].empathy_map_ids.append("x")
        assert patterns.groups[0].empathy_map_ids == ["em-a"]


class TestRowOfArtifact:
    @staticmethod
    def _rows() -> list[StageRow]:
        return [
            StageRow(id="r1", stage=S.CANVAS, status=D,
                     artifacts=[ArtifactRecord(id="a1", type=ArtifactType.CANVAS, data={})]),
            StageRow(id="r2", stage=S.SWOT_ERRC_CYCLE, status=D, artifacts=[
                ArtifactRecord(id="a2", type=ArtifactType.SWOT, data={}),
                ArtifactRecord(id="a3", type=ArtifactType.CANVAS, data={}),
            ]),
            StageRow(id="r3", stage=S.PITCH, status=P),
        ]

    def test_finds_the_row_holding_the_artifact(self):
        rows = self._rows()
        assert row_of_artifact(rows, "a1").id == "r1"
        assert row_of_artifact(rows, "a3").id == "r2"

    def test_unknown_artifact_gives_none(self):
        assert row_of_artifact(self._rows(), "zzz") is None

    def test_row_without_artifacts_never_matches(self):
        assert row_of_artifact(self._rows()[2:], "a1") is None


# --------------------------------------------------------------------------- artifact registry and parsing


def _brief():
    from bizstruct_domain.schemas import Brief

    return Brief(idea_summary="i", industry="x", customer_segment_candidates=["s"], existing_resources=[], gaps=[])


def _artifact_data() -> dict[ArtifactType, dict[str, Any]]:
    """A valid `data` dict for every artifact type, built through the real models."""
    from bizstruct_domain.schemas import (
        BusinessCase, Canvas, CustomerScenario, EmpathyMap, EnvironmentScan, Errc, FutureScenario,
        Ideation, Patterns, Pitch, Storytelling, Swot,
    )

    by_persisted = {CONTRACTS[c][0]: (g, s) for c, (g, s) in GENERATED.items()}

    def built(cls: type[BaseModel]) -> BaseModel:
        generated, system = by_persisted[cls]
        return cls.from_generated(generated, **system)

    return {
        ArtifactType.BRIEF: _brief().model_dump(mode="json"),
        ArtifactType.EMPATHY_MAP: built(EmpathyMap).model_dump(mode="json"),
        ArtifactType.CUSTOMER_SCENARIO: built(CustomerScenario).model_dump(mode="json"),
        ArtifactType.IDEATION: built(Ideation).model_dump(mode="json"),
        ArtifactType.PATTERNS: b.patterns().model_dump(mode="json"),
        ArtifactType.CANVAS: b.canvas().model_dump(mode="json"),
        ArtifactType.SWOT: built(Swot).model_dump(mode="json"),
        ArtifactType.ERRC: built(Errc).model_dump(mode="json"),
        ArtifactType.STORYTELLING: built(Storytelling).model_dump(mode="json"),
        ArtifactType.FUTURE_SCENARIO: built(FutureScenario).model_dump(mode="json"),
        ArtifactType.PITCH: built(Pitch).model_dump(mode="json"),
        ArtifactType.TEAM_INFO: TeamInfo(
            id="team_1", project_id="pr_1",
            members=[TeamMember(name="A", role="R", relevant_experience="E", key_competencies=["c"])],
        ).model_dump(mode="json"),
        ArtifactType.BUSINESS_CASE: built(BusinessCase).model_dump(mode="json"),
        ArtifactType.ENVIRONMENT_SCAN: built(EnvironmentScan).model_dump(mode="json"),
    }


class TestArtifactRegistry:
    def test_fourteen_types(self):
        assert len(ArtifactType) == 14

    def test_models_and_stages_cover_every_type(self):
        assert set(ARTIFACT_MODELS) == set(ArtifactType) == set(ARTIFACT_STAGE)

    def test_stage_mapping(self):
        assert ARTIFACT_STAGE[ArtifactType.SWOT] is Stage.SWOT_ERRC_CYCLE
        assert ARTIFACT_STAGE[ArtifactType.ERRC] is Stage.SWOT_ERRC_CYCLE
        for artifact_type in set(ArtifactType) - {ArtifactType.SWOT, ArtifactType.ERRC}:
            assert ARTIFACT_STAGE[artifact_type].value == artifact_type.value

    def test_every_stage_is_covered_by_some_artifact(self):
        assert set(ARTIFACT_STAGE.values()) == set(Stage)

    def test_models_are_the_persisted_models(self):
        from bizstruct_domain.schemas import Canvas, Errc, Swot

        assert ARTIFACT_MODELS[ArtifactType.CANVAS] is Canvas
        assert ARTIFACT_MODELS[ArtifactType.SWOT] is Swot
        assert ARTIFACT_MODELS[ArtifactType.ERRC] is Errc

    def test_contracts_produce_the_registered_artifacts(self):
        # the generation contracts of a stage convert to the artifact types mapped to it
        for stage, contracts in GENERATION_CONTRACTS.items():
            produced = {CONTRACTS[c][0] for c in contracts}
            expected = {ARTIFACT_MODELS[t] for t, s in ARTIFACT_STAGE.items() if s == stage}
            assert produced == expected, stage


@pytest.mark.parametrize("artifact_type", list(ArtifactType), ids=lambda t: t.value)
class TestParseArtifact:
    def test_valid_data_parses_to_the_persisted_model(self, artifact_type):
        data = _artifact_data()[artifact_type]
        record = ArtifactRecord(id=data.get("id", "brief-id"), type=artifact_type, data=data)
        parsed = parse_artifact(record)
        assert isinstance(parsed, ARTIFACT_MODELS[artifact_type])

    def test_invalid_data_is_a_validation_error(self, artifact_type):
        data = dict(_artifact_data()[artifact_type])
        for key in list(data):
            if key != "id":
                del data[key]
        with pytest.raises(ValidationError):
            parse_artifact(ArtifactRecord(id=data.get("id", "x"), type=artifact_type, data=data))


def test_parse_artifact_rejects_a_record_id_that_differs_from_the_artifact_id():
    data = _artifact_data()[ArtifactType.CANVAS]
    with pytest.raises(ValueError, match="differs"):
        parse_artifact(ArtifactRecord(id="other", type=ArtifactType.CANVAS, data=data))


# --------------------------------------------------------------------------- messages


class TestQueueMessage:
    target = RowTarget(stage_row_id="row_1", stage=S.EMPATHY_MAP, attempt_id="at_1")

    def test_one_target_accepted(self):
        message = QueueMessage(project_id="p", language="en", targets=[self.target])
        assert len(message.targets) == 1

    def test_several_targets_accepted_for_the_agent_phase(self):
        assert len(QueueMessage(project_id="p", language="en", targets=[self.target, self.target]).targets) == 2

    def test_no_target_rejected(self):
        with pytest.raises(ValidationError):
            QueueMessage(project_id="p", language="en", targets=[])

    def test_shape_is_exactly_project_language_targets(self):
        assert set(QueueMessage.model_fields) == {"project_id", "language", "targets"}

    def test_no_params_and_no_force(self):
        assert not {"params", "force", "payload"} & set(QueueMessage.model_fields)

    def test_row_target_shape(self):
        assert set(RowTarget.model_fields) == {"stage_row_id", "stage", "attempt_id"}


class TestStageResult:
    artifact = ArtifactRecord(id="a1", type=ArtifactType.TEAM_INFO, data={"id": "a1"})
    failure = StageFailure(code=StageErrorCode.GENERATION_FAILED, message="bad output")

    def _make(self, **kw):
        base = dict(project_id="p", stage_row_id="r", attempt_id="at")
        return StageResult(**{**base, **kw})

    def test_success_with_artifacts(self):
        assert self._make(status="success", artifacts=[self.artifact]).status == "success"

    def test_success_without_artifacts_rejected(self):
        with pytest.raises(ValidationError, match="requires at least one artifact"):
            self._make(status="success")

    def test_failed_with_error(self):
        assert self._make(status="failed", error=self.failure).error.code is StageErrorCode.GENERATION_FAILED

    def test_failed_without_error_rejected(self):
        with pytest.raises(ValidationError, match="requires an error"):
            self._make(status="failed")

    def test_unknown_status_rejected(self):
        with pytest.raises(ValidationError):
            self._make(status="running", artifacts=[self.artifact])

    def test_carries_the_final_consistency_report(self):
        report = ConsistencyReport(score=5)
        assert self._make(status="success", artifacts=[self.artifact], consistency=report).consistency == report

    def test_cycle_returns_every_version_in_one_result(self):
        artifacts = [ArtifactRecord(id=f"a{i}", type=ArtifactType.CANVAS, data={}) for i in range(4)]
        assert len(self._make(status="success", artifacts=artifacts).artifacts) == 4


class TestSnapshotAndRow:
    def test_snapshot_round_trip_with_enum_keyed_refs(self):
        snapshot = ProjectSnapshot(
            project_id="p", idea="i", language="uk", enabled_optional=[S.TEAM_INFO],
            rows=[StageRow(id="r", stage=S.CUSTOMER_SCENARIO, status=P, refs={S.EMPATHY_MAP: ["e"]})],
        )
        again = ProjectSnapshot.model_validate_json(snapshot.model_dump_json())
        assert again == snapshot
        assert next(iter(again.rows[0].refs)) is S.EMPATHY_MAP

    def test_snapshot_strict_validation_keeps_enum_keys(self):
        row = StageRow(id="r", stage=S.CUSTOMER_SCENARIO, status=P, refs={S.EMPATHY_MAP: ["e"]})
        assert StageRow.model_validate(row.model_dump(), strict=True) == row

    def test_enabled_optional_lives_only_in_the_snapshot(self):
        assert "enabled_optional" in ProjectSnapshot.model_fields
        assert "enabled_optional" not in QueueMessage.model_fields

    def test_row_defaults(self):
        row = StageRow(id="r", stage=S.BRIEF, status=P)
        assert (row.instance_index, row.attempt_id, row.refs, row.artifacts) == (0, None, {}, [])
        assert (row.consistency, row.retry_count, row.error, row.started_at, row.finished_at) == (None, 0, None, None, None)

    def test_row_timestamps_are_datetimes(self):
        from datetime import datetime

        row = StageRow(id="r", stage=S.BRIEF, status=D, started_at="2026-10-04T12:00:00Z")
        assert isinstance(row.started_at, datetime)

    def test_negative_instance_index_and_retry_count_rejected(self):
        with pytest.raises(ValidationError):
            StageRow(id="r", stage=S.BRIEF, status=P, instance_index=-1)
        with pytest.raises(ValidationError):
            StageRow(id="r", stage=S.BRIEF, status=P, retry_count=-1)

    def test_stage_event(self):
        event = StageEvent(project_id="p", stage_row_id="r", stage=S.PITCH, status=D)
        assert event.type == "stage_status"


class TestWireModelsAreSnakeCaseAndSanitized:
    WIRE = [ArtifactRecord, StageRow, ProjectSnapshot, RowTarget, QueueMessage, StageFailure,
            StageResult, StageEvent, wire.CanvasRowSpec]

    @pytest.mark.parametrize("model", WIRE, ids=lambda m: m.__name__)
    def test_inherits_sanitized_model(self, model):
        assert issubclass(model, SanitizedModel)

    @pytest.mark.parametrize("model", WIRE, ids=lambda m: m.__name__)
    def test_field_names_are_snake_case_and_ids_are_strings(self, model):
        for name, info in model.model_fields.items():
            assert name == name.lower() and "-" not in name, name
            if name.endswith("_id"):
                assert info.annotation in (str, str | None), name

    def test_every_class_defined_in_wire_py_is_a_sanitized_model(self):
        import inspect
        from enum import Enum

        for name, cls in inspect.getmembers(wire, inspect.isclass):
            if cls.__module__ == wire.__name__ and not issubclass(cls, Enum):
                assert issubclass(cls, SanitizedModel), name

    def test_nul_is_stripped_from_wire_text(self):
        assert StageFailure(code=StageErrorCode.CHECK_FAILED, message="a\x00b").message == "ab"
