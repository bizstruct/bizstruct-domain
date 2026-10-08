"""Cross-artifact consistency checking: shared result types and the
registry of deterministic rules.

This module answers a different question than the per-model validators
elsewhere in the package. A `@model_validator` on e.g. `Patterns` can only
see `Patterns`' own fields, so it can catch internal contradictions
("MULTI_SIDED_PLATFORM is tagged but branch_decision says SPLIT_MODEL")
but not whether `Patterns` is a *faithful* result of the `CustomerScenario`/
`Ideation` instances it was generated from. That second question needs
several already-generated artifacts at once, which no single artifact's
own validator can see.

Two different situations call for this, and a rule can be either kind:

- Tier 1, same referent: several artifacts about the same thing (e.g. one
  EmpathyMap + its CustomerScenario + its Ideation, all about the same
  persona) contradicting each other directly.
- Tier 2, derivation: one stage's output checked against the inputs it
  actually depends on (chain.py's `depends_on` edges) -- did it faithfully
  use them, not ignore or invent something ungrounded.

Boundary of this module (see docs/adr for the fuller rationale): it holds
the *rules* (pure predicates, no I/O) and the *result shape*. It does not
gather artifacts from storage and does not call a judge model -- both are
bizstruct-be's / bizstruct-ml's job, which is where the data and the LLM
client respectively live. `RuleInput`/`applies_to` let a caller discover,
for a given set of completed stages, which rules just became checkable
and how many instances of each stage type to gather -- the same
"open the graph, don't hardcode it" principle as `chain.py`'s
`next_available`, applied to rules instead of stages.
"""

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field, model_validator

from .artifact_types import ARTIFACT_HOLDERS, ARTIFACT_STAGE, ArtifactType
from .enums import Stage
from .fields import SanitizedModel


class ConsistencyViolation(SanitizedModel):
    """One thing a rule found wrong, or worth flagging, between artifacts."""

    rule_id: str = Field(
        ...,
        description="Which rule raised this (matches ConsistencyRule.id).",
        examples=["multi_sided_requires_signal"],
    )
    severity: Literal["error", "warning"] = Field(
        ...,
        description="'error': the artifacts are actually inconsistent. "
                     "'warning': plausible but worth a second look "
                     "(mainly reserved for judge-model results, not "
                     "deterministic rules, which should mostly raise "
                     "errors precisely because they're checking a hard "
                     "condition).",
        examples=["error"],
    )
    message: str = Field(
        ...,
        description="Human-readable explanation, specific enough to act on.",
        examples=[
            "Patterns tags MULTI_SIDED_PLATFORM, but none of the "
            "CustomerScenario instances for this project has "
            "interdependence_signal=True.",
        ],
    )
    artifact_ids: list[str] = Field(
        ...,
        min_length=1,
        description="ids of the specific artifact instances involved, "
                     "so the caller can point the user at them.",
        examples=[["patterns_001", "customer_scenario_001", "customer_scenario_002"]],
    )


class ConsistencyReport(SanitizedModel):
    """Result of running one or more rules against a set of artifacts."""

    score: int = Field(
        ...,
        ge=1,
        le=5,
        description="1 (severely inconsistent) to 5 (fully consistent). "
                     "How the caller derives this from `violations` "
                     "(e.g. from a judge model, or from counting errors) "
                     "is not fixed here.",
        examples=[4],
    )
    violations: list[ConsistencyViolation] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(v.severity == "error" for v in self.violations)


class Arity(StrEnum):
    """How many instances of an artifact type a rule input takes (ADR-0012)."""

    ONE = "one"
    """Exactly one instance; several candidates are an ambiguity error."""
    MANY = "many"
    """Every instance of the group, as one list."""
    EACH = "each"
    """The check runs once per instance; the other inputs are gathered once."""
    FINAL = "final"
    """The final version of a versioned artifact (`canvas`, `swot`), derived by
    `cycle.select_final_version` over the Swots of the cycle row."""


