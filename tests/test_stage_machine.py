import itertools

import pytest

from bizstruct_domain.chain import STAGES
from bizstruct_domain.enums import StageAction, StageErrorCode, StageStatus
from bizstruct_domain.stage_machine import (
    STAGE_IDS,
    STAGE_TRANSITIONS,
    available_actions,
    dependents_of,
    is_valid_transition,
)

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
