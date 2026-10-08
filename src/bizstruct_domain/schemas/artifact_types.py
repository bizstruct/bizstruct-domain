"""Artifact types and where they live. Pure data, no model imports, so that
`consistency` (rule inputs address a type) and `wire` (rows hold artifacts)
can both import it without a cycle."""

from enum import StrEnum

from .enums import Stage


class ArtifactType(StrEnum):
    """The 14 persisted artifact models. `swot` and `errc` both belong to the
    `swot_errc_cycle` stage."""
    BRIEF = "brief"
    EMPATHY_MAP = "empathy_map"
    CUSTOMER_SCENARIO = "customer_scenario"
    IDEATION = "ideation"
    PATTERNS = "patterns"
    CANVAS = "canvas"
    SWOT = "swot"
    ERRC = "errc"
    STORYTELLING = "storytelling"
    FUTURE_SCENARIO = "future_scenario"
    PITCH = "pitch"
    TEAM_INFO = "team_info"
    BUSINESS_CASE = "business_case"
    ENVIRONMENT_SCAN = "environment_scan"


ARTIFACT_STAGE: dict[ArtifactType, Stage] = {
    ArtifactType.BRIEF: Stage.BRIEF,
    ArtifactType.EMPATHY_MAP: Stage.EMPATHY_MAP,
    ArtifactType.CUSTOMER_SCENARIO: Stage.CUSTOMER_SCENARIO,
    ArtifactType.IDEATION: Stage.IDEATION,
    ArtifactType.PATTERNS: Stage.PATTERNS,
    ArtifactType.CANVAS: Stage.CANVAS,
    ArtifactType.SWOT: Stage.SWOT_ERRC_CYCLE,
    ArtifactType.ERRC: Stage.SWOT_ERRC_CYCLE,
    ArtifactType.STORYTELLING: Stage.STORYTELLING,
    ArtifactType.FUTURE_SCENARIO: Stage.FUTURE_SCENARIO,
    ArtifactType.PITCH: Stage.PITCH,
    ArtifactType.TEAM_INFO: Stage.TEAM_INFO,
    ArtifactType.BUSINESS_CASE: Stage.BUSINESS_CASE,
    ArtifactType.ENVIRONMENT_SCAN: Stage.ENVIRONMENT_SCAN,
}


# The stages whose rows can hold an artifact of this type. Every type lives in
# its home stage (`ARTIFACT_STAGE`); a Canvas also lives in the `swot_errc_cycle`
# row: v1 belongs to the `canvas` row, v2..v5 to the cycle row (ADR-0011 Q1, Q6).
ARTIFACT_HOLDERS: dict[ArtifactType, tuple[Stage, ...]] = {
    **{t: (stage,) for t, stage in ARTIFACT_STAGE.items()},
    ArtifactType.CANVAS: (Stage.CANVAS, Stage.SWOT_ERRC_CYCLE),
}
