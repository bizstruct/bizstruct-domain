"""Output model for the `assessment` generation stage (SWOT).

BMG, Strategy -> Evaluating Business Models (pp. 212-225). A diagnosis of
one canvas; it edits nothing (ERRC does that). The book assesses the canvas
in four clusters rather than block by block (see `SWOTCluster` /
`SWOT_CLUSTER_SECTIONS`), each with Strengths, Weaknesses, Opportunities
and Threats. Strengths and Weaknesses come from the canvas alone.
Opportunities and Threats also use the environment scan when that optional
input is present.

`importance` and `certainty` (1-10) come from the book's format for
Strength/Weakness statements. They are carried on Opportunities and Threats
too as a project extension, because the Canvas -> SWOT -> ERRC stopping
rule weighs Weaknesses + Threats by importance. The domain only holds these
numbers. Computing the weighted sum and deciding when to stop is
bizstruct-be/bizstruct-ml's job (ADR-0008).

The book also rates each S/W statement on a 1-5 strong/weak scale. That is
not a separate field here: a statement's quadrant (strengths vs.
weaknesses) already carries the direction, and `importance` carries the
weight.
"""

from pydantic import ConfigDict, Field, model_validator

from bizstruct_domain.enums import SWOTCluster
from bizstruct_domain.sanitize import SanitizedModel


class SWOTStatement(SanitizedModel):
    """One statement in a SWOT quadrant, tied to this canvas's actual content."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=10, max_length=400)
    importance: int = Field(ge=1, le=10, description="Importance to the business model, 1-10.")
    certainty: int = Field(ge=1, le=10, description="Certainty of the evaluation, 1-10.")


class ClusterAssessment(SanitizedModel):
    """The four SWOT quadrants for one canvas cluster."""

    model_config = ConfigDict(extra="forbid")

    cluster: SWOTCluster
    strengths: list[SWOTStatement] = Field(min_length=1, max_length=5)
    weaknesses: list[SWOTStatement] = Field(min_length=1, max_length=5)
    opportunities: list[SWOTStatement] = Field(min_length=1, max_length=5)
    threats: list[SWOTStatement] = Field(min_length=1, max_length=5)


class Assessment(SanitizedModel):
    """Output of the `assessment` stage: one entry per cluster, in `SWOTCluster` order."""

    model_config = ConfigDict(extra="forbid")

    clusters: list[ClusterAssessment] = Field(min_length=len(SWOTCluster), max_length=len(SWOTCluster))

    @model_validator(mode="after")
    def _validate_cluster_order(self) -> "Assessment":
        actual = tuple(c.cluster for c in self.clusters)
        expected = tuple(SWOTCluster)
        if actual != expected:
            raise ValueError(
                f"clusters must be exactly {[c.value for c in expected]} in that order, "
                f"got {[c.value for c in actual]}"
            )
        return self
