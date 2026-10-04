import itertools
import random
from dataclasses import dataclass

import pytest

from bizstruct_domain.schemas import STAGE_REGISTRY, Stage, StageAction, StageErrorCode, StageStatus
from bizstruct_domain.stage_machine import (
    STAGE_IDS,
    STAGE_TRANSITIONS,
    available_actions,
    dependents_of,
    is_valid_transition,
    ready_stages,
)

S = StageStatus


@dataclass
class Row:
    type: str
    status: StageStatus


def rows(**statuses: StageStatus | list[StageStatus]) -> list[Row]:
    """Rows from `stage=status` (one row) or `stage=[status, ...]` (several)."""
    out: list[Row] = []
    for stage, status in statuses.items():
        for s in status if isinstance(status, list) else [status]:
            out.append(Row(type=stage, status=s))
    return out


ALLOWED_PAIRS = {
    (S.PENDING, S.RUNNING),
    (S.RUNNING, S.RUNNING),
    (S.RUNNING, S.CONSISTENCY_CHECK),
    (S.RUNNING, S.ERROR),
    (S.RUNNING, S.PENDING),
    (S.CONSISTENCY_CHECK, S.DONE),
    (S.CONSISTENCY_CHECK, S.AWAITING_DECISION),
    (S.CONSISTENCY_CHECK, S.NEEDS_RETRY),
    (S.CONSISTENCY_CHECK, S.PENDING),
    (S.CONSISTENCY_CHECK, S.ERROR),
    (S.AWAITING_DECISION, S.DONE),
    (S.AWAITING_DECISION, S.PENDING),
    (S.NEEDS_RETRY, S.RUNNING),
    (S.DONE, S.PENDING),
    (S.DONE, S.NEEDS_RETRY),
    (S.ERROR, S.PENDING),
}


# ---------------------------------------------------------------- transitions


def test_stage_status_has_exactly_seven_values():
    assert len(list(StageStatus)) == 7


def test_stage_error_code_has_exactly_five_values():
    assert len(list(StageErrorCode)) == 5


def test_exactly_sixteen_transitions_defined():
    assert len(STAGE_TRANSITIONS) == 16
    assert len(set(STAGE_TRANSITIONS)) == 16


def test_transitions_match_the_spec():
    assert set(STAGE_TRANSITIONS) == ALLOWED_PAIRS


def test_needs_retry_to_error_does_not_exist():
    assert (S.NEEDS_RETRY, S.ERROR) not in STAGE_TRANSITIONS


@pytest.mark.parametrize("current,target", sorted(ALLOWED_PAIRS, key=lambda p: (p[0].value, p[1].value)))
def test_allowed_transition_is_valid(current, target):
    assert is_valid_transition(current, target) is True


@pytest.mark.parametrize(
    "current,target",
    sorted(set(itertools.product(StageStatus, StageStatus)) - ALLOWED_PAIRS, key=lambda p: (p[0].value, p[1].value)),
)
def test_forbidden_transition_is_rejected(current, target):
    assert is_valid_transition(current, target) is False


def test_all_pairs_covered_by_the_two_parametrized_tests():
    assert len(ALLOWED_PAIRS) + len(set(itertools.product(StageStatus, StageStatus)) - ALLOWED_PAIRS) == 7 * 7


@pytest.mark.parametrize(
    "status,expected",
    [
        (S.AWAITING_DECISION, (StageAction.APPROVE, StageAction.REGENERATE)),
        (S.DONE, (StageAction.REGENERATE,)),
        (S.ERROR, (StageAction.RETRY,)),
        (S.PENDING, ()),
        (S.RUNNING, ()),
        (S.CONSISTENCY_CHECK, ()),
        (S.NEEDS_RETRY, ()),
    ],
)
def test_available_actions(status, expected):
    assert available_actions(status) == expected


# ---------------------------------------------------------------- graph queries


def test_stage_ids_are_the_registry_topological_order():
    assert STAGE_IDS == tuple(STAGE_REGISTRY.topological_order())
    assert set(STAGE_IDS) == set(Stage) and len(STAGE_IDS) == 13


def test_stage_ids_compare_equal_to_plain_strings():
    assert "brief" in STAGE_IDS
    assert STAGE_IDS[0] == "brief"


def test_dependents_of_leaf_stage_is_empty():
    assert dependents_of("pitch") == ()


def test_dependents_of_brief_is_everything_but_the_independent_root():
    # team_info has no dependencies at all: user input, not derived from the brief.
    assert set(dependents_of("brief")) == set(Stage) - {Stage.BRIEF, Stage.TEAM_INFO}


