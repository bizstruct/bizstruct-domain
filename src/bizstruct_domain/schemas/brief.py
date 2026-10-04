from pydantic import Field
from .fields import SanitizedModel


class Brief(SanitizedModel):
    """
        A brief description of a business structure.
    """
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
        description="A list of potential customer segments for the business.",
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
