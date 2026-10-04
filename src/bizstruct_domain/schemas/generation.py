"""Generation contracts: what the LLM writes, per stage.

A generation contract contains ONLY what the LLM writes. System fields are
excluded: ids, foreign keys, versions, `is_final`/`is_generated`, and any value
that must come from a real source (`sources` with their `retrieved_at`).
The persisted model extends its generation model and adds the system fields;
`X.from_generated(generated, **system_fields)` (or `Canvas.from_generated`,
`patterns_from_generated`) converts, running every persisted validator.

`GENERATION_CONTRACTS` maps each stage to the model(s) the LLM is asked for:
the JSON Schema of each is the `response_format`. TEAM_INFO has none (user
input).
"""

from .brief import Brief
from .canvas import CanvasGenerated
from .customer_scenario import CustomerScenarioGenerated
from .empathy_map import EmpathyMapGenerated
from .enums import Stage
from .errc import ErrcGenerated
from .future_scenario import FutureScenarioGenerated
from .ideation import IdeationGenerated
from .optional_inputs import BusinessCaseGenerated, EnvironmentScanGenerated
from .pattern import PatternsGenerated
from .pitch import PitchGenerated
from .storytelling import StorytellingGenerated
from .swot import SwotGenerated

GENERATION_CONTRACTS: dict[Stage, tuple[type, ...]] = {
    # Brief has no system fields: it is its own contract.
    Stage.BRIEF: (Brief,),
    Stage.EMPATHY_MAP: (EmpathyMapGenerated,),
    Stage.CUSTOMER_SCENARIO: (CustomerScenarioGenerated,),
    Stage.IDEATION: (IdeationGenerated,),
    Stage.PATTERNS: (PatternsGenerated,),
    Stage.CANVAS: (CanvasGenerated,),
    # One stage, two artifacts: the SWOT and the ERRC moves.
    Stage.SWOT_ERRC_CYCLE: (SwotGenerated, ErrcGenerated),
    Stage.STORYTELLING: (StorytellingGenerated,),
    Stage.FUTURE_SCENARIO: (FutureScenarioGenerated,),
    Stage.PITCH: (PitchGenerated,),
    Stage.BUSINESS_CASE: (BusinessCaseGenerated,),
    Stage.ENVIRONMENT_SCAN: (EnvironmentScanGenerated,),
}
