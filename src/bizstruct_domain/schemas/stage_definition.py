from pydantic import BaseModel, Field

from .enums import (
    Stage,
)

class StageDefinition(BaseModel):
    """
        A definition of a stage in the application.
    """
    id: Stage = Field(
        ...,
        description="The unique identifier of the stage.",
        examples=[
            Stage.BRIEF,
        ]
    )
    depends_on: list[Stage] = Field(
        ...,
        description="The list of stages that this stage depends on.",
        examples=[
            [Stage.BRIEF, Stage.EMPATHY_MAP],
        ]
    )
    allows_multiple_instances: bool = Field(
        default=False,
        description="Indicates whether the stage allows multiple instances.",
        examples=[
            True,
        ]
    )
    is_optional: bool = Field(
        default=False,
        description="Indicates whether the stage is optional.",
        examples=[
            False,
        ]
    )