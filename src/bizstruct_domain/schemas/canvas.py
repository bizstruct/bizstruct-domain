from pydantic import Field, model_validator
from .fields import SanitizedModel


from .enums import (
    ERRCActionType,
    CanvasSection,
)

# Per-section card count the *generator* must produce. Lives in one place so
# CanvasSectionsGenerated's schema constraints and Canvas's validator can
# never disagree about it.
GENERATED_CARDS_PER_SECTION_MIN = 2
GENERATED_CARDS_PER_SECTION_MAX = 4

class CanvasCard(SanitizedModel):
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


class CanvasSections(SanitizedModel):
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


class Canvas(SanitizedModel):
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
            When the canvas is flagged as generated, every section must hold
            between GENERATED_CARDS_PER_SECTION_MIN and _MAX cards. The same
            bounds are enforced at generation time by CanvasGenerated's
            schema; this re-checks them on the persisted shape.
        """
        if not self.is_generated:
            return self
        for field_name in CanvasSections.model_fields:
            cards = getattr(self.sections, field_name)
            if not (GENERATED_CARDS_PER_SECTION_MIN <= len(cards) <= GENERATED_CARDS_PER_SECTION_MAX):
                raise ValueError(
                    f"Section '{field_name}' must have between "
                    f"{GENERATED_CARDS_PER_SECTION_MIN} and {GENERATED_CARDS_PER_SECTION_MAX} "
                    f"cards when the canvas is generated. Found {len(cards)} cards."
                )
        return self


class CanvasCardDraft(SanitizedModel):
    """
        A card as the generator produces it: text only. The card id and
        errc_marker are assigned by the backend when it persists the card
        as a CanvasCard, so the generator never invents identifiers.
    """
    text: str = Field(
        ...,
        min_length=1,
        description="The text of the card: one short, concrete idea.",
        examples=["Weekly box of seasonal produce from local farms"],
    )


class CanvasSectionsGenerated(SanitizedModel):
    """
        The nine canvas sections as the generator must produce them. Unlike
        CanvasSections (the persisted shape, which accepts any number of
        cards), every section here is bound to 2-4 cards in the schema
        itself, so the bound reaches the model through response_format
        instead of being checked only after the fact.
    """
    value_propositions: list[CanvasCardDraft] = Field(
        ...,
        min_length=GENERATED_CARDS_PER_SECTION_MIN,
        max_length=GENERATED_CARDS_PER_SECTION_MAX,
        description="Cards for the Value Propositions section: "
                    "between 2 and 4 short, distinct cards, one idea per card.",
        examples=[
            [
                CanvasCardDraft(text="Weekly box of seasonal produce from local farms"),
                CanvasCardDraft(text="Delivery slot chosen by the customer"),
            ],
        ],
    )
    customer_segments: list[CanvasCardDraft] = Field(
        ...,
        min_length=GENERATED_CARDS_PER_SECTION_MIN,
        max_length=GENERATED_CARDS_PER_SECTION_MAX,
        description="Cards for the Customer Segments section: "
                    "between 2 and 4 short, distinct cards, one idea per card.",
        examples=[
            [
                CanvasCardDraft(text="Health-conscious urban households"),
                CanvasCardDraft(text="Small restaurants sourcing locally"),
            ],
        ],
    )
    channels: list[CanvasCardDraft] = Field(
        ...,
        min_length=GENERATED_CARDS_PER_SECTION_MIN,
        max_length=GENERATED_CARDS_PER_SECTION_MAX,
        description="Cards for the Channels section: "
                    "between 2 and 4 short, distinct cards, one idea per card.",
        examples=[
            [
                CanvasCardDraft(text="Mobile app for ordering and tracking"),
                CanvasCardDraft(text="Pick-up points at farmers' markets"),
            ],
        ],
    )
    customer_relationships: list[CanvasCardDraft] = Field(
        ...,
        min_length=GENERATED_CARDS_PER_SECTION_MIN,
        max_length=GENERATED_CARDS_PER_SECTION_MAX,
        description="Cards for the Customer Relationships section: "
                    "between 2 and 4 short, distinct cards, one idea per card.",
        examples=[
            [
                CanvasCardDraft(text="Self-service subscription management"),
                CanvasCardDraft(text="Direct messaging with the farm"),
            ],
        ],
    )
    revenue_streams: list[CanvasCardDraft] = Field(
        ...,
        min_length=GENERATED_CARDS_PER_SECTION_MIN,
        max_length=GENERATED_CARDS_PER_SECTION_MAX,
        description="Cards for the Revenue Streams section: "
                    "between 2 and 4 short, distinct cards, one idea per card.",
        examples=[
            [
                CanvasCardDraft(text="Monthly subscription fee"),
                CanvasCardDraft(text="Delivery fee per order"),
            ],
        ],
    )
    key_resources: list[CanvasCardDraft] = Field(
        ...,
        min_length=GENERATED_CARDS_PER_SECTION_MIN,
        max_length=GENERATED_CARDS_PER_SECTION_MAX,
        description="Cards for the Key Resources section: "
                    "between 2 and 4 short, distinct cards, one idea per card.",
        examples=[
            [
                CanvasCardDraft(text="Network of partner farms"),
                CanvasCardDraft(text="Delivery logistics platform"),
            ],
        ],
    )
    key_activities: list[CanvasCardDraft] = Field(
        ...,
        min_length=GENERATED_CARDS_PER_SECTION_MIN,
        max_length=GENERATED_CARDS_PER_SECTION_MAX,
        description="Cards for the Key Activities section: "
                    "between 2 and 4 short, distinct cards, one idea per card.",
        examples=[
            [
                CanvasCardDraft(text="Coordinating harvest and delivery schedules"),
                CanvasCardDraft(text="Maintaining the ordering app"),
            ],
        ],
    )
    key_partnerships: list[CanvasCardDraft] = Field(
        ...,
        min_length=GENERATED_CARDS_PER_SECTION_MIN,
        max_length=GENERATED_CARDS_PER_SECTION_MAX,
        description="Cards for the Key Partnerships section: "
                    "between 2 and 4 short, distinct cards, one idea per card.",
        examples=[
            [
                CanvasCardDraft(text="Local farms and cooperatives"),
                CanvasCardDraft(text="Last-mile courier companies"),
            ],
        ],
    )
    cost_structure: list[CanvasCardDraft] = Field(
        ...,
        min_length=GENERATED_CARDS_PER_SECTION_MIN,
        max_length=GENERATED_CARDS_PER_SECTION_MAX,
        description="Cards for the Cost Structure section: "
                    "between 2 and 4 short, distinct cards, one idea per card.",
        examples=[
            [
                CanvasCardDraft(text="Courier and fuel costs"),
                CanvasCardDraft(text="Platform development and hosting"),
            ],
        ],
    )


class CanvasGenerated(SanitizedModel):
    """
        Generation-time contract for the canvas stage: the response_format
        bizstruct-ml asks the model for. It carries content only; group_id,
        empathy_map_ids, version and card ids are known to or assigned by
        the orchestrator, not generated. The persisted shape is Canvas.
    """
    sections: CanvasSectionsGenerated = Field(
        ...,
        description="The nine canvas sections, each with 2-4 cards.",
    )


def _assert_section_names_in_sync() -> None:
    """The nine section names exist in three places: the CanvasSection enum
    (Canvas.get_section does getattr(sections, section.value)), the persisted
    CanvasSections, and CanvasSectionsGenerated. Fail at import if they drift."""
    expected = {section.value for section in CanvasSection}
    persisted = set(CanvasSections.model_fields)
    generated = set(CanvasSectionsGenerated.model_fields)
    if not (expected == persisted == generated):
        raise RuntimeError(
            "Canvas section names are out of sync: "
            f"enum={sorted(expected)}, CanvasSections={sorted(persisted)}, "
            f"CanvasSectionsGenerated={sorted(generated)}"
        )


_assert_section_names_in_sync()
