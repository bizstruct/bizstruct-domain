from pydantic import Field
from .fields import SanitizedModel

from .enums import (
    Stage,
)

class StageDefinition(SanitizedModel):
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
        description="The list of stages that this stage depends on. Hard "
                     "dependencies: the stage cannot be generated until "
                     "every one of these is done.",
        examples=[
            [Stage.BRIEF, Stage.EMPATHY_MAP],
        ]
    )
    optional_depends_on: list[Stage] = Field(
        default_factory=list,
        description="Stages whose output is used if present, but never "
                     "blocks this stage (e.g. environment_scan enriching "
                     "swot_errc_cycle, team_info/business_case enriching "
                     "pitch).",
        examples=[
            [Stage.ENVIRONMENT_SCAN],
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
