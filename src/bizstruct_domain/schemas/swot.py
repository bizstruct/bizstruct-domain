from typing import Literal

from pydantic import Field, model_validator
from .fields import SanitizedModel

from .enums import SwotCluster


class SwotAxisStatement(SanitizedModel):
    """
        Represents a statement for a SWOT axis (Strengths, Weaknesses, Opportunities, Threats).
    """
    positive_statement: str = Field(
        ...,
        description="A statement describing a positive aspect (Strength or Opportunity).",
        examples=["Our product has a unique feature that competitors lack."],
    )
    negative_statement: str = Field(
        ...,
        description="A statement describing a negative aspect (Weakness or Threat).",
        examples=["Our production costs are higher than the industry average."],
    )
    score: Literal[-5, -4, -3, -2, -1, 1, 2, 3, 4, 5] = Field(
        ...,
        description=(
            "A score representing the impact of the statement, from -5 (very negative)"
            " to 5 (very positive). A forced choice: there is no neutral 0 (the book's"
            " bipolar scale), so every statement takes a side."
        ),
        examples=[-5, -1, 1, 5],
    )
    importance: int = Field(
        ...,
        ge=1,
        le=10,
        description=(
            "A score representing the importance of the statement,"
            " ranging from 1 (least important) to 10 (most important)."
        ),
        examples=[2, 5, 9],
    )
    certainty: int = Field(
        ...,
        ge=1,
        le=10,
        description=(
            "A score representing the certainty of the statement,"
            " ranging from 1 (least certain) to 10 (most certain)."
        ),
        examples=[3, 7, 10],
    )


class SwotOpportunityThreat(SanitizedModel):
    """
        Represents a single Opportunity or Threat item, per the BMG document's
        Evaluating Business Models format (pp. 220-223): each generative
        question is paired with a 1-5 scale. The book gives no caption for
        this scale; the working interpretation used here is "how strongly
        this applies to this model" (1 = barely, 5 = very strongly).
    """
    text: str = Field(
        ...,
        description="The opportunity or threat statement (typically phrased as, "
                     "or derived from, one of the book's generative questions).",
        examples=["Could we generate recurring revenues by converting products into services?"],
    )
    score: int = Field(
        ...,
        ge=1,
        le=5,
        description="How strongly this applies to this model: 1 (barely) to 5 (very strongly). "
                     "Interpretation is a project decision; the book's pages give the scale "
                     "with no caption.",
        examples=[2, 3, 5],
    )


class SwotClusterResult(SanitizedModel):
    """
        Represents the result of a SWOT analysis for a specific cluster.
    """
    cluster: SwotCluster = Field(
        ...,
        description=(
            "The cluster of the SWOT analysis"
            "(e.g., Value Proposition, Cost & Revenue, Infrastructure, Customer Interface)."
        ),
        examples=[SwotCluster.VALUE_PROPOSITION],
    )
    axis_statements: list[SwotAxisStatement] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="Statements for the SWOT axis within the specified cluster: between 2 and 5.",
        examples=[
            [
                SwotAxisStatement(
                    positive_statement="Our product has a unique feature that competitors lack.",
                    negative_statement="Our production costs are higher than the industry average.",
                    score=4,
                    importance=8,
                    certainty=7,
                ),
                SwotAxisStatement(
                    positive_statement="We have a strong brand reputation in the market.",
                    negative_statement="Our customer support response time is slower than desired.",
                    score=3,
                    importance=6,
                    certainty=8,
                ),
            ],
        ],
    )
    opportunities: list[SwotOpportunityThreat] = Field(
        ...,
        min_length=1,
        max_length=7,
        description="Identified opportunities for the specified cluster, each scored 1-5: between 1 and 7.",
        examples=[[
            SwotOpportunityThreat(text="Expand into new geographic markets.", score=4),
            SwotOpportunityThreat(text="Develop strategic partnerships with complementary businesses.", score=3),
        ]],
    )
    threats: list[SwotOpportunityThreat] = Field(
        ...,
        min_length=1,
        max_length=7,
        description="Identified threats for the specified cluster, each scored 1-5: between 1 and 7.",
        examples=[[
            SwotOpportunityThreat(text="Emerging competitors with lower-priced alternatives.", score=4),
            SwotOpportunityThreat(text="Changes in regulations that could impact our operations.", score=2),
        ]],
    )


