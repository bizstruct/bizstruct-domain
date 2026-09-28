"""Output model for the `scenario` generation stage (future scenario).

BMG, Design -> Scenarios, type 2: future scenarios (pp. 186-189). Not to be
confused with `customer_scenario` (type 1 from the same chapter).

Repurposed from the former before/after user-journey scenario (ADR-0008),
which had no basis in the book's Scenarios chapter. A stress test of the
final canvas against a few possible futures of its environment. It is
diagnostic like SWOT, not an edit like ERRC, and does not change the canvas.

- 2-4 uncertainty drivers: key factors that may develop differently. The
  book advises keeping to a few; the upper bound of 4 is this project's.
- 2-4 scenarios combining extreme values of the drivers (e.g. a 2x2 matrix
  for two drivers), each with a short narrative and adaptation questions
  tied to specific canvas areas (`ScenarioAdaptationArea`).

The book's optional follow-up of building a full business model per
scenario is not part of this stage.

Single language per project; this model doesn't carry the language.
"""

from typing import Annotated

from pydantic import ConfigDict, Field, model_validator

from bizstruct_domain.enums import ScenarioAdaptationArea
from bizstruct_domain.sanitize import SanitizedModel

UncertaintyDriver = Annotated[str, Field(min_length=10, max_length=300)]


class AdaptationQuestion(SanitizedModel):
    """How one canvas area would have to adapt in this future."""

    model_config = ConfigDict(extra="forbid")

    area: ScenarioAdaptationArea
    question: str = Field(min_length=10, max_length=300)


class FutureScenarioCase(SanitizedModel):
    """One possible future, from one combination of driver values."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    narrative: str = Field(min_length=40, max_length=1200)
    adaptation_questions: list[AdaptationQuestion] = Field(
        min_length=1,
        max_length=len(ScenarioAdaptationArea),
        description="One question per significant canvas area, each area at most once.",
    )

    @model_validator(mode="after")
    def _validate_unique_areas(self) -> "FutureScenarioCase":
        areas = [q.area for q in self.adaptation_questions]
        if len(set(areas)) != len(areas):
            raise ValueError(f"adaptation_questions must not repeat an area, got {[a.value for a in areas]}")
        return self


class FutureScenario(SanitizedModel):
    """Output of the `scenario` stage."""

    model_config = ConfigDict(extra="forbid")

    uncertainty_drivers: list[UncertaintyDriver] = Field(min_length=2, max_length=4)
    scenario_matrix: list[FutureScenarioCase] = Field(min_length=2, max_length=4)
