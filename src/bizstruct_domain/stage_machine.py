"""Stage state machine: allowed transitions, dependents, readiness and user actions.

Single source of truth for how a stage's `StageStatus` may change (thesis
§2.3.4, decisions D17, D26) and for which stages can start. Consumers
(bizstruct-be, bizstruct-fe via schemas/stage_states.json) must read the
rules from here rather than re-deriving them. The stage graph itself comes
from `bizstruct_domain.schemas.STAGE_REGISTRY`.
"""

from collections.abc import Iterable
from typing import Protocol

from bizstruct_domain.schemas.chain import STAGE_REGISTRY
from bizstruct_domain.schemas.enums import Stage, StageAction, StageErrorCode, StageStatus

__all__ = [
    "STAGE_IDS",
    "STAGE_TRANSITIONS",
    "StageAction",
    "StageErrorCode",
    "StageLike",
    "StageStatus",
    "available_actions",
    "dependents_of",
    "is_valid_transition",
    "ready_stages",
]

# Graph order (every stage after all its inputs). `Stage` is a StrEnum, so
# members compare and hash equal to their plain string values.
STAGE_IDS: tuple[Stage, ...] = tuple(STAGE_REGISTRY.topological_order())


class StageLike(Protocol):
    """The minimal shape `ready_stages` needs from a stage record.

    Lets callers (e.g. bizstruct-be's ORM `Stage` model) pass their own
    rows without this package depending on that model.
    """

    type: str
    status: StageStatus


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
    (StageStatus.CONSISTENCY_CHECK, StageStatus.DONE),  # no violations, no user decision needed
    (StageStatus.CONSISTENCY_CHECK, StageStatus.AWAITING_DECISION),  # no violations and a user decision is wanted, or retry limit reached with violations attached
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


def _parse_stage(stage_id: str) -> Stage:
    try:
        return Stage(stage_id)
    except ValueError:
        raise ValueError(f"unknown stage id: '{stage_id}'") from None


def is_valid_transition(current: StageStatus, target: StageStatus) -> bool:
    """Whether a stage may move from `current` to `target`."""
    return (current, target) in _STAGE_TRANSITIONS_SET


def dependents_of(stage_id: str) -> tuple[Stage, ...]:
    """The transitive dependents of `stage_id`, in graph order.

    A dependent is any stage whose `depends_on` or `optional_depends_on`
    includes `stage_id`, directly or through another dependent. Optional
    edges count here because this answers "which results may be stale if
    `stage_id` changes": a stage that consumed an optional input is stale
    when that input changes. Whether the consumer actually used the optional
    input in its last run is bizstruct-be's knowledge, not this package's.
    `stage_id` itself is excluded.

    Raises:
        ValueError: If `stage_id` is not a known stage id.
    """
    start = _parse_stage(stage_id)

    direct_dependents: dict[Stage, set[Stage]] = {s: set() for s in STAGE_IDS}
    for stage, definition in STAGE_REGISTRY.stages.items():
        for dep in (*definition.depends_on, *definition.optional_depends_on):
            direct_dependents[dep].add(stage)

    dependents: set[Stage] = set()
    frontier = {start}
    while frontier:
        next_frontier: set[Stage] = set()
        for current in frontier:
            for dependent in direct_dependents[current]:
                if dependent not in dependents:
                    dependents.add(dependent)
                    next_frontier.add(dependent)
        frontier = next_frontier

    return tuple(s for s in STAGE_IDS if s in dependents)


def ready_stages(
    stages: Iterable[StageLike],
    enabled_optional: set[Stage] | None = None,
) -> tuple[Stage, ...]:
    """Stage types that can start now, given the project's stage rows.

    Rows may share a type when the stage allows multiple instances (e.g.
    one empathy_map per segment). Readiness is decided per *type*:

    - A type is *done* iff it has at least one row and every one of its rows
      is `done`.
    - A type is *ready* iff it has at least one `pending` row and every
      hard dependency (`depends_on`) type is done.
    - An optional stage (`is_optional`) is only ready if it is in
      `enabled_optional`.
    - An optional dependency (`optional_depends_on`) blocks its consumer only
      while it is enabled and not done. An enabled optional stage that has no
      row yet is not done, so it blocks its consumer.

    This is deliberately conservative: the graph has no instance links, so
    per-segment progress cannot be expressed. With one `empathy_map` done and
    another still pending, `empathy_map` is not done and nothing downstream
    of it becomes ready, even though a segment-level pipeline could proceed.
    Which rows belong together, retry state and gates are the caller's
    business (bizstruct-be).

    Returns types in graph order, not input order. A dependency type that has
    no rows is treated as not done (so a partial list is safe).

    Raises:
        ValueError: If a row's `type` is not a known stage id, or
            `enabled_optional` contains a stage that is not optional.
    """
    enabled = set(enabled_optional or ())
    not_optional = {s for s in enabled if not STAGE_REGISTRY.stages[s].is_optional}
    if not_optional:
        raise ValueError(f"enabled_optional contains non-optional stages: {not_optional}")

    statuses: dict[Stage, list[StageStatus]] = {}
    for row in stages:
        statuses.setdefault(_parse_stage(row.type), []).append(row.status)

    def is_done(stage: Stage) -> bool:
        rows = statuses.get(stage)
        return bool(rows) and all(s == StageStatus.DONE for s in rows)

    ready: set[Stage] = set()
    for stage, rows in statuses.items():
        definition = STAGE_REGISTRY.stages[stage]
        if StageStatus.PENDING not in rows:
            continue
        if definition.is_optional and stage not in enabled:
            continue
        if not all(is_done(dep) for dep in definition.depends_on):
            continue
        if not all(is_done(dep) for dep in definition.optional_depends_on if dep in enabled):
            continue
        ready.add(stage)
    return tuple(s for s in STAGE_IDS if s in ready)


def available_actions(status: StageStatus) -> tuple[StageAction, ...]:
    """Which user actions are allowed for a stage in `status`.

    `awaiting_decision` gives approve and regenerate, `done` gives
    regenerate, `error` gives retry, everything else gives nothing.
    """
    return _ACTIONS_BY_STATUS.get(status, ())
