"""bizstruct-domain: single source of truth for the BizStruct domain model.

Re-exports enums, generation-chain definitions, and block models so
consumers (bizstruct-ml, bizstruct-be) can `import bizstruct_domain as bd`.
"""

from bizstruct_domain import enums
from bizstruct_domain.chain import STAGES, Stage, StageMode, stages_for_mode, topological_order
from bizstruct_domain.blocks.architecture import Architecture
from bizstruct_domain.blocks.empathy_map import EmpathyMap
from bizstruct_domain.blocks.scenario import Scenario
from bizstruct_domain.blocks.pitch import Pitch

__all__ = [
    "enums",
    "STAGES",
    "Stage",
    "StageMode",
    "stages_for_mode",
    "topological_order",
    "Architecture",
    "EmpathyMap",
    "Scenario",
    "Pitch",
]

__version__ = "0.4.0"
