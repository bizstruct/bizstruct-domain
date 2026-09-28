from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import SwotCluster


class SwotAxisStatement(BaseModel):
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
    score: int = Field(
        ...,
        ge=-5,
        le=5,
        
        description=(
            "A score representing the impact of the statement,"
            " ranging from -5 (very negative) to 5 (very positive)."
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

    @field_validator("score")
    @classmethod
    def score_not_zero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("Score cannot be zero.")
        return v


class SwotClusterResult(BaseModel):
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
        min_length=1,
        description="A list of statements for the SWOT axis within the specified cluster.",
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
    opportunities: list[str] = Field(
        ...,
        description="A list of identified opportunities for the specified cluster.",
        examples=[[
            "Expand into new geographic markets.",
            "Develop strategic partnerships with complementary businesses.",
        ]],
    )
    threats: list[str] = Field(
        ...,
        description="A list of identified threats for the specified cluster.",
        examples=[[
            "Emerging competitors with lower-priced alternatives.",
            "Changes in regulations that could impact our operations.",
        ]],
    )


class Swot(BaseModel):
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
    used_environment_scan: bool = Field(
        default=False,
        description="Indicates whether an environmental scan was used in this SWOT analysis.",
        examples=[True, False],
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
                    ],
                    opportunities=[
                        "Expand into new geographic markets.",
                    ],
                    threats=[
                        "Emerging competitors with lower-priced alternatives.",
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
                    ],
                    opportunities=[
                        "Develop strategic partnerships with complementary businesses.",
                    ],
                    threats=[
                        "Changes in regulations that could impact our operations.",
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
                    ],
                    opportunities=[
                        "Invest in scalable infrastructure solutions.",
                    ],
                    threats=[
                        "Supply chain disruptions due to global events.",
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
                    ],
                    opportunities=[
                        "Enhance the user experience through design improvements.",
                    ],
                    threats=[
                        "Negative reviews and feedback impacting brand perception.",
                    ],
                ),
            ],
        ],
    )
    
    @property
    def weighted_weakness_threat_score(self) -> float:
        """
            Calculates the weighted score for weaknesses and threats across all clusters.
            The score is calculated as the sum of the absolute values of negative scores
            multiplied by their importance, plus the count of threats.
        """
        total = 0.0
        for c in self.clusters:
            for axis in c.axis_statements:
                if axis.score < 0:
                    total += axis.importance * abs(axis.score)
            total += len(c.threats)
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