class Swot(SanitizedModel):
    """
        Represents a SWOT analysis for a business model, organized by clusters.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the SWOT analysis.",
        examples=["swot_001"],
    )
    canvas_id: str = Field(
        ...,
        description="Identifier of the canvas this SWOT analysis is associated with.",
        examples=["canvas_001"],
    )
    canvas_version: int = Field(
        ...,
        ge=1,
        le=5,
        description="Version of the canvas this SWOT analysis is associated with.",
        examples=[1],
    )
    environment_scan_id: str | None = Field(
        None,
        description="Identifier of the EnvironmentScan used to inform Opportunities/Threats "
                     "for this cluster set, if any. Strengths/Weaknesses are always derived "
                     "solely from the canvas.",
        examples=["environment_scan_001"],
    )
    clusters: list[SwotClusterResult] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="A list of SWOT cluster results, one for each cluster.",
        examples=[
            [
                SwotClusterResult(
                    cluster=SwotCluster.VALUE_PROPOSITION,
                    axis_statements=[
                        SwotAxisStatement(
                            positive_statement="Our product has a unique feature that competitors lack.",
                            negative_statement="Our production costs are higher than the industry average.",
                            score=4,
                            importance=8,
                            certainty=7,
                        ),
                        SwotAxisStatement(
                            positive_statement="Customers value the core offer.",
                            negative_statement="The core offer is easy to copy.",
                            score=2,
                            importance=5,
                            certainty=6,
                        ),
                    ],
                    opportunities=[
                        SwotOpportunityThreat(text="Expand into new geographic markets.", score=4),
                    ],
                    threats=[
                        SwotOpportunityThreat(text="Emerging competitors with lower-priced alternatives.", score=4),
                    ],
                ),
                SwotClusterResult(
                    cluster=SwotCluster.COST_REVENUE,
                    axis_statements=[
                        SwotAxisStatement(
                            positive_statement="We have a strong brand reputation in the market.",
                            negative_statement="Our customer support response time is slower than desired.",
                            score=3,
                            importance=6,
                            certainty=8,
                        ),
                        SwotAxisStatement(
                            positive_statement="Customers value the core offer.",
                            negative_statement="The core offer is easy to copy.",
                            score=2,
                            importance=5,
                            certainty=6,
                        ),
                    ],
                    opportunities=[
                        SwotOpportunityThreat(text="Develop strategic partnerships with complementary businesses.", score=3),
                    ],
                    threats=[
                        SwotOpportunityThreat(text="Changes in regulations that could impact our operations.", score=2),
                    ],
                ),
                SwotClusterResult(
                    cluster=SwotCluster.INFRASTRUCTURE,
                    axis_statements=[
                        SwotAxisStatement(
                            positive_statement="Our supply chain is highly efficient and reliable.",
                            negative_statement="We have limited scalability in our current infrastructure.",
                            score=2,
                            importance=7,
                            certainty=6,
                        ),
                        SwotAxisStatement(
                            positive_statement="Customers value the core offer.",
                            negative_statement="The core offer is easy to copy.",
                            score=2,
                            importance=5,
                            certainty=6,
                        ),
                    ],
                    opportunities=[
                        SwotOpportunityThreat(text="Invest in scalable infrastructure solutions.", score=3),
                    ],
                    threats=[
                        SwotOpportunityThreat(text="Supply chain disruptions due to global events.", score=3),
                    ],
                ),
                SwotClusterResult(
                    cluster=SwotCluster.CUSTOMER_INTERFACE,
                    axis_statements=[
                        SwotAxisStatement(
                            positive_statement="We have a loyal customer base with high retention rates.",
                            negative_statement="Our user interface is not as intuitive as competitors'.",
                            score=1,
                            importance=5,
                            certainty=7,
                        ),
                        SwotAxisStatement(
                            positive_statement="Customers value the core offer.",
                            negative_statement="The core offer is easy to copy.",
                            score=2,
                            importance=5,
                            certainty=6,
                        ),
                    ],
                    opportunities=[
                        SwotOpportunityThreat(text="Enhance the user experience through design improvements.", score=2),
                    ],
                    threats=[
                        SwotOpportunityThreat(text="Negative reviews and feedback impacting brand perception.", score=3),
                    ],
                ),
            ],
        ],
    )

    @property
    def weighted_weakness_threat_score(self) -> float:
        """
            Calculates the weighted score for weaknesses and threats across all clusters.
            The score is the sum of the absolute values of negative axis scores
            multiplied by their importance, plus the sum of each threat's own
            1-5 score (not a flat count per item).
        """
        total = 0.0
        for c in self.clusters:
            for axis in c.axis_statements:
                if axis.score < 0:
                    total += axis.importance * abs(axis.score)
            total += sum(t.score for t in c.threats)
        return total

    @model_validator(mode="after")
    def clusters_cover_all_types(self) -> "Swot":
        """
            Validates that all four SWOT clusters are represented in the analysis.
        """
        present = {c.cluster for c in self.clusters}
        if present != set(SwotCluster):
            missing = set(SwotCluster) - present
            raise ValueError(
                f"All four SWOT clusters must be represented. Missing: {', '.join(missing)}"
            )
        return self
