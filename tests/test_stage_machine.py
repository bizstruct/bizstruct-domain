import itertools
import random
from dataclasses import dataclass

import pytest

from bizstruct_domain.chain import STAGES
from bizstruct_domain.enums import StageAction, StageErrorCode, StageStatus
from bizstruct_domain.stage_machine import (
    STAGE_IDS,
    STAGE_TRANSITIONS,
    available_actions,
    dependents_of,
    is_valid_transition,
    ready_stages,
)


@dataclass
class _FakeStage:
    type: str
    status: StageStatus

ALLOWED_PAIRS = {
    (StageStatus.PENDING, StageStatus.RUNNING),
    (StageStatus.RUNNING, StageStatus.RUNNING),
    (StageStatus.RUNNING, StageStatus.CONSISTENCY_CHECK),
    (StageStatus.RUNNING, StageStatus.ERROR),
    (StageStatus.RUNNING, StageStatus.PENDING),
    (StageStatus.CONSISTENCY_CHECK, StageStatus.DONE),
    (StageStatus.CONSISTENCY_CHECK, StageStatus.AWAITING_DECISION),
    (StageStatus.CONSISTENCY_CHECK, StageStatus.NEEDS_RETRY),
    (StageStatus.CONSISTENCY_CHECK, StageStatus.PENDING),
    (StageStatus.CONSISTENCY_CHECK, StageStatus.ERROR),
    (StageStatus.AWAITING_DECISION, StageStatus.DONE),
    (StageStatus.AWAITING_DECISION, StageStatus.PENDING),
    (StageStatus.NEEDS_RETRY, StageStatus.RUNNING),
    (StageStatus.DONE, StageStatus.PENDING),
    (StageStatus.DONE, StageStatus.NEEDS_RETRY),
    (StageStatus.ERROR, StageStatus.PENDING),
}


def test_stage_status_has_exactly_seven_values():
    assert len(list(StageStatus)) == 7


def test_stage_error_code_has_exactly_five_values():
    assert len(list(StageErrorCode)) == 5


def test_exactly_sixteen_transitions_defined():
    assert len(STAGE_TRANSITIONS) == 16
    assert len(set(STAGE_TRANSITIONS)) == 16  # no duplicates


def test_transitions_match_the_spec():
    assert set(STAGE_TRANSITIONS) == ALLOWED_PAIRS


def test_needs_retry_to_error_does_not_exist():
    assert (StageStatus.NEEDS_RETRY, StageStatus.ERROR) not in STAGE_TRANSITIONS


@pytest.mark.parametrize("current,target", sorted(ALLOWED_PAIRS, key=lambda p: (p[0].value, p[1].value)))
def test_allowed_transition_is_valid(current, target):
    assert is_valid_transition(current, target) is True


@pytest.mark.parametrize(
    "current,target",
    sorted(
        set(itertools.product(StageStatus, StageStatus)) - ALLOWED_PAIRS,
        key=lambda p: (p[0].value, p[1].value),
    ),
)
def test_forbidden_transition_is_rejected(current, target):
    assert is_valid_transition(current, target) is False


def test_all_pairs_covered_by_the_two_parametrized_tests():
    assert len(ALLOWED_PAIRS) + len(set(itertools.product(StageStatus, StageStatus)) - ALLOWED_PAIRS) == 7 * 7


def test_stage_ids_matches_chain_order():
    assert STAGE_IDS == tuple(stage.id for stage in STAGES)


def test_dependents_of_leaf_stage_is_empty():
    assert dependents_of("pitch") == ()


def test_dependents_of_brief_is_everything_else():
    assert set(dependents_of("brief")) == {s.id for s in STAGES if s.id != "brief"}


def test_dependents_of_is_in_graph_order():
    dependents = dependents_of("canvas")
    assert dependents == tuple(s.id for s in STAGES if s.id in set(dependents))


def test_dependents_of_unknown_stage_raises():
    with pytest.raises(ValueError):
        dependents_of("not_a_real_stage")


