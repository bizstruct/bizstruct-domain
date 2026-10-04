from pydantic import Field, model_validator
from .fields import FromGeneratedMixin, SanitizedModel

from .enums import (
    ERRCActionType,
    CanvasSection
)

class ErrcMove(SanitizedModel):
    """
        Represents a move in the error correction system.
    """
    action: ERRCActionType = Field(
        ...,
        description="The action to be taken for error correction.",
        examples=[
            ERRCActionType.ELIMINATE,
            ERRCActionType.REDUCE,
            ERRCActionType.RAISE,
            ERRCActionType.CREATE,
        ],
    )
    target_section: CanvasSection = Field(
        ...,
        description="The section of the canvas that the action targets.",
        examples=[
            CanvasSection.CUSTOMER_SEGMENTS,
            CanvasSection.VALUE_PROPOSITIONS,
            CanvasSection.CHANNELS,
        ],
    )
    target_card_text: str | None = Field(
        None,
        description="The text of the card that the action targets, if applicable.",
        examples=[
            "Improve customer onboarding process",
            "Reduce production costs",
        ],
    )
    new_text: str | None = Field(
        None,
        description="The new text to be used for the card after the action is applied, if applicable.",
        examples=[
            "Implement a new customer onboarding process",
            "Reduce production costs by 15%",
        ],
    )
    opposite_side_impact: str = Field(
        ...,
        description="A description of how the action will impact the opposite side of the canvas.",
        examples=[
            "Eliminating this feature may reduce customer satisfaction.",
            "Raising the price may increase revenue but could decrease demand.",
        ],
    )
    rationale: str = Field(
        ...,
        description="The rationale behind the action, explaining why it is necessary.",
        examples=[
            "This feature is not aligned with our core value proposition.",
            "Reducing production costs will improve our profit margins.",
        ],
    )

    @model_validator(mode="after")
    def action_field_consistency(self) -> "ErrcMove":
        """
            Ensures that the action and its associated fields are consistent.
        """
        if self.action == ERRCActionType.CREATE:
            if not self.new_text:
                raise ValueError("new_text must be provided when action is CREATE.")
            if self.target_card_text:
                raise ValueError("target_card_text must be None when action is CREATE.")
        else:
            if not self.target_card_text:
                raise ValueError("target_card_text must be provided when action is not CREATE.")
            if self.new_text:
                raise ValueError("new_text must be None when action is not CREATE.")
        return self


class ErrcGenerated(SanitizedModel):
    """
        Generation contract of Errc: only what the LLM writes. The system
        fields (canvas_id, from_version, id, result_canvas_id, swot_id, to_version) are added by Errc, which extends this model.
    """
    moves: list[ErrcMove] = Field(
        ...,
        min_length=1,
        max_length=6,
        description="The moves of the ERRC analysis: between 1 and 6.",
        examples=[
            [
                ErrcMove(
                    action=ERRCActionType.ELIMINATE,
                    target_section=CanvasSection.CUSTOMER_SEGMENTS,
                    target_card_text="Old customer segment",
                    new_text=None,
                    opposite_side_impact="Eliminating this segment may reduce revenue.",
                    rationale="This segment is no longer profitable.",
                ),
                ErrcMove(
                    action=ERRCActionType.CREATE,
                    target_section=CanvasSection.VALUE_PROPOSITIONS,
                    target_card_text=None,
                    new_text="New value proposition",
                    opposite_side_impact="Creating this proposition may attract new customers.",
                    rationale="This proposition addresses a new market need.",
                ),
            ],
        ],
    )


class Errc(ErrcGenerated, FromGeneratedMixin):
    """
        Represents an error correction (ERRC) analysis for a business model canvas.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the ERRC analysis.",
        examples=["errc_001"],
    )
    canvas_id: str = Field(
        ...,
        description="Identifier of the canvas this ERRC analysis is associated with.",
        examples=["canvas_001"],
    )
    swot_id: str = Field(
        ...,
        description="Identifier of the SWOT analysis whose signals informed these moves. "
                     "SWOT always precedes ERRC in the swot_errc_cycle, so this is required, "
                     "not optional.",
        examples=["swot_001"],
    )
    from_version: int = Field(
        ...,
        ge=1,
        le=5,
        description="The version of the canvas from which this ERRC analysis is derived.",
        examples=[1],
    )
    to_version: int = Field(
        ...,
        ge=2,
        le=5,
        description="The version of the canvas to which this ERRC analysis is applied.",
        examples=[2],
    )
    result_canvas_id: str = Field(
        ...,
        description="Identifier of the resulting canvas after applying this ERRC analysis.",
        examples=["canvas_002"],
    )

    @model_validator(mode="after")
    def version_increments(self) -> "Errc":
        """
            Ensures that the version numbers are incremented correctly.
        """
        if self.to_version != self.from_version + 1:
            raise ValueError(
                f"to_version ({self.to_version}) must be exactly"
                f" one greater than from_version ({self.from_version})."
            )
        return self
