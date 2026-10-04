from pydantic import Field
from .fields import FromGeneratedMixin, SanitizedModel

from .enums import (
    CanvasSection,
    StorytellingPerspective,
    StorytellingGoal,
    StorytellingFormat,
)


class CanvasReference(SanitizedModel):
    """
        Represents a reference to a specific section and card on the canvas.
    """
    section: CanvasSection = Field(
        ...,
        description="The section of the canvas (e.g., 'Customer Segments', 'Value Propositions').",
        examples=[
            CanvasSection.CUSTOMER_SEGMENTS,
            CanvasSection.VALUE_PROPOSITIONS,
        ],
    )
    note: str = Field(
        ...,
        description="A note or description related to the specific section and card.",
        examples=[
            "This customer segment is highly profitable.",
            "The value proposition needs to be more compelling.",
        ],
    )


class StorytellingGenerated(SanitizedModel):
    """
        Generation contract of Storytelling: only what the LLM writes. The system
        fields (canvas_id, id) are added by Storytelling, which extends this model.
    """
    perspective: StorytellingPerspective = Field(
        ...,
        description="The perspective from which the storytelling is presented (e.g., 'Company', 'Customer').",
        examples=[StorytellingPerspective.COMPANY],
    )
    goal: StorytellingGoal = Field(
        ...,
        description=(
            "The goal of the storytelling"
            " (e.g., 'Introducing New', 'Engaging Employees', 'Pitching Investors')."
            ),
        examples=[StorytellingGoal.PITCHING_INVESTORS],
    )
    format: StorytellingFormat = Field(
        ...,
        description="The format of the storytelling (e.g.,, 'Video Clip', 'TALK AND IMAGE').",
        examples=[StorytellingFormat.VIDEO_CLIP],
    )
    narrative_text: str = Field(
        ...,
        description="The narrative text of the storytelling element.",
        examples=[
            (
                "Our innovative solution addresses a critical market need by"
                " providing unparalleled value to our customers."
            ),
        ],
    )
    canvas_references: list[CanvasReference] = Field(
        ...,
        min_length=1,
        description=(
            "A list of references to specific sections and cards on"
            " the canvas that are relevant to the storytelling element."
        ),
        examples=[
            [
                CanvasReference(
                    section=CanvasSection.VALUE_PROPOSITIONS,
                    note="This value proposition highlights our unique selling points.",
                ),
                CanvasReference(
                    section=CanvasSection.CUSTOMER_SEGMENTS,
                    note="This customer segment is the primary target for our new product.",
                ),
            ],
        ],
    )


class Storytelling(StorytellingGenerated, FromGeneratedMixin):
    """
        Represents a storytelling element for a business model canvas.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the storytelling element.",
        examples=["storytelling_001"],
    )
    canvas_id: str = Field(
        ...,
        description="Identifier of the canvas this storytelling element is associated with.",
        examples=["canvas_001"],
    )