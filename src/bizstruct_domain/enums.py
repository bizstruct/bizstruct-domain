"""
    Shared enums for the BizStruct domain model.
    
    All enums are `str, Enum` so they serialize as plain strings in JSON /
    OpenAI structured output and compare equal to their string values.
"""

from enum import StrEnum


class Epicenter(StrEnum):
    """
        Epicentres of business model innovation.

        Osterwalder & Pigneur, "Business Model Generation" — Ideation,
        Epicentres of Business Model Innovation. The book names four
        epicentres plus "multiple-epicenter driven" innovation. Only the four
        are values here: "multiple" is expressed as `Ideation.epicenters`
        holding more than one value, not as a fifth value that would duplicate
        that meaning (see docs/adr/0008-bmg-domain-rewrite.md). Do not add
        invented values (e.g. a "competitor-driven" epicenter is not part
        of the methodology).
    """

    RESOURCE_DRIVEN = "resource_driven"
    OFFER_DRIVEN = "offer_driven"
    CUSTOMER_DRIVEN = "customer_driven"
    FINANCE_DRIVEN = "finance_driven"



class Pattern(StrEnum):
    """Business model patterns.

    Osterwalder & Pigneur, "Business Model Generation" — Part 2,
    Patterns. Exactly 5 canonical values; do not add invented values
    (e.g. "PAID" is not part of the methodology).
    """

    UNBUNDLING = "unbundling"
    LONG_TAIL = "long_tail"
    MULTI_SIDED_PLATFORM = "multi_sided_platform"
    FREE = "free"
    OPEN_BUSINESS_MODEL = "open_business_model"



class PatternSubtype(StrEnum):
    """Subtypes that refine specific patterns.

    Only meaningful in combination with `Pattern.FREE`
    (`freemium`, `ad_supported`, `bait_and_hook`) or
    `Pattern.OPEN_BUSINESS_MODEL` (`outside_in`, `inside_out`).
    See `PATTERN_SUBTYPES` below for the full mapping.
    """

    FREEMIUM = "freemium"
    AD_SUPPORTED = "ad_supported"
    BAIT_AND_HOOK = "bait_and_hook"
    OUTSIDE_IN = "outside_in"
    INSIDE_OUT = "inside_out"


PATTERN_SUBTYPES: dict[Pattern, set[PatternSubtype]] = {
    Pattern.UNBUNDLING: set(),
    Pattern.LONG_TAIL: set(),
    Pattern.MULTI_SIDED_PLATFORM: set(),
    Pattern.FREE: {
        PatternSubtype.FREEMIUM,
        PatternSubtype.AD_SUPPORTED,
        PatternSubtype.BAIT_AND_HOOK,
    },
    Pattern.OPEN_BUSINESS_MODEL: {
        PatternSubtype.OUTSIDE_IN,
        PatternSubtype.INSIDE_OUT,
    },
}





class HypothesisCategoryStrEnum(StrEnum):
    """Testing Business Ideas risk categories: Desirability / Viability / Feasibility."""

    DESIRABILITY = "desirability"
    VIABILITY = "viability"
    FEASIBILITY = "feasibility"


class Quadrant(str, Enum):
    """Hypothesis prioritization matrix: importance x uncertainty.

    ADR-decided semantics (see docs/adr/0001-generation-stages.md context
    for how hypotheses feed into the chain):

    - Q1: high importance, high uncertainty — test first.
    - Q2: high importance, low uncertainty.
    - Q3: low importance, high uncertainty.
    - Q4: low importance, low uncertainty.
    """

    Q1 = "q1"
    Q2 = "q2"
    Q3 = "q3"
    Q4 = "q4"



class ERRCStatus(str, StrEnum):
    """Lifecycle status of an ERRC alternative."""

    DRAFT = "draft"
    APPLIED = "applied"



class ERRCAction(str, StrEnum):
    """Blue Ocean Strategy ERRC grid actions.

    `raise` is a reserved Python keyword, so the member name is `RAISE_`
    while the serialized value stays the plain string "raise".
    """

    ELIMINATE = "eliminate"
    REDUCE = "reduce"
    RAISE_ = "raise"
    CREATE = "create"



class CanvasBranchingDecision(StrEnum):
    """How many canvases the Patterns stage decides to build.

    Project decision on top of BMG (see docs/adr/0008-bmg-domain-rewrite.md):
    - A_SHARED: one canvas shared by every customer segment.
    - B_BRANCHING: one canvas per customer segment.

    This is only the classification result. Creating the one or N canvas
    instances is bizstruct-be's job, not this package's.
    """

    A_SHARED = "a_shared"
    B_BRANCHING = "b_branching"


