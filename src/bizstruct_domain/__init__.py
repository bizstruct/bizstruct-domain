"""bizstruct-domain: single source of truth for the BizStruct domain model.

Re-exports the BMG schemas (`bizstruct_domain.schemas`) and the stage state
machine so consumers (bizstruct-ml, bizstruct-be) can `import bizstruct_domain as bd`.
"""

from bizstruct_domain import schemas
from bizstruct_domain.schemas import *  # noqa: F401,F403
from bizstruct_domain.stage_machine import (
    STAGE_IDS,
    STAGE_TRANSITIONS,
    StageLike,
    available_actions,
    dependents_of,
    is_valid_transition,
    ready_stages,
)

__all__ = [
    *schemas.__all__,
    "STAGE_IDS",
    "STAGE_TRANSITIONS",
    "StageLike",
    "available_actions",
    "dependents_of",
    "is_valid_transition",
    "ready_stages",
]

__version__ = "0.14.0"
