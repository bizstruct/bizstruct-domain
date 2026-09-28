"""bizstruct-domain: single source of truth for the BizStruct domain model.

Re-exports enums, generation-chain definitions, and block models so
consumers (bizstruct-ml, bizstruct-be) can `import bizstruct_domain as bd`.
"""

from bizstruct_domain import enums
from bizstruct_domain.chain import STAGES, Stage, topological_order, validate_dag
from bizstruct_domain.enums import StageAction, StageErrorCode, StageStatus
from bizstruct_domain.stage_machine import (
    STAGE_IDS,
    STAGE_TRANSITIONS,
    StageLike,
    available_actions,
    dependents_of,
    is_valid_transition,
    ready_stages,
)
from bizstruct_domain.blocks.assessment import Assessment, ClusterAssessment, SWOTStatement
from bizstruct_domain.blocks.business_case import BusinessCase, CostItem, MarketBenchmark, SalesScenario
from bizstruct_domain.blocks.customer_scenario import CustomerScenario, ScenarioQuestion
from bizstruct_domain.blocks.empathy_map import EmpathyMap
from bizstruct_domain.blocks.ideation import Ideation
from bizstruct_domain.blocks.patterns import Patterns, PatternTag
from bizstruct_domain.blocks.scenario import AdaptationQuestion, FutureScenario, FutureScenarioCase
from bizstruct_domain.blocks.pitch import Pitch
from bizstruct_domain.blocks.hypotheses import Hypothesis, Hypotheses
from bizstruct_domain.blocks.models_options import BusinessModelOption, ModelsOptions
from bizstruct_domain.blocks.canvas import CanvasCard, Canvas, CanvasGenerated
from bizstruct_domain.blocks.errc import ERRC, ERRCAlternative, ERRCGenerated, ERRCMove
from bizstruct_domain.blocks.team_info import TeamInfo, TeamMember
from bizstruct_domain.sanitize import SanitizedModel
from bizstruct_domain.validate_model import FieldFeedback, ValidateModelResult

__all__ = [
    "enums",
    "SanitizedModel",
    "STAGES",
    "Stage",
    "topological_order",
    "validate_dag",
    "StageAction",
    "StageErrorCode",
    "StageStatus",
    "STAGE_IDS",
    "STAGE_TRANSITIONS",
    "StageLike",
    "available_actions",
    "dependents_of",
    "is_valid_transition",
    "ready_stages",
    "Assessment",
    "ClusterAssessment",
    "SWOTStatement",
    "BusinessCase",
    "CostItem",
    "MarketBenchmark",
    "SalesScenario",
    "CustomerScenario",
    "ScenarioQuestion",
    "EmpathyMap",
    "Ideation",
    "Patterns",
    "PatternTag",
    "AdaptationQuestion",
    "FutureScenario",
    "FutureScenarioCase",
    "Pitch",
    "Hypothesis",
    "Hypotheses",
    "BusinessModelOption",
    "ModelsOptions",
    "CanvasCard",
    "Canvas",
    "CanvasGenerated",
    "ERRC",
    "ERRCAlternative",
    "ERRCGenerated",
    "ERRCMove",
    "TeamInfo",
    "TeamMember",
    "FieldFeedback",
    "ValidateModelResult",
]

__version__ = "0.11.0"