class RuleInput(SanitizedModel):
    """One of a rule's inputs: which artifact TYPE, and how many instances.

    The stage is derived: `stage` is the type's home stage. A stage is not
    enough to name an input because `swot_errc_cycle` holds Swot and Errc (several
    of each) and Canvas v2..v5 (ADR-0012). The check function takes, per
    input and in order: a single instance (`ONE`, `EACH`, `FINAL`) or a list
    (`MANY`). Where the instances come from is the caller's job: for each holding
    stage of the type (`ARTIFACT_HOLDERS`) the instances of the rows the fresh
    row's `refs` name under that stage, else of the DONE rows of that stage in
    the closure, plus the fresh row's own artifacts of the type.
    """

    artifact: ArtifactType
    arity: Arity
    optional: bool = Field(
        default=False,
        description="True for an input that only exists in some projects "
                     "(chain.py's is_optional stages: team_info, "
                     "business_case, environment_scan). An optional "
                     "input never blocks discovery on its own; if it is "
                     "absent the caller passes None (ONE/FINAL) or an empty "
                     "list (MANY) in its position, and EACH has nothing to run.",
    )

    @model_validator(mode="after")
    def final_is_for_versioned_artifacts(self) -> "RuleInput":
        if self.arity is Arity.FINAL and self.artifact not in (ArtifactType.CANVAS, ArtifactType.SWOT):
            raise ValueError(f"FINAL applies to canvas and swot only, not {self.artifact.value}.")
        return self

    @property
    def stage(self) -> Stage:
        """The home stage of the artifact type."""
        return ARTIFACT_STAGE[self.artifact]

    @property
    def required_stages(self) -> frozenset[Stage]:
        """Stages that must be completed for this input to exist: the home stage, and for `FINAL`
        the cycle (the final version is known only when the loop has run)."""
        if self.arity is Arity.FINAL:
            return frozenset({Stage.SWOT_ERRC_CYCLE})
        return frozenset({self.stage})

    @property
    def read_stages(self) -> tuple[Stage, ...]:
        """Stages whose fresh row can trigger a check on this input: the home stage, and for the
        multi-instance kinds (`MANY`, `EACH`, `FINAL`) every stage holding the type."""
        if self.arity in (Arity.MANY, Arity.EACH, Arity.FINAL):
            return tuple(dict.fromkeys((self.stage, *ARTIFACT_HOLDERS[self.artifact])))
        return (self.stage,)


def _is_checkable(inputs: tuple[RuleInput, ...], completed: set[Stage]) -> bool:
    """Shared discovery rule for ConsistencyRule and JudgeCheck.

    Every non-optional input's required stages must be completed. If the
    rule declares optional inputs at all, at least one of them must be
    completed too -- otherwise the rule has nothing optional to check
    (e.g. a pitch-vs-sources check with neither TeamInfo nor
    BusinessCase present).
    """
    required = set().union(*(i.required_stages for i in inputs if not i.optional))
    optional = set().union(*(i.required_stages for i in inputs if i.optional))
    if not required <= completed:
        return False
    return not optional or bool(optional & completed)


def _applies_to(inputs: tuple[RuleInput, ...]) -> tuple[Stage, ...]:
    return tuple(dict.fromkeys(stage for i in inputs for stage in i.read_stages))


def _check_single_each(inputs: Sequence[RuleInput]) -> None:
    if sum(i.arity is Arity.EACH for i in inputs) > 1:
        raise ValueError("At most one input may be EACH: two would mean a cross product of instances.")


class InputBindingError(ValueError):
    """The candidates do not fit the inputs: a required one is missing, or a `ONE` is ambiguous."""


