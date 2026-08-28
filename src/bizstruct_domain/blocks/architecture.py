"""Output model for the `architecture` generation stage.

Classifies a business model by its epicenter of innovation (Osterwalder &
Pigneur, "Business Model Generation" — Epicentres of Business Model
Innovation) and by its dominant pattern (same book, Part 2 — Patterns),
with a rationale for each choice.

Single language per project (see data-quality brief part E / ADR-0006) —
`epicenter_rationale`/`pattern_rationale` are one field each, not `_uk`/
`_en` pairs. Language is a property of the project, decided by
bizstruct-be and passed to bizstruct-ml; this model doesn't carry it.
"""

from pydantic import ConfigDict, Field, model_validator

from bizstruct_domain.enums import PATTERN_SUBTYPES, Epicenter, Pattern, PatternSubtype
from bizstruct_domain.sanitize import SanitizedModel

# Measured against experiments/results/ (4 models x 5 ideas): at
# max_length=600, pattern_rationale was truncated mid-word 35-40% of the
# time, epicenter_rationale 10-15% — raised with headroom for both
# uniformly rather than per-field, since they share the same "justify a
# classification choice" shape. See the data-quality brief's part D and
# the task summary.
_RATIONALE_KWARGS = dict(min_length=40, max_length=750)


class Architecture(SanitizedModel):
    """Output of the `architecture` stage: epicenter and pattern classification.

    Depends on `canvas` in the generation chain — the epicenter names which
    part of the Business Model Canvas is the driver of change, so it cannot
    be determined before the canvas exists.
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    epicenter: Epicenter
    epicenter_rationale: str = Field(
        **_RATIONALE_KWARGS,
        description="Rationale for the chosen epicenter, in the project's language.",
    )
    pattern: Pattern
    pattern_subtype: PatternSubtype | None = Field(
        default=None,
        description=(
            "Subtype refining the pattern. Required for patterns that "
            "define subtypes (free, open_business_model) — freemium, "
            "ad-supported, and bait-and-hook are distinct economics and "
            "must be told apart; must be null for all other patterns."
        ),
    )
    pattern_rationale: str = Field(
        **_RATIONALE_KWARGS,
        description="Rationale for the chosen pattern, in the project's language.",
    )

    @model_validator(mode="after")
    def _validate_pattern_subtype(self) -> "Architecture":
        allowed = PATTERN_SUBTYPES.get(self.pattern, set())
        if self.pattern_subtype is None:
            if allowed:
                allowed_values = ", ".join(sorted(s.value for s in allowed))
                raise ValueError(
                    f"pattern '{self.pattern.value}' requires a pattern_subtype; "
                    f"choose one of: {allowed_values}"
                )
            return self
        if not allowed:
            raise ValueError(
                f"pattern '{self.pattern.value}' does not define subtypes, "
                f"but pattern_subtype='{self.pattern_subtype.value}' was given"
            )
        if self.pattern_subtype not in allowed:
            allowed_values = ", ".join(sorted(s.value for s in allowed))
            raise ValueError(
                f"pattern_subtype '{self.pattern_subtype.value}' is not valid for "
                f"pattern '{self.pattern.value}'; allowed subtypes: {allowed_values}"
            )
        return self