@pytest.mark.parametrize(
    "status,expected",
    [
        (StageStatus.AWAITING_DECISION, (StageAction.APPROVE, StageAction.REGENERATE)),
        (StageStatus.DONE, (StageAction.REGENERATE,)),
        (StageStatus.ERROR, (StageAction.RETRY,)),
        (StageStatus.PENDING, ()),
        (StageStatus.RUNNING, ()),
        (StageStatus.CONSISTENCY_CHECK, ()),
        (StageStatus.NEEDS_RETRY, ()),
    ],
)
def test_available_actions(status, expected):
    assert available_actions(status) == expected


# ready_stages: exercised over the real STAGES graph's
# brief -> empathy_map -> value_map -> models_options -> {canvas, scenario}
# chain, since canvas and scenario share the exact same depends_on and are
# where the graph's only fan-out (parallel readiness) sits (thesis §2.2.7).
_CHAIN_IDS = ("brief", "empathy_map", "value_map", "models_options", "canvas", "scenario")


def _chain_stages(**statuses: StageStatus) -> list[_FakeStage]:
    return [_FakeStage(type=stage_id, status=statuses.get(stage_id, StageStatus.PENDING)) for stage_id in _CHAIN_IDS]


def test_ready_stages_all_pending_only_root_is_ready():
    assert ready_stages(_chain_stages()) == ("brief",)


def test_ready_stages_root_done_unblocks_its_direct_dependent():
    stages = _chain_stages(brief=StageStatus.DONE)
    assert ready_stages(stages) == ("empathy_map",)


def test_ready_stages_needs_every_direct_dependency_done():
    stages = _chain_stages(brief=StageStatus.DONE, empathy_map=StageStatus.DONE, value_map=StageStatus.DONE)
    assert ready_stages(stages) == ("models_options",)


def test_ready_stages_parallel_readiness_when_shared_dependency_done():
    stages = _chain_stages(
        brief=StageStatus.DONE,
        empathy_map=StageStatus.DONE,
        value_map=StageStatus.DONE,
        models_options=StageStatus.DONE,
    )
    assert ready_stages(stages) == ("canvas", "scenario")


def test_ready_stages_all_done_nothing_ready():
    stages = _chain_stages(**{stage_id: StageStatus.DONE for stage_id in _CHAIN_IDS})
    assert ready_stages(stages) == ()


@pytest.mark.parametrize(
    "status",
    [
        StageStatus.RUNNING,
        StageStatus.DONE,
        StageStatus.ERROR,
        StageStatus.AWAITING_DECISION,
        StageStatus.NEEDS_RETRY,
        StageStatus.CONSISTENCY_CHECK,
    ],
)
def test_ready_stages_never_returns_a_non_pending_stage(status):
    stages = _chain_stages(
        brief=StageStatus.DONE,
        empathy_map=StageStatus.DONE,
        value_map=StageStatus.DONE,
        models_options=StageStatus.DONE,
        canvas=status,
    )
    assert "canvas" not in ready_stages(stages)


def test_ready_stages_dependency_awaiting_decision_still_blocks():
    stages = _chain_stages(
        brief=StageStatus.DONE,
        empathy_map=StageStatus.DONE,
        value_map=StageStatus.DONE,
        models_options=StageStatus.AWAITING_DECISION,
    )
    assert "canvas" not in ready_stages(stages)
    assert "scenario" not in ready_stages(stages)


def test_ready_stages_partial_input_does_not_raise():
    stages = [
        _FakeStage(type="brief", status=StageStatus.DONE),
        _FakeStage(type="empathy_map", status=StageStatus.PENDING),
        _FakeStage(type="value_map", status=StageStatus.PENDING),
    ]
    assert ready_stages(stages) == ("empathy_map",)


def test_ready_stages_unknown_stage_type_raises():
    with pytest.raises(ValueError):
        ready_stages([_FakeStage(type="not_a_real_stage", status=StageStatus.PENDING)])


def test_ready_stages_output_order_is_domain_graph_order_regardless_of_input_order():
    stages = _chain_stages(
        brief=StageStatus.DONE,
        empathy_map=StageStatus.DONE,
        value_map=StageStatus.DONE,
        models_options=StageStatus.DONE,
    )
    shuffled = stages.copy()
    random.shuffle(shuffled)
    result = ready_stages(shuffled)
    assert result == ("canvas", "scenario")
    assert result == tuple(stage_id for stage_id in STAGE_IDS if stage_id in set(result))


def test_ready_stages_empty_input_is_empty():
    assert ready_stages([]) == ()