def bind_inputs(inputs: Sequence[RuleInput], candidates: Mapping[ArtifactType, Sequence[BaseModel]]) -> list[tuple[Any, ...]]:
    """Apply the arity of each input to the instances the caller gathered, giving the argument
    tuples for `rule.check(*args)` / the judge payload (pure, no I/O).

    `candidates[type]` holds EVERY instance of the type in scope (for a Canvas: all versions of
    the group's lineage, so the caller gathers v1 from the `canvas` row and v2..v5 from the cycle
    row, see `ARTIFACT_HOLDERS`). Per input:

    - `ONE`: exactly one candidate, else `InputBindingError` (several is the ambiguity error);
      an absent optional input is `None`.
    - `MANY`: the list of candidates; empty is an error unless the input is optional.
    - `EACH`: one argument tuple per candidate (the other inputs are bound once); an absent
      optional input yields no tuples, a missing required one is an error.
    - `FINAL`: the final version (`cycle.final_swot` / `cycle.final_canvas`, which use
      `select_final_version` over the Swots in `candidates[SWOT]`); absent optional -> `None`.
    """
    from .cycle import final_canvas, final_swot  # local: cycle imports models that import this module's neighbours

    _check_single_each(inputs)
    fixed: list[Any] = []
    each_index: int | None = None
    each_items: list[Any] = []
    for position, spec in enumerate(inputs):
        pool = list(candidates.get(spec.artifact, ()))
        name = spec.artifact.value
        if not pool:
            if spec.arity is Arity.MANY and spec.optional:
                fixed.append([])
            elif spec.arity is Arity.EACH and spec.optional:
                each_index = position
                fixed.append(None)
            elif spec.optional:
                fixed.append(None)
            else:
                raise InputBindingError(f"no {name} instance among the candidates")
            continue
        if spec.arity is Arity.ONE:
            if len(pool) > 1:
                raise InputBindingError(f"ambiguous input: {len(pool)} {name} instances, expected one")
            fixed.append(pool[0])
        elif spec.arity is Arity.MANY:
            fixed.append(pool)
        elif spec.arity is Arity.EACH:
            each_index, each_items = position, pool
            fixed.append(None)
        else:  # FINAL
            swots = list(candidates.get(ArtifactType.SWOT, ()))
            if not swots:
                raise InputBindingError("no swot instance among the candidates: the final version is undefined")
            try:
                fixed.append(final_swot(swots) if spec.artifact is ArtifactType.SWOT else final_canvas(pool, swots))
            except ValueError as e:
                raise InputBindingError(str(e)) from e
    if each_index is None:
        return [tuple(fixed)]
    return [tuple(item if i == each_index else value for i, value in enumerate(fixed)) for item in each_items]


class ConsistencyRule:
    """One deterministic, pure check: no I/O, no LLM call.

    Not a Pydantic model -- this is a registry entry (code + metadata),
    not project data to validate. `check`'s positional parameters follow
    `inputs` in order, each `ONE` input as a single artifact instance and
    each `MANY` input as a list of instances -- that pairing is what lets
    a caller call `rule.check(*gathered_args)` generically, without
    importing the rule by name or knowing its Python signature ahead of
    time.
    """

    def __init__(
        self,
        id: str,
        inputs: tuple[RuleInput, ...],
        check: Callable[..., list[ConsistencyViolation]],
    ) -> None:
        _check_single_each(inputs)
        self.id = id
        self.inputs = inputs
        self.check = check

    @property
    def applies_to(self) -> tuple[Stage, ...]:
        """All stages this rule reads, optional ones included (the cycle
        too for versioned canvases). For deciding whether the rule can run
        now, use `is_checkable`, not a subset test against this."""
        return _applies_to(self.inputs)

    def is_checkable(self, completed: set[Stage]) -> bool:
        return _is_checkable(self.inputs, completed)


