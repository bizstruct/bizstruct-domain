"""Stage state machine: allowed transitions, dependents, and user actions.

Single source of truth for how a stage's `StageStatus` may change (thesis
§2.3.4, decisions D17, D26). Consumers (bizstruct-be, bizstruct-fe via
schemas/stage_states.json) must read the rules from here rather than
re-deriving them.
"""

from bizstruct_domain.chain import STAGES
from bizstruct_domain.enums import StageAction, StageErrorCode, StageStatus

STAGE_IDS: tuple[str, ...] = tuple(stage.id for stage in STAGES)

# The 16 allowed (from, to) transitions, in a fixed order so exports (e.g.
# schemas/stage_states.json) are deterministic. `needs_retry -> error` does
# not exist: reaching the retry limit is not an error, the latest artifact
# goes back to the user (D26). `error` is only for external failures and
# cancellation.
STAGE_TRANSITIONS: tuple[tuple[StageStatus, StageStatus], ...] = (
    # pending
    (StageStatus.PENDING, StageStatus.RUNNING),  # dependencies done
    # running
    (StageStatus.RUNNING, StageStatus.RUNNING),  # invalid structure, retry
    (StageStatus.RUNNING, StageStatus.CONSISTENCY_CHECK),  # artifact generated
    (StageStatus.RUNNING, StageStatus.ERROR),  # generation failed
    (StageStatus.RUNNING, StageStatus.PENDING),  # upstream reset
    # consistency_check
    (StageStatus.CONSISTENCY_CHECK, StageStatus.DONE),  # no violations, agent mode
    (StageStatus.CONSISTENCY_CHECK, StageStatus.AWAITING_DECISION),  # no violations, or retry limit reached with violations attached
    (StageStatus.CONSISTENCY_CHECK, StageStatus.NEEDS_RETRY),  # violation in this stage
    (StageStatus.CONSISTENCY_CHECK, StageStatus.PENDING),  # violation in an upstream stage
    (StageStatus.CONSISTENCY_CHECK, StageStatus.ERROR),  # check failed
    # awaiting_decision
    (StageStatus.AWAITING_DECISION, StageStatus.DONE),  # user approves, also with open violations
    (StageStatus.AWAITING_DECISION, StageStatus.PENDING),  # regeneration or upstream reset
    # needs_retry
    (StageStatus.NEEDS_RETRY, StageStatus.RUNNING),  # automatic repair, retry_count +1
    # done
    (StageStatus.DONE, StageStatus.PENDING),  # user regeneration or upstream reset
    (StageStatus.DONE, StageStatus.NEEDS_RETRY),  # violation traced to this stage
    # error
    (StageStatus.ERROR, StageStatus.PENDING),  # user retry
)

_STAGE_TRANSITIONS_SET: frozenset[tuple[StageStatus, StageStatus]] = frozenset(STAGE_TRANSITIONS)

_ACTIONS_BY_STATUS: dict[StageStatus, tuple[StageAction, ...]] = {
    StageStatus.AWAITING_DECISION: (StageAction.APPROVE, StageAction.REGENERATE),
    StageStatus.DONE: (StageAction.REGENERATE,),
    StageStatus.ERROR: (StageAction.RETRY,),
}


def is_valid_transition(current: StageStatus, target: StageStatus) -> bool:
    """Whether a stage may move from `current` to `target`."""
    return (current, target) in _STAGE_TRANSITIONS_SET


def dependents_of(stage_id: str) -> tuple[str, ...]:
    """The transitive dependents of `stage_id`, in graph order.

    A dependent is any stage whose `depends_on` includes `stage_id`,
    directly or through another dependent. `stage_id` itself is excluded.
    """
    if stage_id not in STAGE_IDS:
        raise ValueError(f"unknown stage id: '{stage_id}'")

    direct_dependents: dict[str, set[str]] = {stage.id: set() for stage in STAGES}
    for stage in STAGES:
        for dep in stage.depends_on:
            if dep in direct_dependents:
                direct_dependents[dep].add(stage.id)

    dependents: set[str] = set()
    frontier = {stage_id}
    while frontier:
        next_frontier: set[str] = set()
        for current_id in frontier:
            for dependent_id in direct_dependents.get(current_id, ()):
                if dependent_id not in dependents:
                    dependents.add(dependent_id)
                    next_frontier.add(dependent_id)
        frontier = next_frontier

    return tuple(stage.id for stage in STAGES if stage.id in dependents)


def available_actions(status: StageStatus) -> tuple[StageAction, ...]:
    """Which user actions are allowed for a stage in `status`.

    `awaiting_decision` gives approve and regenerate, `done` gives
    regenerate, `error` gives retry, everything else gives nothing.
    """
    return _ACTIONS_BY_STATUS.get(status, ())
