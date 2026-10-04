from typing import Literal

from pydantic import Field, model_validator
from .fields import FromGeneratedMixin, SanitizedModel

from .enums import THREAT_QUESTIONS_BY_CLUSTER, SwotCluster, ThreatQuestion


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


class SwotOpportunity(SanitizedModel):
    """
        Represents a single Opportunity, per the BMG document's Evaluating
        Business Models format (pp. 220-223): each generative question is
        paired with a 1-5 scale. The book gives no caption for this scale; the
        working interpretation used here is "how strongly this applies to this
        model" (1 = barely, 5 = very strongly).
    """
    text: str = Field(
        ...,
        description="The opportunity statement (typically phrased as, "
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


class SwotThreat(SanitizedModel):
    """
        Represents the rating of ONE question of the fixed threat catalog
        (`ThreatQuestion`). Every SWOT iteration rates the same 21 questions, so
        the sum of the scores is comparable between iterations. Same 1-5 scale
        and working interpretation as `SwotOpportunity`.
    """
    question: ThreatQuestion = Field(
        ...,
        description="Which catalog threat this rates. Each cluster must rate exactly the "
                     "questions of its own catalog, once each.",
        examples=[ThreatQuestion.SUBSTITUTES_AVAILABLE],
    )
    text: str = Field(
        ...,
        description="How this threat applies to this business model, in one or two sentences.",
        examples=["Customers can switch to a cheaper app that covers the same basic need."],
    )
    score: int = Field(
        ...,
        ge=1,
        le=5,
        description="How strongly this threat applies to this model: 1 (barely) to 5 (very strongly). "
                     "Interpretation is a project decision; the book's pages give the scale "
                     "with no caption.",
        examples=[2, 3, 5],
    )


def _example_threats(cluster: SwotCluster, score: int = 3) -> list[SwotThreat]:
    """The exact catalog of `cluster`, rated `score` each (for field examples)."""
    return [
        SwotThreat(
            question=question,
            text=f"Example assessment of the '{question.value}' threat.",
            score=score,
        )
        for question in THREAT_QUESTIONS_BY_CLUSTER[cluster]
    ]


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
    opportunities: list[SwotOpportunity] = Field(
        ...,
        min_length=1,
        max_length=7,
        description="Identified opportunities for the specified cluster, each scored 1-5: between 1 and 7.",
        examples=[[
            SwotOpportunity(text="Expand into new geographic markets.", score=4),
            SwotOpportunity(text="Develop strategic partnerships with complementary businesses.", score=3),
        ]],
    )
    threats: list[SwotThreat] = Field(
        ...,
        min_length=2,
        max_length=7,
        description="One rating per threat question of this cluster's catalog (2, 5, 7 or 7 questions "
                     "depending on the cluster), each scored 1-5. Exactly the cluster's catalog, "
                     "each question once, in any order.",
        examples=[_example_threats(SwotCluster.VALUE_PROPOSITION)],
    )

    @model_validator(mode="after")
    def threats_are_exactly_the_cluster_catalog(self) -> "SwotClusterResult":
        """
            Validates that the threats rate exactly the catalog of this cluster:
            every question once, none missing, none from another cluster.
            Order is free.
        """
        expected = set(THREAT_QUESTIONS_BY_CLUSTER[self.cluster])
        questions = [t.question for t in self.threats]
        duplicated = sorted({q.value for q in questions if questions.count(q) > 1})
        if duplicated:
            raise ValueError(f"Each threat question may be rated only once. Repeated: {', '.join(duplicated)}.")
        present = set(questions)
        foreign = sorted(q.value for q in present - expected)
        missing = sorted(q.value for q in expected - present)
        if foreign or missing:
            raise ValueError(
                f"Threats of cluster {self.cluster.value} must be exactly its catalog. "
                f"Missing: {', '.join(missing) or '-'}. Not in this cluster: {', '.join(foreign) or '-'}."
            )
        return self


class SwotGenerated(SanitizedModel):
    """
        Generation contract of Swot: only what the LLM writes. The system
        fields (canvas_id, canvas_version, environment_scan_id, id) are added by Swot, which extends this model.
    """
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
                        SwotOpportunity(text="Expand into new geographic markets.", score=4),
                    ],
                    threats=_example_threats(SwotCluster.VALUE_PROPOSITION),
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
                        SwotOpportunity(text="Develop strategic partnerships with complementary businesses.", score=3),
                    ],
                    threats=_example_threats(SwotCluster.COST_REVENUE),
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
                        SwotOpportunity(text="Invest in scalable infrastructure solutions.", score=3),
                    ],
                    threats=_example_threats(SwotCluster.INFRASTRUCTURE),
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
                        SwotOpportunity(text="Enhance the user experience through design improvements.", score=2),
                    ],
                    threats=_example_threats(SwotCluster.CUSTOMER_INTERFACE),
                ),
            ],
        ],
    )

    @property
    def weighted_weakness_threat_score(self) -> float:
        """
            Weighted score for weaknesses and threats across all clusters: the sum
            of |score| * importance over the negative axis statements, plus the sum
            of the scores of the rated threats.

            The threat part is comparable between iterations: every cluster rates
            exactly its fixed catalog, so it always sums over the same 21 threat
            questions (21..105). The weakness part is NOT yet comparable: it
            depends on how many axis statements the model writes (2-5 per cluster)
            and only negative ones count.
        """
        total = 0.0
        for c in self.clusters:
            for axis in c.axis_statements:
                if axis.score < 0:
                    total += axis.importance * abs(axis.score)
            total += sum(t.score for t in c.threats)
        return total

    @model_validator(mode="after")
    def clusters_cover_all_types(self) -> "SwotGenerated":
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


class Swot(SwotGenerated, FromGeneratedMixin):
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