class JudgeCheck(SanitizedModel):
    """A consistency claim that needs a judge model, not a deterministic
    rule -- comparing the *meaning* of free text across artifacts, which
    no pure predicate can do (see module docstring: e.g. does Canvas's
    Value Proposition content actually reflect the EmpathyMap/
    CustomerScenario it was supposedly derived from, or does it introduce
    unsupported claims).

    Declared the same way as a ConsistencyRule -- `id` + `inputs` with
    arity -- so a caller can discover a checkable JudgeCheck exactly like
    it discovers a checkable ConsistencyRule (same `applies_to` pattern),
    without a separate mechanism for "what am I supposed to run now".
    The difference is `instruction` instead of `check`: no domain code
    executes this. bizstruct-ml serializes the gathered instances,
    sends `instruction` plus that data to a judge model (a different
    model family than the generator, per the evaluation methodology),
    and parses the response as a `ConsistencyReport` -- the same result
    shape a deterministic rule produces.
    """

    id: str
    inputs: tuple[RuleInput, ...]
    instruction: str = Field(
        ...,
        description="What the judge model should verify, phrased so it "
                     "can be dropped into a prompt alongside the "
                     "serialized instances named in `inputs`. Should say "
                     "what to ignore (style, tone) as well as what to "
                     "check, so the judge doesn't penalize things this "
                     "check isn't about.",
    )

    @model_validator(mode="after")
    def at_most_one_each(self) -> "JudgeCheck":
        _check_single_each(self.inputs)
        return self

    @property
    def applies_to(self) -> tuple[Stage, ...]:
        return _applies_to(self.inputs)

    def is_checkable(self, completed: set[Stage]) -> bool:
        return _is_checkable(self.inputs, completed)


