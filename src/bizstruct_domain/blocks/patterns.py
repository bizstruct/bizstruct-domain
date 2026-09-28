"""Output model for the `patterns` generation stage.

BMG, Patterns (pp. 56-119). A structural classifier, not a creative step. It
reads every (customer_scenario, ideation) pair of the project and produces:

- 0-5 pattern tags for the whole project. The five patterns are not an
  exhaustive list (so zero tags is valid), and one idea can fit several at
  once.
- The A/B decision: one shared canvas, or one canvas per customer segment.
  This is only a classification field. Creating the canvas instances is
  bizstruct-be's job (ADR-0008).

Replaces the `architecture` block, which merged the epicentre (now
`ideation`) with a single dominant pattern and ran after the canvas instead
of feeding it.

The per-pattern canvas layout templates the book gives (e.g. pp. 86-87 for
multi-sided platforms) are static reference knowledge, not generated
output, so they are not part of this model.
"""

from pydantic import ConfigDict, Field, model_validator

from bizstruct_domain.enums import PATTERN_SUBTYPES, CanvasBranchingDecision, Pattern, PatternSubtype
from bizstruct_domain.sanitize import SanitizedModel

# Carried over from the former architecture block's rationale fields
# (measured against experiments/results/ there, see git history).
_RATIONALE_KWARGS = dict(min_length=40, max_length=750)

_MIN_SEGMENTS_FOR_MULTIPLE = 2


class PatternTag(SanitizedModel):
    """One business model pattern the project fits, with its subtype."""

    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    pattern: Pattern
    subtype: PatternSubtype | None = Field(
        default=None,
        description=(
            "Subtype refining the pattern. Required for patterns that "
            "define subtypes (free, open_business_model) — freemium, "
            "ad-supported, and bait-and-hook are distinct economics and "
            "must be told apart; must be null for all other patterns."
        ),
    )
    rationale: str = Field(
        **_RATIONALE_KWARGS,
        description="Why the project fits this pattern, in the project's language.",
    )

    @model_validator(mode="after")
    def _validate_subtype(self) -> "PatternTag":
        allowed = PATTERN_SUBTYPES.get(self.pattern, set())
        if self.subtype is None:
            if allowed:
                allowed_values = ", ".join(sorted(s.value for s in allowed))
                raise ValueError(
                    f"pattern '{self.pattern.value}' requires a subtype; choose one of: {allowed_values}"
                )
            return self
        if not allowed:
            raise ValueError(
                f"pattern '{self.pattern.value}' does not define subtypes, "
                f"but subtype='{self.subtype.value}' was given"
            )
        if self.subtype not in allowed:
            allowed_values = ", ".join(sorted(s.value for s in allowed))
            raise ValueError(
                f"subtype '{self.subtype.value}' is not valid for "
                f"pattern '{self.pattern.value}'; allowed subtypes: {allowed_values}"
            )
        return self


class Patterns(SanitizedModel):
    """Output of the `patterns` stage: pattern tags plus the A/B canvas decision."""

    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    pattern_tags: list[PatternTag] = Field(
        min_length=0,
        max_length=len(Pattern),
        description="Patterns the whole project fits, each at most once. May be empty.",
    )
    segment_count: int = Field(
        ge=1,
        description=(
            "How many customer segments (customer_scenario/ideation pairs) this "
            "classification was made over. Set from the stage's inputs by the "
            "caller, not judged by the LLM. It exists only so the validators "
            "below can check pattern/decision constraints that depend on it."
        ),
    )
    branching_decision: CanvasBranchingDecision
    branching_rationale: str = Field(
        **_RATIONALE_KWARGS,
        description=(
            "Why one shared canvas or one per segment: similarity of the "
            "segments, synergy between them, or conflict, in the project's language."
        ),
    )

    @model_validator(mode="after")
    def _validate_tags_and_decision(self) -> "Patterns":
        patterns = [t.pattern for t in self.pattern_tags]
        if len(set(patterns)) != len(patterns):
            raise ValueError(f"pattern_tags must not repeat a pattern, got {[p.value for p in patterns]}")
        if Pattern.MULTI_SIDED_PLATFORM in patterns and self.segment_count < _MIN_SEGMENTS_FOR_MULTIPLE:
            raise ValueError(
                "multi_sided_platform needs at least two interdependent customer "
                f"segments (BMG, Patterns, pp. 76-79), got segment_count={self.segment_count}"
            )
        if (
            self.branching_decision is CanvasBranchingDecision.B_BRANCHING
            and self.segment_count < _MIN_SEGMENTS_FOR_MULTIPLE
        ):
            raise ValueError(
                "b_branching means one canvas per segment and needs at least two "
                f"segments, got segment_count={self.segment_count}"
            )
        return self
