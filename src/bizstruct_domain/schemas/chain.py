"""Populated stage graph for the BMG generation chain.

Single source of truth for stage order and dependencies, consumed by
bizstruct-ml (both the pipeline and the agentic strategy), bizstruct-be
(orchestration), and bizstruct-fe (via an exported schemas/stages.json).
See docs/adr for the graph shape rationale.
"""

from .enums import Stage
from .stage_definition import StageDefinition
from .stage_registry import StageRegistry


STAGE_REGISTRY = StageRegistry(
    stages={
        Stage.BRIEF: StageDefinition(
            id=Stage.BRIEF,
            depends_on=[],
        ),
        Stage.EMPATHY_MAP: StageDefinition(
            id=Stage.EMPATHY_MAP,
            depends_on=[Stage.BRIEF],
            allows_multiple_instances=True,
        ),
        Stage.CUSTOMER_SCENARIO: StageDefinition(
            id=Stage.CUSTOMER_SCENARIO,
            depends_on=[Stage.EMPATHY_MAP],
            allows_multiple_instances=True,
        ),
        Stage.IDEATION: StageDefinition(
            id=Stage.IDEATION,
            depends_on=[Stage.EMPATHY_MAP],
            allows_multiple_instances=True,
        ),
        Stage.PATTERNS: StageDefinition(
            id=Stage.PATTERNS,
            depends_on=[Stage.CUSTOMER_SCENARIO, Stage.IDEATION],
        ),
        Stage.CANVAS: StageDefinition(
            id=Stage.CANVAS,
            depends_on=[Stage.PATTERNS],
        ),
        Stage.SWOT_ERRC_CYCLE: StageDefinition(
            id=Stage.SWOT_ERRC_CYCLE,
            depends_on=[Stage.CANVAS],
            optional_depends_on=[Stage.ENVIRONMENT_SCAN],
        ),
        Stage.STORYTELLING: StageDefinition(
            id=Stage.STORYTELLING,
            depends_on=[Stage.SWOT_ERRC_CYCLE],
        ),
        Stage.FUTURE_SCENARIO: StageDefinition(
            id=Stage.FUTURE_SCENARIO,
            depends_on=[Stage.SWOT_ERRC_CYCLE],
        ),
        Stage.PITCH: StageDefinition(
            id=Stage.PITCH,
            depends_on=[Stage.STORYTELLING, Stage.SWOT_ERRC_CYCLE],
            optional_depends_on=[Stage.TEAM_INFO, Stage.BUSINESS_CASE],
        ),
        Stage.TEAM_INFO: StageDefinition(
            id=Stage.TEAM_INFO,
            depends_on=[],
            is_optional=True,
        ),
        Stage.BUSINESS_CASE: StageDefinition(
            id=Stage.BUSINESS_CASE,
            depends_on=[Stage.BRIEF],
            is_optional=True,
        ),
        Stage.ENVIRONMENT_SCAN: StageDefinition(
            id=Stage.ENVIRONMENT_SCAN,
            depends_on=[Stage.BRIEF],
            is_optional=True,
        ),
    }
)
