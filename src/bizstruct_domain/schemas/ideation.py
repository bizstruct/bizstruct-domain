from pydantic import BaseModel, Field, model_validator

from .enums import Epicenter


class EpicenterClassification(BaseModel):
    """
        Represents the classification of an epicenter in a business context.
    """
    tags: list[Epicenter] = Field(
        ...,
        min_length=1,
        description="A list of tags associated with the epicenter classification.",
        examples=[
            [Epicenter.FINANCE_DRIVEN],
            [
                Epicenter.RESOURCE_DRIVEN,
                Epicenter.OFFER_DRIVEN,
                Epicenter.MULTIPLE_EPICENTER,
            ],
        ],
    )
    rationale: str = Field(
        ...,
        description="A rationale explaining the reasoning behind the epicenter classification.",
        examples=["The business model is primarily driven by customer needs and feedback."],
    )
    
    @model_validator(mode="after")
    def multiple_tags_require_marker(self) -> "EpicenterClassification":
        """
            Validates that if multiple tags are provided, the 'MULTIPLE_EPICENTER' tag must be included.
        """
        if len(self.tags) > 1 and Epicenter.MULTIPLE_EPICENTER not in self.tags:
            raise ValueError(
                "If multiple tags are provided, the 'MULTIPLE_EPICENTER' tag must be included."
            )
        return self


class Ideation(BaseModel):
    """
        Represents an ideation instance in a business context.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the ideation instance.",
        examples=["ideation_001"],
    )
    empathy_map_id: str = Field(
        ...,
        description="Identifier of the empathy map this ideation instance is associated with.",
        examples=["empathy_map_001"],
    )
    epicenter: EpicenterClassification = Field(
        ...,
        description="The classification of the epicenter for this ideation instance.",
    )
    what_if_questions: list[str] = Field(
        ...,
        description="A list of 'what if' questions that explore potential scenarios or ideas.",
        examples=[[
            "What if we could deliver our product in half the time?",
            "What if we could offer a subscription model for our service?",
        ]],
    )

    