JUDGE_CHECKS: list[JudgeCheck] = [
    JudgeCheck(
        id="empathy_map_customer_scenario_persona_consistency",
        inputs=(
            RuleInput(artifact=ArtifactType.EMPATHY_MAP, arity=Arity.ONE),
            RuleInput(artifact=ArtifactType.CUSTOMER_SCENARIO, arity=Arity.ONE),
        ),
        instruction=(
            "You will see one EmpathyMap (pains, gains, thinks_and_feels, "
            "says_and_does, sees, hears for one persona) and the "
            "CustomerScenario generated for that same persona "
            "(situation_narrative, open_questions).\n\n"
            "This is a Tier-1 check: both artifacts describe the SAME "
            "person at the same point in time, so they must not "
            "directly contradict each other. Check specifically for:\n"
            "- A capability, attitude, or behavior in situation_narrative "
            "that contradicts pains or thinks_and_feels (e.g. the "
            "EmpathyMap says the persona is frustrated by or struggles "
            "with something the CustomerScenario shows them doing "
            "confidently and without friction).\n"
            "- A stated need or motivation in situation_narrative that "
            "has no basis in, or actively conflicts with, gains.\n"
            "- Demographic or situational facts (persona_demographics) "
            "contradicted by details of the scenario's setting.\n\n"
            "Do not flag the CustomerScenario for simply not mentioning "
            "every EmpathyMap detail -- omission is expected and is not "
            "a contradiction. Only flag an explicit or clearly implied "
            "conflict between a specific claim in each artifact."
        ),
    ),
    JudgeCheck(
        id="canvas_grounded_in_customer_insights",
        inputs=(
            RuleInput(artifact=ArtifactType.EMPATHY_MAP, arity=Arity.MANY),
            RuleInput(artifact=ArtifactType.CUSTOMER_SCENARIO, arity=Arity.MANY),
            RuleInput(artifact=ArtifactType.CANVAS, arity=Arity.ONE),
        ),
        instruction=(
            "You will see one or more EmpathyMap instances (each with "
            "pains and gains for one persona), the matching "
            "CustomerScenario instances (situation_narrative, "
            "open_questions), and one Canvas (nine sections, each a "
            "list of short cards).\n\n"
            "Check whether the Canvas's content is actually grounded in "
            "the EmpathyMap/CustomerScenario instances, not invented "
            "independently of them:\n"
            "- Value Propositions should address specific pains/gains "
            "that appear in the EmpathyMap instances, not generic "
            "claims unconnected to any of them.\n"
            "- Customer Segments should correspond to the personas "
            "described, not introduce a segment absent from every "
            "EmpathyMap.\n"
            "- Channels and Customer Relationships should engage with "
            "the open_questions raised in the CustomerScenario "
            "instances where those questions exist, rather than "
            "ignoring them.\n\n"
            "Do not penalize wording, tone, or which specific phrasing "
            "was chosen -- only whether the substance of each card can "
            "be traced back to something in the upstream artifacts. "
            "A card is a violation only if it has no discernible basis "
            "in any of the provided EmpathyMap/CustomerScenario "
            "instances."
        ),
    ),
    JudgeCheck(
        id="pitch_risk_analysis_grounded_in_swot",
        inputs=(
            RuleInput(artifact=ArtifactType.SWOT, arity=Arity.FINAL),
            RuleInput(artifact=ArtifactType.PITCH, arity=Arity.ONE),
        ),
        instruction=(
            "You will see one Swot (four clusters, each with "
            "axis_statements and threats) and one Pitch generated "
            "afterward, including its risk_analysis list.\n\n"
            "Every Swot rates a fixed catalog of threats, so it always "
            "contains all of them, including ones scored 1 or 2 that the "
            "analysis considers weak. Only a threat with score >= 3 "
            "counts as a real risk here.\n\n"
            "Pitch.risk_analysis is supposed to be a pitch-facing "
            "restatement of the real risks the Swot found, not a "
            "generic or invented risk list. Check whether each entry in "
            "risk_analysis can be traced back to a negative "
            "axis_statement (score < 0) or a threat with score >= 3 -- "
            "paraphrase and simplification for an external audience are "
            "expected and fine, but a risk with no discernible basis in "
            "the Swot at all is a violation.\n\n"
            "Also flag the reverse gap only if it's severe: a threat "
            "with score 5, or a negative axis_statement with importance "
            ">= 8, that risk_analysis omits entirely. Minor omissions are "
            "expected -- a pitch is a summary, not an exhaustive list."
        ),
    ),

    JudgeCheck(
        id="ideation_grounds_pattern_tags",
        inputs=(
            RuleInput(artifact=ArtifactType.IDEATION, arity=Arity.MANY),
            RuleInput(artifact=ArtifactType.PATTERNS, arity=Arity.ONE),
        ),
        instruction=(
            "You will see one or more Ideation instances (each with an "
            "EpicenterClassification -- tags and rationale -- and "
            "what_if_questions for one segment) and one Patterns "
            "(pattern_tags, each with a rationale, plus the branch "
            "decision).\n\n"
            "Check whether each PatternTag's rationale is actually "
            "connected to the epicenter classifications and/or "
            "what_if_questions provided, not a generic justification "
            "that could apply to any idea. It is fine for a pattern to "
            "draw on more than one Ideation instance, or on a "
            "what_if_question rather than the epicenter tag -- flag it "
            "only if a PatternTag's rationale has no discernible link "
            "to anything in the provided Ideation instances at all."
        ),
    ),
    JudgeCheck(
        id="pitch_optional_sections_grounded_in_sources",
        inputs=(
            RuleInput(artifact=ArtifactType.PITCH, arity=Arity.ONE),
            RuleInput(artifact=ArtifactType.TEAM_INFO, arity=Arity.ONE, optional=True),
            RuleInput(artifact=ArtifactType.BUSINESS_CASE, arity=Arity.ONE, optional=True),
        ),
        instruction=(
            "You will see one Pitch (with team_section and "
            "financial_analysis_section) and the TeamInfo/BusinessCase "
            "it declares as sources for those two sections. Only one of "
            "TeamInfo/BusinessCase may be relevant if the other's "
            "corresponding Pitch field is null -- in that case, skip the "
            "check for the missing side.\n\n"
            "Pitch.optional_sections_match_ids already guarantees "
            "team_section is non-null exactly when team_info_id is set "
            "(same for business_case_id/financial_analysis_section). "
            "That only proves a section of TEXT exists, not that the "
            "text reflects the source. Check whether team_section "
            "actually describes the members, roles, and experience in "
            "TeamInfo (not a generic 'experienced team' claim "
            "unconnected to who is named), and whether "
            "financial_analysis_section reflects BusinessCase's "
            "market_benchmarks, sales_scenarios, and cost/funding "
            "figures rather than inventing numbers absent from it."
        ),
    ),
    JudgeCheck(
        id="business_case_environment_scan_relevant_to_brief",
        inputs=(
            RuleInput(artifact=ArtifactType.BRIEF, arity=Arity.ONE),
            RuleInput(artifact=ArtifactType.BUSINESS_CASE, arity=Arity.ONE, optional=True),
            RuleInput(artifact=ArtifactType.ENVIRONMENT_SCAN, arity=Arity.ONE, optional=True),
        ),
        instruction=(
            "You will see one Brief (industry, idea_summary) and, where "
            "present, a BusinessCase and/or EnvironmentScan generated "
            "from it. If one of the two is not provided, skip the check "
            "for that one.\n\n"
            "Both are supposed to be triggered by Brief.industry: check "
            "whether BusinessCase.market_benchmarks and "
            "EnvironmentScan's four force lists actually describe the "
            "industry named in Brief, not a generic or mismatched "
            "industry's benchmarks. This is a coarse plausibility check, "
            "not a fact-check of the figures themselves -- flag only a "
            "clear industry mismatch (e.g. Brief names a food delivery "
            "business and BusinessCase discusses SaaS pricing "
            "benchmarks with no connection to food delivery)."
        ),
    ),
]


