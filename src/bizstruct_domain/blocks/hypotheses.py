"""Output model for the `hypotheses` generation stage.

Testable business hypotheses, each tagged with a `HypothesisCategory`
(Desirability/Viability/Feasibility — Testing Business Ideas) and a
`Quadrant` (importance x uncertainty — see `bizstruct_domain.enums.Quadrant`
for the axis semantics). Coverage of all three categories is enforced here
via a cross-field validator — it previously lived only in bizstruct-ml's
postprocessing, so bizstruct-be could persist a set missing a category.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bizstruct_domain.enums import HypothesisCategory, Quadrant


class Hypothesis(BaseModel):
    """One testable assumption behind the business model."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        pattern=r"^H\d+\.\d+$",
        description="Format H<group>.<index>, e.g. H1.1 — group number matches the quadrant number (q1 -> H1.x).",
    )
    text: str = Field(
        min_length=15,
        max_length=300,
        description=(
            "A falsifiable statement, specific enough that a concrete result would "
            "prove it wrong — must include a number, metric, or percentage."
        ),
    )
    category: HypothesisCategory
    quadrant: Quadrant = Field(
        description=(
            "Importance x uncertainty quadrant for prioritization — see "
            "bizstruct_domain.enums.Quadrant for the full axis definition. "
            "q1: high importance/high uncertainty (test first); q2: high "
            "importance/low uncertainty; q3: low importance/high uncertainty; "
            "q4: low importance/low uncertainty."
        ),
    )


class Hypotheses(BaseModel):
    """Output of the `hypotheses` stage."""

    model_config = ConfigDict(extra="forbid")

    hypotheses: list[Hypothesis] = Field(min_length=5)

    @model_validator(mode="after")
    def _validate_category_coverage(self) -> "Hypotheses":
        present = {h.category for h in self.hypotheses}
        required = {
            HypothesisCategory.DESIRABILITY,
            HypothesisCategory.VIABILITY,
            HypothesisCategory.FEASIBILITY,
        }
        missing = required - present
        if missing:
            missing_values = ", ".join(sorted(m.value for m in missing))
            raise ValueError(f"hypotheses must cover all three categories; missing: {missing_values}")
        return self
