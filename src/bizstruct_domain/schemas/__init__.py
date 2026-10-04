"""Public API of the BMG domain model (13-stage graph, artifacts, consistency).

Import from here rather than from the individual modules:

    from bizstruct_domain.schemas import Canvas, STAGE_REGISTRY, Stage
"""

from .brief import Brief
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
from .customer_scenario import CustomerScenario
from .empathy_map import EmpathyMap
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
from .errc import Errc, ErrcMove
from .fields import SanitizedModel, strip_control_chars
from .future_scenario import AdaptationQuestion, FutureScenario, FutureScenarioVariant
from .ideation import EpicenterClassification, Ideation
from .optional_inputs import (
    BusinessCase,
    EnvironmentScan,
    SalesScenario,
    Source,
    TeamInfo,
    TeamMember,
)
from .pattern import CanvasGroup, PairwiseSegmentScore, PatternTag, Patterns, SegmentPair
from .pitch import Pitch
from .stage_definition import StageDefinition
from .stage_registry import StageRegistry
from .storytelling import CanvasReference, Storytelling
from .swot import Swot, SwotAxisStatement, SwotClusterResult, SwotOpportunity, SwotThreat
from .validate_model import FieldFeedback, ValidateModelResult

__all__ = [
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
    # generation-time contract
    "CanvasGenerated",
    "CanvasCardDraft",
    "CanvasSectionsGenerated",
    "GENERATED_CARDS_PER_SECTION_MIN",
    "GENERATED_CARDS_PER_SECTION_MAX",
    # side-channel contract (not a stage)
    "FieldFeedback",
    "ValidateModelResult",
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
