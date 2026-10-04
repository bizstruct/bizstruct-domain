"""Public API of the BMG domain model (13-stage graph, artifacts, consistency).

Import from here rather than from the individual modules:

    from bizstruct_domain.schemas import Canvas, STAGE_REGISTRY, Stage
"""

from .brief import MAX_SEGMENTS, Brief
from .canvas import (
    GENERATED_CARDS_PER_SECTION_MAX,
    GENERATED_CARDS_PER_SECTION_MIN,
    Canvas,
    CanvasCard,
    CanvasCardDraft,
    CanvasGenerated,
    CanvasSections,
    CanvasSectionsGenerated,
)
from .chain import STAGE_REGISTRY
from .consistency import (
    CONSISTENCY_RULES,
    JUDGE_CHECKS,
    ConsistencyReport,
    ConsistencyRule,
    ConsistencyViolation,
    JudgeCheck,
    RuleInput,
    StageArity,
)
from .customer_scenario import CustomerScenario, CustomerScenarioGenerated
from .empathy_map import EmpathyMap, EmpathyMapGenerated
from .enums import (
    SWOT_CLUSTER_SECTIONS,
    THREAT_QUESTIONS_BY_CLUSTER,
    CanvasBranch,
    CanvasSection,
    Epicenter,
    ERRCActionType,
    FreePatternSubtype,
    OpenBusinessModelPatternSubtype,
    Pattern,
    PricingTier,
    SegmentRelationType,
    Stage,
    StageAction,
    StageErrorCode,
    StageStatus,
    StorytellingFormat,
    StorytellingGoal,
    StorytellingPerspective,
    SwotCluster,
    ThreatQuestion,
)
from .errc import Errc, ErrcGenerated, ErrcMove
from .fields import FromGeneratedMixin, SanitizedModel, strip_control_chars
from .generation import GENERATION_CONTRACTS
from .future_scenario import AdaptationQuestion, FutureScenario, FutureScenarioGenerated, FutureScenarioVariant
from .ideation import EpicenterClassification, Ideation, IdeationGenerated
from .optional_inputs import (
    BusinessCase,
    BusinessCaseGenerated,
    EnvironmentScan,
    EnvironmentScanGenerated,
    SalesScenario,
    Source,
    TeamInfo,
    TeamMember,
)
from .pattern import (
    CanvasGroup,
    CanvasGroupGenerated,
    PairwiseSegmentScore,
    PairwiseSegmentScoreGenerated,
    PatternsGenerated,
    PatternTag,
    Patterns,
    SegmentPair,
    SegmentPairGenerated,
    patterns_from_generated,
)
from .pitch import Pitch, PitchGenerated
from .stage_definition import StageDefinition
from .stage_registry import StageRegistry
from .storytelling import CanvasReference, Storytelling, StorytellingGenerated
from .swot import Swot, SwotAxisStatement, SwotClusterResult, SwotGenerated, SwotOpportunity, SwotThreat
from .validate_model import FieldFeedback, ValidateModelResult
from .wire import (
    ARTIFACT_ID_NAMESPACE,
    ARTIFACT_MODELS,
    ARTIFACT_STAGE,
    ArtifactRecord,
    ArtifactType,
    CanvasRowSpec,
    ProjectSnapshot,
    QueueMessage,
    RowTarget,
    StageEvent,
    StageFailure,
    StageResult,
    StageRow,
    canvas_rows_for,
    dependent_rows,
    derive_artifact_id,
    parse_artifact,
    project_status,
    ready_rows,
    row_of_artifact,
    validate_row_refs,
)

__all__ = [
    "MAX_SEGMENTS",
    "SWOT_CLUSTER_SECTIONS",
    "THREAT_QUESTIONS_BY_CLUSTER",
    "ThreatQuestion",
    # enums
    "CanvasBranch",
    "CanvasSection",
    "Epicenter",
    "ERRCActionType",
    "FreePatternSubtype",
    "OpenBusinessModelPatternSubtype",
    "Pattern",
    "PricingTier",
    "SegmentRelationType",
    "Stage",
    "StageAction",
    "StageErrorCode",
    "StageStatus",
    "StorytellingFormat",
    "StorytellingGoal",
    "StorytellingPerspective",
    "SwotCluster",
    # stage graph
    "STAGE_REGISTRY",
    "StageDefinition",
    "StageRegistry",
    # artifacts
    "Brief",
    "EmpathyMap",
    "CustomerScenario",
    "Ideation",
    "EpicenterClassification",
    "Patterns",
    "CanvasGroup",
    "PairwiseSegmentScore",
    "PatternTag",
    "SegmentPair",
    "Canvas",
    "CanvasCard",
    "CanvasSections",
    "Swot",
    "SwotAxisStatement",
    "SwotClusterResult",
    "SwotOpportunity",
    "SwotThreat",
    "Errc",
    "ErrcMove",
    "Storytelling",
    "CanvasReference",
    "FutureScenario",
    "FutureScenarioVariant",
    "AdaptationQuestion",
    "Pitch",
    "TeamInfo",
    "TeamMember",
    "BusinessCase",
    "SalesScenario",
    "EnvironmentScan",
    "Source",
    # generation contracts: what the LLM writes (see generation.py)
    "GENERATION_CONTRACTS",
    "EmpathyMapGenerated",
    "CustomerScenarioGenerated",
    "IdeationGenerated",
    "PatternsGenerated",
    "SegmentPairGenerated",
    "PairwiseSegmentScoreGenerated",
    "CanvasGroupGenerated",
    "patterns_from_generated",
    "SwotGenerated",
    "ErrcGenerated",
    "StorytellingGenerated",
    "FutureScenarioGenerated",
    "PitchGenerated",
    "BusinessCaseGenerated",
    "EnvironmentScanGenerated",
    "FromGeneratedMixin",
    # canvas generation contract
    "CanvasGenerated",
    "CanvasCardDraft",
    "CanvasSectionsGenerated",
    "GENERATED_CARDS_PER_SECTION_MIN",
    "GENERATED_CARDS_PER_SECTION_MAX",
    # side-channel contract (not a stage)
    "FieldFeedback",
    "ValidateModelResult",
    # wire contract between bizstruct-be and bizstruct-ml (ADR-0011, see wire.py)
    "ArtifactType",
    "ARTIFACT_STAGE",
    "ARTIFACT_MODELS",
    "ARTIFACT_ID_NAMESPACE",
    "ArtifactRecord",
    "StageRow",
    "ProjectSnapshot",
    "RowTarget",
    "QueueMessage",
    "StageFailure",
    "StageResult",
    "StageEvent",
    "CanvasRowSpec",
    "derive_artifact_id",
    "validate_row_refs",
    "ready_rows",
    "dependent_rows",
    "project_status",
    "canvas_rows_for",
    "row_of_artifact",
    "parse_artifact",
    # sanitizing base class
    "SanitizedModel",
    "strip_control_chars",
    # consistency
    "ConsistencyReport",
    "ConsistencyViolation",
    "ConsistencyRule",
    "JudgeCheck",
    "RuleInput",
    "StageArity",
    "CONSISTENCY_RULES",
    "JUDGE_CHECKS",
]