CONSISTENCY_RULES: list[ConsistencyRule] = []


def register(id: str, inputs: tuple[RuleInput, ...]):
    """Decorator: add a function to CONSISTENCY_RULES as a ConsistencyRule.

    `inputs` must list the rule's parameters in the same order the
    decorated function takes them, one RuleInput per parameter.
    """

    def decorator(fn: Callable[..., list[ConsistencyViolation]]) -> Callable[..., list[ConsistencyViolation]]:
        CONSISTENCY_RULES.append(ConsistencyRule(id=id, inputs=inputs, check=fn))
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
#
# Deliberately few for now: these two are concrete illustrations of the
# pattern (one Tier-1-shaped, one Tier-2-shaped), not a claim of coverage.
# See docs/adr open questions for the rest of the candidate list.

from .customer_scenario import CustomerScenario
from .enums import SegmentRelationType
from .pattern import Patterns


@register(
    "multi_sided_requires_signal",
    (
        RuleInput(artifact=ArtifactType.CUSTOMER_SCENARIO, arity=Arity.MANY),
        RuleInput(artifact=ArtifactType.PATTERNS, arity=Arity.ONE),
    ),
)
def multi_sided_requires_signal(
    customer_scenarios: list[CustomerScenario],
    patterns: Patterns,
) -> list[ConsistencyViolation]:
    """Tier 2 (derivation): every group with relation_type MULTI_SIDED must be
    grounded in an interdependence signal of ITS OWN segments: at least one
    CustomerScenario whose `empathy_map_id` is in the group's
    `empathy_map_ids` carries interdependence_signal=True. Checked per group,
    whether or not Patterns carries the MULTI_SIDED_PLATFORM tag (ADR-0012 D5):
    a signal in another group of a split project does not count.
    `Patterns.multi_sided_requires_two_maps` checks the *group size* from
    Patterns' own fields; this rule checks that the *signal it was supposedly
    grounded in* actually exists upstream, which no validator on Patterns
    alone can see. A group whose scenarios were not provided has no signal.
    """
    violations: list[ConsistencyViolation] = []
    for group in patterns.groups:
        if group.relation_type != SegmentRelationType.MULTI_SIDED:
            continue
        members = set(group.empathy_map_ids)
        own = [s for s in customer_scenarios if s.empathy_map_id in members]
        if any(s.interdependence_signal for s in own):
            continue
        violations.append(
            ConsistencyViolation(
                rule_id="multi_sided_requires_signal",
                severity="error",
                message=(
                    f"Group {group.id} (empathy maps {', '.join(group.empathy_map_ids)}) has "
                    "relation_type MULTI_SIDED, but none of the CustomerScenario instances of "
                    "its own segments has interdependence_signal=True. Give the group another "
                    "relation_type, or move into it the segments whose scenarios carry the signal."
                ),
                artifact_ids=[patterns.id, *[s.id for s in own]],
            )
        )
    return violations


