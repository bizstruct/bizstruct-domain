"""Output model for the `customer_scenario` generation stage.

BMG, Design -> Scenarios, type 1: customer scenarios (pp. 182-185). A
concrete, detailed usage situation for one persona: who, where, when and
how exactly they interact with the offer. It builds on the empathy map and
makes it tangible. Each scenario comes with open questions about the canvas
blocks it informs most directly: Channels, Customer Relationships, and what
the customer will actually pay for (Revenue Streams).

Shape of one pass: one scenario per empathy map, 1:1, the default the book
supports. How many a project has is bizstruct-be's concern (ADR-0008).

Single language per project; this model doesn't carry the language.
"""

from pydantic import ConfigDict, Field, model_validator

from bizstruct_domain.enums import CanvasSection
from bizstruct_domain.sanitize import SanitizedModel

# The three canvas blocks the book ties customer-scenario questions to.
QUESTION_SECTIONS: frozenset[CanvasSection] = frozenset({
    CanvasSection.CHANNELS,
    CanvasSection.CUSTOMER_RELATIONSHIPS,
    CanvasSection.REVENUE_STREAMS,
})


class ScenarioQuestion(SanitizedModel):
    """An open question the scenario raises about one canvas block."""

    model_config = ConfigDict(extra="forbid")

    section: CanvasSection = Field(
        description="One of channels, customer_relationships, revenue_streams.",
    )
    question: str = Field(min_length=10, max_length=300)


class CustomerScenario(SanitizedModel):
    """Output of the `customer_scenario` stage."""

    model_config = ConfigDict(extra="forbid")

    persona: str = Field(
        min_length=10,
        max_length=200,
        description="Who the protagonist is — the same persona as the empathy map, not a new one.",
    )
    situation: str = Field(
        min_length=40,
        max_length=1000,
        description="Where, when and how exactly the persona uses the offer, told as a short concrete story.",
    )
    open_questions: list[ScenarioQuestion] = Field(min_length=3, max_length=9)

    @model_validator(mode="after")
    def _validate_question_sections(self) -> "CustomerScenario":
        sections = {q.section for q in self.open_questions}
        stray = sections - QUESTION_SECTIONS
        if stray:
            raise ValueError(
                f"open_questions may only address {sorted(s.value for s in QUESTION_SECTIONS)}, "
                f"got {sorted(s.value for s in stray)}"
            )
        missing = QUESTION_SECTIONS - sections
        if missing:
            raise ValueError(f"open_questions must cover every one of the three blocks; missing: {sorted(s.value for s in missing)}")
        return self
