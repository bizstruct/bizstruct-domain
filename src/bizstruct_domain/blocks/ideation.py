"""Output model for the `ideation` generation stage.

BMG, Design -> Ideation (pp. 136-141). The book gives two independent
starting points for generating ideas, and this stage produces both from the
same inputs (brief + one empathy map):

- Epicentre classification: which of the four epicentres of business model
  innovation drive the idea. More than one value means "multiple-epicenter
  driven" in the book's terms. That is why `Epicenter` has no separate
  `multiple_epicenter` value (ADR-0008). The book treats this as a tag-only
  classifier with no separate text artifact.
- "What if...?" questions: provocative challenges to the industry's
  standard assumptions. They are starting points, not solutions. Some are
  expected to stay unanswered, and the domain does not require each one to
  be resolved downstream.

Shape of one pass: one `Ideation` per empathy map. How many a project has is
bizstruct-be's concern (ADR-0008).

Single language per project; this model doesn't carry the language.
"""

from typing import Annotated

from pydantic import ConfigDict, Field, model_validator

from bizstruct_domain.enums import Epicenter
from bizstruct_domain.sanitize import SanitizedModel

WhatIfQuestion = Annotated[str, Field(min_length=10, max_length=300)]


class Ideation(SanitizedModel):
    """Output of the `ideation` stage: epicentre tags plus "What if" questions."""

    model_config = ConfigDict(extra="forbid")

    epicenters: list[Epicenter] = Field(
        min_length=1,
        max_length=len(Epicenter),
        description=(
            "Epicentres driving the idea, each at most once. More than one "
            "value means the idea is multiple-epicenter driven."
        ),
    )
    what_if_questions: list[WhatIfQuestion] = Field(
        min_length=1,
        max_length=10,
        description=(
            "Provocative 'What if...?' questions, each challenging one standard "
            "industry assumption from the brief, tied to an empathy-map pain or "
            "gain where possible. Starting points, not solutions."
        ),
    )

    @model_validator(mode="after")
    def _validate_unique_epicenters(self) -> "Ideation":
        if len(set(self.epicenters)) != len(self.epicenters):
            raise ValueError(f"epicenters must not repeat, got {[e.value for e in self.epicenters]}")
        return self