from .canvas import Canvas
from .storytelling import Storytelling
from .future_scenario import FutureScenario
from .errc import Errc
from .swot import Swot
from .pitch import Pitch
from .brief import Brief
from .ideation import Ideation
from .optional_inputs import TeamInfo, BusinessCase


from .pattern import CanvasGroup


@register(
    "canvas_group_id_is_known",
    (
        RuleInput(artifact=ArtifactType.PATTERNS, arity=Arity.ONE),
        RuleInput(artifact=ArtifactType.CANVAS, arity=Arity.EACH),
    ),
)
def canvas_group_id_is_known(
    patterns: Patterns,
    canvas: Canvas,
) -> list[ConsistencyViolation]:
    """Tier 2 (derivation): Canvas.group_id must name a group that
    Patterns actually produced. Patterns' own validators check its
    groups are internally consistent (branch_decision, MULTI_SIDED
    sizing); nothing checks that a specific Canvas's group_id is one of
    those groups rather than a dangling reference.
    """
    known_group_ids = {g.id for g in patterns.groups}
    if canvas.group_id in known_group_ids:
        return []

    return [
        ConsistencyViolation(
            rule_id="canvas_group_id_is_known",
            severity="error",
            message=(
                f"Canvas {canvas.id} references group_id '{canvas.group_id}', "
                f"which is not one of the groups Patterns {patterns.id} produced "
                f"({sorted(known_group_ids)})."
            ),
            artifact_ids=[canvas.id, patterns.id],
        )
    ]


@register(
    "future_scenario_references_nonempty_sections",
    (
        RuleInput(artifact=ArtifactType.CANVAS, arity=Arity.FINAL),
        RuleInput(artifact=ArtifactType.FUTURE_SCENARIO, arity=Arity.ONE),
    ),
)
def future_scenario_references_nonempty_sections(
    canvas: Canvas,
    future_scenario: "FutureScenario",
) -> list[ConsistencyViolation]:
    """Tier 2 (derivation): same shape as
    storytelling_references_nonempty_sections, for the other consumer of
    the final canvas. Every AdaptationQuestion, in every variant, must
    point at a section that has cards on the referenced canvas.
    """
    violations: list[ConsistencyViolation] = []
    for variant in future_scenario.variants:
        for question in variant.adaptation_questions:
            cards = canvas.get_section(question.section)
            if not cards:
                violations.append(
                    ConsistencyViolation(
                        rule_id="future_scenario_references_nonempty_sections",
                        severity="error",
                        message=(
                            f"FutureScenario variant '{variant.name}' asks an "
                            f"adaptation question about section "
                            f"'{question.section.value}', but that section is "
                            f"empty on canvas {canvas.id}."
                        ),
                        artifact_ids=[future_scenario.id, canvas.id],
                    )
                )
    return violations


