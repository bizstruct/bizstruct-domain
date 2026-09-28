from pydantic import BaseModel, Field

from .enums import (
    CanvasSection,
)

class AdaptationQuestion(BaseModel):
    """
        Represents an adaptation question related to a specific section of the business model canvas.
    """
    section: CanvasSection = Field(
        ...,
        description="The section of the canvas to which this adaptation question pertains.",
        examples=[
            CanvasSection.CUSTOMER_SEGMENTS,
            CanvasSection.VALUE_PROPOSITIONS,
        ],
    )
    question: str = Field(
        ...,
        description="The adaptation question related to the specified canvas section.",
        examples=[
            "How can we adapt our value proposition to better meet the needs of our target customer segments?",
            "What changes can we make to our customer segments to better align with our value proposition?",
        ],
    )


class FutureScenarioVariant(BaseModel):
    """
        Represents a variant of a future scenario in a business context.
    """
    name: str = Field(
        ...,
        description="The name of the future scenario variant.",
        examples=["Optimistic Growth", "Pessimistic Decline", "Steady State"],
    )
    narrative: str = Field(
        ...,
        description="A narrative describing the future scenario variant.",
        examples=[
            "In this scenario, the company experiences rapid growth due to market expansion and increased customer demand.",
            "In this scenario, the company faces challenges due to economic downturns and increased competition.",
        ],
    )
    adaptation_questions: list[AdaptationQuestion] = Field(
        ...,
        min_length=1,
        description="A list of adaptation questions related to this future scenario variant.",
        examples=[
            [
                AdaptationQuestion(
                    section=CanvasSection.CUSTOMER_SEGMENTS,
                    question="How can we adapt our customer segments to better align with the changing market conditions?",
                ),
                AdaptationQuestion(
                    section=CanvasSection.VALUE_PROPOSITIONS,
                    question="What changes can we make to our value propositions to better meet the evolving needs of our customers?",
                ),
            ],
        ],
    )
    

class FutureScenario(BaseModel):
    """
        Represents a future scenario in a business context.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the future scenario.",
        examples=["future_scenario_001"],
    )
    canvas_id: str = Field(
        ...,
        description="Identifier of the canvas this future scenario is associated with.",
        examples=["canvas_001"],
    )
    uncertainty_drivers: list[str] = Field(
        ...,
        min_length=2,
        description="A list of uncertainty drivers that may impact the future scenario.",
        examples=[["Market volatility", "Regulatory changes"]],
    )
    variants: list[FutureScenarioVariant] = Field(
        ...,
        min_length=2,
        max_length=4,
        description="A list of variants for this future scenario.",
        examples=[
            [
                FutureScenarioVariant(
                    name="Optimistic Growth",
                    narrative="In this scenario, the company experiences rapid growth due to market expansion and increased customer demand.",
                    adaptation_questions=[
                        AdaptationQuestion(
                            section=CanvasSection.CUSTOMER_SEGMENTS,
                            question="How can we adapt our customer segments to better align with the changing market conditions?",
                        ),
                        AdaptationQuestion(
                            section=CanvasSection.VALUE_PROPOSITIONS,
                            question="What changes can we make to our value propositions to better meet the evolving needs of our customers?",
                        ),
                    ],
                ),
                FutureScenarioVariant(
                    name="Pessimistic Decline",
                    narrative="In this scenario, the company faces challenges due to economic downturns and increased competition.",
                    adaptation_questions=[
                        AdaptationQuestion(
                            section=CanvasSection.CUSTOMER_SEGMENTS,
                            question="How can we adapt our customer segments to mitigate the impact of economic downturns?",
                        ),
                        AdaptationQuestion(
                            section=CanvasSection.VALUE_PROPOSITIONS,
                            question="What changes can we make to our value propositions to remain competitive in a declining market?",
                        ),
                    ],
                ),
            ],
        ],
    )
    