def test_dependents_of_follows_optional_edges():
    # swot_errc_cycle only optionally consumes environment_scan, but a changed
    # scan still makes a swot that used it stale.
    assert set(dependents_of("environment_scan")) == {
        Stage.SWOT_ERRC_CYCLE, Stage.STORYTELLING, Stage.FUTURE_SCENARIO, Stage.PITCH,
    }
    assert set(dependents_of("team_info")) == {Stage.PITCH}


def test_dependents_of_is_in_graph_order_and_excludes_itself():
    dependents = dependents_of("canvas")
    assert dependents == tuple(s for s in STAGE_IDS if s in set(dependents))
    assert Stage.CANVAS not in dependents


def test_dependents_of_accepts_enum_members():
    assert dependents_of(Stage.TEAM_INFO) == dependents_of("team_info")


def test_dependents_of_unknown_stage_raises():
    with pytest.raises(ValueError, match="unknown stage id"):
        dependents_of("not_a_real_stage")


@pytest.mark.parametrize("removed", ["errc", "hypotheses", "models_options", "assessment", "scenario", "value_map"])
def test_old_stage_ids_are_unknown(removed):
    with pytest.raises(ValueError, match="unknown stage id"):
        dependents_of(removed)
    with pytest.raises(ValueError, match="unknown stage id"):
        ready_stages([Row(type=removed, status=S.PENDING)])


# ---------------------------------------------------------------- ready_stages


def test_all_pending_only_root_is_ready():
    assert ready_stages(rows(brief=S.PENDING, empathy_map=S.PENDING, ideation=S.PENDING)) == (Stage.BRIEF,)


def test_root_done_unblocks_its_direct_dependent():
    assert ready_stages(rows(brief=S.DONE, empathy_map=S.PENDING, ideation=S.PENDING)) == (Stage.EMPATHY_MAP,)


def test_parallel_readiness_when_shared_dependency_done():
    stages = rows(brief=S.DONE, empathy_map=S.DONE, customer_scenario=S.PENDING, ideation=S.PENDING)
    assert ready_stages(stages) == (Stage.CUSTOMER_SCENARIO, Stage.IDEATION)


def test_needs_every_hard_dependency_done():
    base = dict(brief=S.DONE, empathy_map=S.DONE, patterns=S.PENDING)
    assert ready_stages(rows(**base, customer_scenario=S.DONE, ideation=S.PENDING)) == (Stage.IDEATION,)
    assert ready_stages(rows(**base, customer_scenario=S.DONE, ideation=S.DONE)) == (Stage.PATTERNS,)


def test_canvas_needs_all_five_hard_dependencies():
    deps = dict(brief=S.DONE, empathy_map=S.DONE, customer_scenario=S.DONE, ideation=S.DONE, patterns=S.DONE)
    assert ready_stages(rows(**deps, canvas=S.PENDING)) == (Stage.CANVAS,)
    for missing in deps:
        partial = {**deps, missing: S.AWAITING_DECISION}
        assert Stage.CANVAS not in ready_stages(rows(**partial, canvas=S.PENDING))


def test_all_done_nothing_ready():
    assert ready_stages(rows(brief=S.DONE, empathy_map=S.DONE)) == ()


@pytest.mark.parametrize("status", [S.RUNNING, S.DONE, S.ERROR, S.AWAITING_DECISION, S.NEEDS_RETRY, S.CONSISTENCY_CHECK])
def test_never_returns_a_type_without_a_pending_row(status):
    stages = rows(brief=S.DONE, empathy_map=S.DONE, ideation=status)
    assert Stage.IDEATION not in ready_stages(stages)


def test_dependency_awaiting_decision_still_blocks():
    stages = rows(brief=S.DONE, empathy_map=S.DONE, customer_scenario=S.DONE, ideation=S.AWAITING_DECISION, patterns=S.PENDING)
    assert Stage.PATTERNS not in ready_stages(stages)


def test_dependency_type_without_rows_is_not_done():
    assert ready_stages(rows(empathy_map=S.PENDING)) == ()


def test_partial_input_does_not_raise():
    assert ready_stages(rows(brief=S.DONE, empathy_map=S.PENDING, ideation=S.PENDING)) == (Stage.EMPATHY_MAP,)


def test_unknown_stage_type_raises():
    with pytest.raises(ValueError, match="unknown stage id"):
        ready_stages([Row(type="not_a_real_stage", status=S.PENDING)])


def test_output_is_in_graph_order_regardless_of_input_order():
    stages = rows(brief=S.DONE, empathy_map=S.DONE, customer_scenario=S.PENDING, ideation=S.PENDING)
    random.Random(7).shuffle(stages)
    result = ready_stages(stages)
    assert result == (Stage.CUSTOMER_SCENARIO, Stage.IDEATION)
    assert result == tuple(s for s in STAGE_IDS if s in set(result))


def test_empty_input_is_empty():
    assert ready_stages([]) == ()


