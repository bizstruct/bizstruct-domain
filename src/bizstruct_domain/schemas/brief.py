from pydantic import Field
from .fields import SanitizedModel


# Upper bound on customer segments: one empathy map, customer scenario and
# ideation per segment, so it caps the width of the whole graph.
MAX_SEGMENTS = 3

# Room for a short name: it is shown in a sidebar, so it is far below be's own limit on a title.
PROJECT_TITLE_MAX_LENGTH = 80


class Brief(SanitizedModel):
    """
        A brief description of a business structure.
    """
    project_title: str | None = Field(
        None,
        max_length=PROJECT_TITLE_MAX_LENGTH,
        description="A short name for the project that a person would give it, in the language of the idea: "
                    "a noun phrase of a few words, not a sentence and without a trailing period.",
        examples=["Reminders for auto repair shops"],
    )
    idea_summary: str = Field(
        ...,
        description="A brief summary of the business idea.",
        examples=["A platform that connects local farmers with consumers for fresh produce delivery."],
    )
    industry: str = Field(
        ...,
        description="The industry in which the business operates.",
        examples=["Agriculture and Food Delivery"],
    )
    customer_segment_candidates: list[str] = Field(
        min_length=1,
        max_length=MAX_SEGMENTS,
        description="Potential customer segments for the business: between 1 and 3. "
                     "Each one gets its own empathy map, customer scenario and ideation.",
        examples=[["Health-conscious consumers", "Local restaurants", "Farmers' markets"]],
    )
    existing_resources: list[str] = Field(
        description="A list of existing resources that the business can leverage.",
        examples=[["Local farm partnerships", "Delivery logistics network", "Mobile app platform"]],
    )
    monetization_hint: str | None = Field(
        None,
        description="A hint about how the business can generate revenue.",
        examples=["Subscription model for regular customers"],
    )
    gaps: list[str] = Field(
        description="A list of gaps or challenges that the business needs to address.",
        examples=[[
            "Limited delivery radius",
            "Seasonal availability of produce",
            "Competition from established grocery delivery services",
        ]],
    )
