from pydantic import Field, model_validator
from .fields import FromGeneratedMixin, SanitizedModel

from .enums import Epicenter


class EpicenterClassification(SanitizedModel):
    """
        Represents the classification of an epicenter in a business context.
    """
    tags: list[Epicenter] = Field(
        ...,
        min_length=1,
        description="The epicenter tags: one or more distinct concrete epicenters. When there are two "
                     "or more, MULTIPLE_EPICENTER must also be listed; with a single concrete tag it "
                     "must not be.",
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
    def tags_follow_the_multiple_epicenter_rule(self) -> "EpicenterClassification":
        """
            Validates the two-way MULTIPLE_EPICENTER rule. The concrete tags
            are the ones other than MULTIPLE_EPICENTER: they must be unique,
            and there must be 1 to 4 of them. MULTIPLE_EPICENTER is present
            if and only if there are at least two concrete tags.
        """
        if len(set(self.tags)) != len(self.tags):
            raise ValueError("tags must not contain duplicates.")
        concrete = [t for t in self.tags if t != Epicenter.MULTIPLE_EPICENTER]
        has_marker = Epicenter.MULTIPLE_EPICENTER in self.tags
        if not concrete:
            raise ValueError(
                "At least one concrete epicenter tag is required; "
                "'MULTIPLE_EPICENTER' alone is not a classification."
            )
        if len(concrete) >= 2 and not has_marker:
            raise ValueError(
                "If multiple concrete tags are provided, the 'MULTIPLE_EPICENTER' tag must be included."
            )
        if len(concrete) == 1 and has_marker:
            raise ValueError(
                "'MULTIPLE_EPICENTER' requires at least two concrete tags."
            )
        return self


class IdeationGenerated(SanitizedModel):
    """
        Generation contract of Ideation: only what the LLM writes. The system
        fields (empathy_map_id, id) are added by Ideation, which extends this model.
    """
    epicenter: EpicenterClassification = Field(
        ...,
        description="The classification of the epicenter for this ideation instance.",
    )
    what_if_questions: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="'What if' questions that explore potential scenarios or ideas: between 1 and 10.",
        examples=[[
            "What if we could deliver our product in half the time?",
            "What if we could offer a subscription model for our service?",
        ]],
    )


class Ideation(IdeationGenerated, FromGeneratedMixin):
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

    