# -- several rows of one type (allows_multiple_instances) --------------------


def test_two_rows_one_done_one_pending_type_is_not_done():
    # empathy_map still has a pending row: the type is not done, so its
    # dependents are not ready (conservative; see ready_stages docstring)...
    stages = rows(brief=S.DONE, empathy_map=[S.DONE, S.PENDING], customer_scenario=S.PENDING, ideation=S.PENDING)
    # ...while the pending empathy_map row itself is ready to start.
    assert ready_stages(stages) == (Stage.EMPATHY_MAP,)


def test_two_rows_both_done_type_is_done():
    stages = rows(brief=S.DONE, empathy_map=[S.DONE, S.DONE], customer_scenario=S.PENDING, ideation=S.PENDING)
    assert ready_stages(stages) == (Stage.CUSTOMER_SCENARIO, Stage.IDEATION)


def test_two_rows_done_and_running_type_is_not_done():
    stages = rows(brief=S.DONE, empathy_map=[S.DONE, S.RUNNING], customer_scenario=S.PENDING)
    assert ready_stages(stages) == ()


def test_type_with_pending_and_done_rows_is_ready_when_dependencies_done():
    stages = rows(brief=S.DONE, empathy_map=S.DONE, customer_scenario=[S.DONE, S.PENDING])
    assert ready_stages(stages) == (Stage.CUSTOMER_SCENARIO,)


# -- optional stages ---------------------------------------------------------

THROUGH_CANVAS = dict(
    brief=S.DONE, empathy_map=S.DONE, customer_scenario=S.DONE, ideation=S.DONE, patterns=S.DONE, canvas=S.DONE
)


def test_disabled_optional_stage_is_never_ready():
    stages = rows(brief=S.DONE, environment_scan=S.PENDING)
    assert ready_stages(stages) == ()
    assert ready_stages(stages, set()) == ()


def test_enabled_optional_stage_is_ready_when_its_deps_are_done():
    stages = rows(brief=S.DONE, environment_scan=S.PENDING)
    assert ready_stages(stages, {Stage.ENVIRONMENT_SCAN}) == (Stage.ENVIRONMENT_SCAN,)


def test_enabled_optional_stage_still_needs_its_own_deps():
    stages = rows(brief=S.PENDING, environment_scan=S.PENDING)
    assert ready_stages(stages, {Stage.ENVIRONMENT_SCAN}) == (Stage.BRIEF,)


def test_optional_stage_without_dependencies_is_ready_when_enabled():
    assert ready_stages(rows(team_info=S.PENDING), {Stage.TEAM_INFO}) == (Stage.TEAM_INFO,)


def test_disabled_optional_dependency_does_not_block_consumer():
    stages = rows(**THROUGH_CANVAS, swot_errc_cycle=S.PENDING, environment_scan=S.PENDING)
    assert ready_stages(stages) == (Stage.SWOT_ERRC_CYCLE,)


def test_enabled_optional_stage_with_no_row_yet_blocks_its_consumer():
    stages = rows(**THROUGH_CANVAS, swot_errc_cycle=S.PENDING)
    assert ready_stages(stages) == (Stage.SWOT_ERRC_CYCLE,)  # not enabled: no block
    assert ready_stages(stages, {Stage.ENVIRONMENT_SCAN}) == ()


def test_enabled_incomplete_optional_dependency_blocks_consumer():
    stages = rows(**THROUGH_CANVAS, swot_errc_cycle=S.PENDING, environment_scan=S.RUNNING)
    assert ready_stages(stages, {Stage.ENVIRONMENT_SCAN}) == ()


def test_completed_optional_dependency_unblocks_consumer():
    stages = rows(**THROUGH_CANVAS, swot_errc_cycle=S.PENDING, environment_scan=S.DONE)
    assert ready_stages(stages, {Stage.ENVIRONMENT_SCAN}) == (Stage.SWOT_ERRC_CYCLE,)


@pytest.mark.parametrize("pending", [Stage.TEAM_INFO, Stage.BUSINESS_CASE])
def test_enabled_pending_pitch_input_blocks_pitch(pending):
    done = {
        **THROUGH_CANVAS, "swot_errc_cycle": S.DONE, "storytelling": S.DONE,
        "team_info": S.DONE, "business_case": S.DONE,
    }
    done[pending.value] = S.PENDING
    stages = rows(**done, pitch=S.PENDING)
    assert Stage.PITCH not in ready_stages(stages, {Stage.TEAM_INFO, Stage.BUSINESS_CASE})
    assert Stage.PITCH in ready_stages(stages)


def test_enabling_a_non_optional_stage_raises():
    with pytest.raises(ValueError, match="non-optional"):
        ready_stages(rows(brief=S.PENDING), {Stage.CANVAS})