@register(
    "errc_move_targets_correct_canvas_version",
    (
        RuleInput(artifact=ArtifactType.CANVAS, arity=Arity.MANY),
        RuleInput(artifact=ArtifactType.ERRC, arity=Arity.EACH),
    ),
)
def errc_move_targets_correct_canvas_version(
    canvas_versions: list[Canvas],
    errc: "Errc",
) -> list[ConsistencyViolation]:
    """Tier 2 (derivation): ErrcMove.action_field_consistency already
    checks that target_card_text is well-formed for the action. It
    cannot check that the card actually exists on the *specific* canvas
    version Errc.canvas_id/from_version names -- that requires the
    other canvas versions to tell a formally identical card apart from
    one that merely has matching text on a different version.
    """
    source_canvas = next((c for c in canvas_versions if c.id == errc.canvas_id), None)
    if source_canvas is None:
        return [
            ConsistencyViolation(
                rule_id="errc_move_targets_correct_canvas_version",
                severity="error",
                message=f"Errc {errc.id} references canvas_id '{errc.canvas_id}', which was not provided.",
                artifact_ids=[errc.id],
            )
        ]

    violations: list[ConsistencyViolation] = []
    for move in errc.moves:
        if move.target_card_text is None:
            continue
        cards = source_canvas.get_section(move.target_section)
        if not any(c.text == move.target_card_text for c in cards):
            violations.append(
                ConsistencyViolation(
                    rule_id="errc_move_targets_correct_canvas_version",
                    severity="error",
                    message=(
                        f"ErrcMove targets '{move.target_card_text}' in section "
                        f"'{move.target_section.value}', but no card with that "
                        f"exact text exists in that section on canvas "
                        f"{source_canvas.id} (version {source_canvas.version}), "
                        f"the version Errc {errc.id} claims to edit."
                    ),
                    artifact_ids=[errc.id, source_canvas.id],
                )
            )
    return violations


from .optional_inputs import EnvironmentScan


@register(
    "swot_environment_scan_reference_is_known",
    (
        RuleInput(artifact=ArtifactType.SWOT, arity=Arity.EACH),
        RuleInput(artifact=ArtifactType.ENVIRONMENT_SCAN, arity=Arity.ONE),
    ),
)
def swot_environment_scan_reference_is_known(
    swot: "Swot",
    environment_scan: EnvironmentScan,
) -> list[ConsistencyViolation]:
    """Tier 2 (derivation), optional-input variant: if Swot declares
    environment_scan_id, it must be the EnvironmentScan actually
    provided, not a stale or mistaken id. This is a referential check
    only -- whether Opportunities/Threats actually *used* that scan's
    content (rather than merely citing its id) is the judge's job
    (canvas_grounded_in_customer_insights is the template for that kind
    of check; a symmetrical one for environment_scan is not written
    yet).
    """
    if swot.environment_scan_id is None:
        return []
    if swot.environment_scan_id == environment_scan.id:
        return []
    return [
        ConsistencyViolation(
            rule_id="swot_environment_scan_reference_is_known",
            severity="error",
            message=(
                f"Swot {swot.id} declares environment_scan_id "
                f"'{swot.environment_scan_id}', but the EnvironmentScan "
                f"provided has id '{environment_scan.id}'."
            ),
            artifact_ids=[swot.id, environment_scan.id],
        )
    ]


@register(
    "storytelling_references_nonempty_sections",
    (
        RuleInput(artifact=ArtifactType.CANVAS, arity=Arity.FINAL),
        RuleInput(artifact=ArtifactType.STORYTELLING, arity=Arity.ONE),
    ),
)
def storytelling_references_nonempty_sections(
    canvas: Canvas,
    storytelling: Storytelling,
) -> list[ConsistencyViolation]:
    """Tier 2 (derivation): every CanvasReference in the narrative must
    point at a section that actually has cards in the referenced canvas.
    A reference to an empty section means the narrative describes a
    part of the model that, on this canvas, does not exist.
    """
    violations: list[ConsistencyViolation] = []
    for ref in storytelling.canvas_references:
        cards = canvas.get_section(ref.section)
        if not cards:
            violations.append(
                ConsistencyViolation(
                    rule_id="storytelling_references_nonempty_sections",
                    severity="error",
                    message=(
                        f"Storytelling references section '{ref.section.value}', "
                        f"but that section is empty on canvas {canvas.id}."
                    ),
                    artifact_ids=[storytelling.id, canvas.id],
                )
            )
    return violations