class CanvasDetailLevel(StrEnum):
    """Level of detail of a canvas.

    BMG, Design -> Prototyping (p. 165): napkin sketch, elaborated canvas,
    business case.
    """

    NAPKIN = "napkin"
    ELABORATED = "elaborated"
    BUSINESS_CASE = "business_case"


class SWOTCluster(StrEnum):
    """The four canvas clusters a SWOT assessment is grouped by.

    BMG, Strategy -> Evaluating Business Models (pp. 217-223): the book
    does not assess the nine blocks one by one but in these four groups.
    See `SWOT_CLUSTER_SECTIONS` for which blocks each one covers.
    """

    VALUE_PROPOSITION = "value_proposition"
    COST_REVENUE = "cost_revenue"
    INFRASTRUCTURE = "infrastructure"
    CUSTOMER_INTERFACE = "customer_interface"


class ScenarioAdaptationArea(StrEnum):
    """Canvas areas a future scenario asks adaptation questions about.

    BMG, Design -> Scenarios, type 2 (pp. 187-188): value proposition, key
    resources/activities, revenue, costs, partnerships, customer
    relationships.
    """

    VALUE_PROPOSITION = "value_proposition"
    KEY_RESOURCES_ACTIVITIES = "key_resources_activities"
    REVENUE_STREAMS = "revenue_streams"
    COST_STRUCTURE = "cost_structure"
    KEY_PARTNERS = "key_partners"
    CUSTOMER_RELATIONSHIPS = "customer_relationships"


class PitchAudience(str, StrEnum):
    """Target audience for a generated pitch."""

    INVESTOR = "investor"
    CUSTOMER = "customer"



class MonetizationType(str, StrEnum):
    """How a business model option makes money."""

    SUBSCRIPTION = "subscription"
    TRANSACTION_FEE = "transaction_fee"
    RETAINER_PLUS_SAAS = "retainer_plus_saas"
    ADVERTISING = "advertising"
    LICENSING = "licensing"
    MARKETPLACE_TAKE_RATE = "marketplace_take_rate"



class CanvasSection(str, StrEnum):
    """The nine building blocks of the Business Model Canvas."""

    KEY_PARTNERS = "key_partners"
    KEY_ACTIVITIES = "key_activities"
    KEY_RESOURCES = "key_resources"
    VALUE_PROPOSITIONS = "value_propositions"
    CUSTOMER_RELATIONSHIPS = "customer_relationships"
    CHANNELS = "channels"
    CUSTOMER_SEGMENTS = "customer_segments"
    COST_STRUCTURE = "cost_structure"
    REVENUE_STREAMS = "revenue_streams"


SWOT_CLUSTER_SECTIONS: dict[SWOTCluster, frozenset[CanvasSection]] = {
    SWOTCluster.VALUE_PROPOSITION: frozenset({CanvasSection.VALUE_PROPOSITIONS}),
    SWOTCluster.COST_REVENUE: frozenset({CanvasSection.REVENUE_STREAMS, CanvasSection.COST_STRUCTURE}),
    SWOTCluster.INFRASTRUCTURE: frozenset({
        CanvasSection.KEY_RESOURCES,
        CanvasSection.KEY_ACTIVITIES,
        CanvasSection.KEY_PARTNERS,
    }),
    SWOTCluster.CUSTOMER_INTERFACE: frozenset({
        CanvasSection.CUSTOMER_SEGMENTS,
        CanvasSection.CHANNELS,
        CanvasSection.CUSTOMER_RELATIONSHIPS,
    }),
}



class StageStatus(str, StrEnum):
    """Lifecycle status of a single stage in the generation chain.

    See `bizstruct_domain.stage_machine` for the allowed-transition table
    between these statuses.
    """

    PENDING = "pending"
    RUNNING = "running"
    CONSISTENCY_CHECK = "consistency_check"
    AWAITING_DECISION = "awaiting_decision"
    NEEDS_RETRY = "needs_retry"
    DONE = "done"
    ERROR = "error"



class StageErrorCode(str, StrEnum):
    """Reason a stage entered `StageStatus.ERROR`.

    `error` is reserved for external failures and cancellation, never for
    reaching the retry limit (that goes to `awaiting_decision` instead).
    """

    GENERATION_FAILED = "generation_failed"
    CHECK_FAILED = "check_failed"
    QUEUE_UNAVAILABLE = "queue_unavailable"
    CANCELED_BY_USER = "canceled_by_user"
    STUCK_TIMEOUT = "stuck_timeout"



class StageAction(str, StrEnum):
    """A user-facing action offered for a stage, given its current status.

    See `bizstruct_domain.stage_machine.available_actions`.
    """

    APPROVE = "approve"
    REGENERATE = "regenerate"
    RETRY = "retry"
