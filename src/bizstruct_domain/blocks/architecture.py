"""Output model for the `architecture` generation stage.

Classifies a business model by its epicenter of innovation (Osterwalder &
Pigneur, "Business Model Generation" — Epicentres of Business Model
Innovation) and by its dominant pattern (same book, Part 2 — Patterns),
with bilingual rationale for each choice.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bizstruct_domain.enums import PATTERN_SUBTYPES, Epicenter, Pattern, PatternSubtype


class Architecture(BaseModel):
    """Output of the `architecture` stage: epicenter and pattern classification.

    Depends on `canvas` in the generation chain — the epicenter names which
    part of the Business Model Canvas is the driver of change, so it cannot
    be determined before the canvas exists.
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    epicenter: Epicenter
    epicenter_rationale_uk: str = Field(
        min_length=40,
        max_length=600,
        description="Обґрунтування вибору епіцентру українською мовою.",
    )
    epicenter_rationale_en: str = Field(
        min_length=40,
        max_length=600,
        description="Rationale for the chosen epicenter, in English.",
    )
    pattern: Pattern
    pattern_subtype: PatternSubtype | None = Field(
        default=None,
        description=(
            "Subtype refining the pattern. Only valid for patterns that "
            "define subtypes (free, open_business_model); must be null "
            "for all other patterns."
        ),
    )
    pattern_rationale_uk: str = Field(
        min_length=40,
        max_length=600,
        description="Обґрунтування вибору патерну українською мовою.",
    )
    pattern_rationale_en: str = Field(
        min_length=40,
        max_length=600,
        description="Rationale for the chosen pattern, in English.",
    )

    @model_validator(mode="after")
    def _validate_pattern_subtype(self) -> "Architecture":
        allowed = PATTERN_SUBTYPES.get(self.pattern, set())
        if self.pattern_subtype is None:
            if allowed:
                # subtype is optional even when the pattern defines some
                return self
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
