from pydantic import BaseModel, Field

from .enums import PricingTier

class CustomerScenario(BaseModel):
    """
        A customer scenario describes a specific situation or 
        context in which a customer interacts with a product or service.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the customer scenario.",
        examples=["customer_scenario_001"],
    )
    empathy_map_id: str = Field(
        ...,
        description="Identifier of the empathy map this customer scenario is associated with.",
        examples=["empathy_map_001"],
    )
    situation_narrative: str = Field(
        ...,
        description="A narrative describing the situation or context of the customer scenario.",
        examples=["A busy professional trying to order groceries online during a hectic workday."],
    )
    pricing_tier: PricingTier | None = Field(
        None,
        description="The pricing tier relevant to this customer scenario, if applicable.",
        examples=[PricingTier.PREMIUM, PricingTier.MID_MARKET, PricingTier.LOW_COST],
    )
    channel_type: str | None = Field(
        None,
        description="The channel through which the customer interacts with the product or service.",
        examples=["mobile app", "website", "in-store"],
    )
    relationship_type: str | None = Field(
        None,
        description="The type of relationship the customer has with the business in this scenario.",
        examples=["loyal customer", "first-time user", "occasional buyer"],
    )
    interdependence_signal: bool= Field(
        default=False,
        description="Indicates whether there is a signal of interdependence in this customer scenario.",
        examples=[True, False],
    )
    open_questions: list[str] = Field(
        description="A list of open-ended questions that arise from this customer scenario.",
        examples=[
            ["How can we improve the online ordering experience for busy professionals?"],
        ],
    )

