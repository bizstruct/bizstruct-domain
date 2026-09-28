from pydantic import BaseModel, Field, model_validator


from .enums import (
    ERRCActionType,
    CanvasSection,
)

class CanvasCard(BaseModel):
    """
        Represents a card in a business canvas, which can be used to capture key information or insights.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the canvas card.",
        examples=["canvas_card_001"],
    )
    text: str = Field(
        ...,
        description="The text of the canvas card.",
        examples=["This card describes the value proposition for our new product."],
    )
    errc_marker: ERRCActionType | None = Field(
        None,
        description="The ERRC action type associated with this canvas card, if applicable.",
        examples=[
            ERRCActionType.ELIMINATE,
            ERRCActionType.REDUCE,
            ERRCActionType.RAISE,
            ERRCActionType.CREATE,
        ],
    )


class CanvasSections(BaseModel):
    """
        Represents the sections of a business canvas, each containing a list of canvas cards.
    """
    value_propositions: list[CanvasCard] = Field(
        default_factory=list,
        description="A list of canvas cards for the Value Propositions section.",
        examples=[
            [
                CanvasCard(
                    id="canvas_card_001",
                    text="Our product offers a unique solution to a common problem.",
                    errc_marker=ERRCActionType.CREATE,
                ),
                CanvasCard(
                    id="canvas_card_002",
                    text="We eliminate unnecessary features to simplify the user experience.",
                    errc_marker=ERRCActionType.ELIMINATE,
                ),
            ],
        ],
    )
    customer_segments: list[CanvasCard] = Field(
        default_factory=list,
        description="A list of canvas cards for the Customer Segments section.",
        examples=[
            [
                CanvasCard(
                    id="canvas_card_003",
                    text="Our target customer is a tech-savvy professional.",
                    errc_marker=ERRCActionType.RAISE,
                ),
            ],
        ],
    )
    channels: list[CanvasCard] = Field(
        default_factory=list,
        description="A list of canvas cards for the Channels section.",
        examples=[
            [
                CanvasCard(
                    id="canvas_card_004",
                    text="We use social media to reach our target audience.",
                    errc_marker=ERRCActionType.RAISE,
                ),
            ],
        ],
    )
    customer_relationships: list[CanvasCard] = Field(
        default_factory=list,
        description="A list of canvas cards for the Customer Relationships section.",
        examples=[
            [
                CanvasCard(
                    id="canvas_card_005",
                    text="We provide personalized support to our customers.",
                    errc_marker=ERRCActionType.RAISE,
                ),
            ],
        ],
    )
    revenue_streams: list[CanvasCard] = Field(
        default_factory=list,
        description="A list of canvas cards for the Revenue Streams section.",
        examples=[
            [
                CanvasCard(
                    id="canvas_card_006",
                    text="We generate revenue through subscription models.",
                    errc_marker=ERRCActionType.RAISE,
                ),
            ],
        ],
    )
    key_resources: list[CanvasCard] = Field(
        default_factory=list,
        description="A list of canvas cards for the Key Resources section.",
        examples=[
            [
                CanvasCard(
                    id="canvas_card_007",
                    text="Our key resource is our proprietary technology.",
                    errc_marker=ERRCActionType.RAISE,
                ),
            ],
        ],
    )
    key_activities: list[CanvasCard] = Field(
        default_factory=list,
        description="A list of canvas cards for the Key Activities section.",
        examples=[
            [
                CanvasCard(
                    id="canvas_card_008",
                    text="Our key activity is continuous product development.",
                    errc_marker=ERRCActionType.RAISE,
                ),
            ],
        ],
    )
    key_partnerships: list[CanvasCard] = Field(
        default_factory=list,
        description="A list of canvas cards for the Key Partnerships section.",
        examples=[
            [
                CanvasCard(
                    id="canvas_card_009",
                    text="We partner with industry leaders to enhance our offerings.",
                    errc_marker=ERRCActionType.RAISE,
                ),
            ],
        ],
    )
    cost_structure: list[CanvasCard] = Field(
        default_factory=list,
        description="A list of canvas cards for the Cost Structure section.",
        examples=[
            [
                CanvasCard(
                    id="canvas_card_010",
                    text="Our cost structure is optimized for scalability.",
                    errc_marker=ERRCActionType.REDUCE,
                ),
            ],
        ],
    )


class Canvas(BaseModel):
    """
        Represents a business canvas, which is a visual representation of key elements of a business model.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the canvas.",
        examples=["canvas_001"],
    )
    group_id: str = Field(
        ...,
        description="Identifier of the canvas group this canvas is associated with.",
        examples=["canvas_group_001"],
    )
    empathy_map_ids: list[str] = Field(
        ...,
        min_length=1,
        description="A list of empathy map identifiers associated with this canvas.",
        examples=[["empathy_map_001", "empathy_map_002"]],
    )
    version: int = Field(
        ...,
        ge=1,
        le=5,
        description="The version number of the canvas.",
        examples=[1],
    )
    previous_version_id: str | None = Field(
        None,
        description="Identifier of the previous version of this canvas, if applicable.",
        examples=["canvas_000"],
    )
    is_final: bool = Field(
        default=False,
        description="Indicates whether this canvas is the final version.",
        examples=[True, False],
    )
    sections: CanvasSections = Field(
        ...,
        description="The sections of the canvas, each containing a list of canvas cards.",
        examples=[
            CanvasSections(
                value_propositions=[
                    CanvasCard(
                        id="canvas_card_001",
                        text="Our product offers a unique solution to a common problem.",
                        errc_marker=ERRCActionType.CREATE,
                    ),
                ],
                customer_segments=[
                    CanvasCard(
                        id="canvas_card_003",
                        text="Our target customer is a tech-savvy professional.",
                        errc_marker=ERRCActionType.RAISE,
                    ),
                ],
                channels=[
                    CanvasCard(
                        id="canvas_card_004",
                        text="We use social media to reach our target audience.",
                        errc_marker=ERRCActionType.RAISE,
                    ),
                ],
                customer_relationships=[
                    CanvasCard(
                        id="canvas_card_005",
                        text="We provide personalized support to our customers.",
                        errc_marker=ERRCActionType.RAISE,
                    ),
                ],
                revenue_streams=[
                    CanvasCard(
                        id="canvas_card_006",
                        text="We generate revenue through subscription models.",
                        errc_marker=ERRCActionType.RAISE,
                    ),
                ],
                key_resources=[
                    CanvasCard(
                        id="canvas_card_007",
                        text="Our key resource is our proprietary technology.",
                        errc_marker=ERRCActionType.RAISE,
                    ),
                ],
                key_activities=[
                    CanvasCard(
                        id="canvas_card_008",
                        text="Our key activity is continuous product development.",
                        errc_marker=ERRCActionType.RAISE,
                    ),
                ],
                key_partnerships=[
                    CanvasCard(
                        id="canvas_card_009",
                        text="We partner with industry leaders to enhance our offerings.",
                        errc_marker=ERRCActionType.RAISE,
                    ),
                ],
                cost_structure=[
                    CanvasCard(
                        id="canvas_card_010",
                        text="Our cost structure is optimized for scalability.",
                        errc_marker=ERRCActionType.REDUCE,
                    ),
                ],
            )
        ],
    )
    is_generated: bool = Field(
        default=True,
        description="Indicates whether this canvas was generated automatically.",
        examples=[True, False],
    )


    def get_section(self, section: CanvasSection) -> list[CanvasCard]:
        return getattr(self.sections, section.value)

    @model_validator(mode="after")
    def generated_card_count(self) -> "Canvas":
        """
            Validates that each section of the canvas has at least one card.
        """
        if not self.is_generated:
            return self
        for field_name in CanvasSections.model_fields:
            cards = getattr(self.sections, field_name)
            if not (2 <= len(cards) <= 4):
                raise ValueError(
                    f"Section '{field_name}' must have between 2 and 4 cards when the canvas is generated. "
                    f"Found {len(cards)} cards."
                )
        return self

