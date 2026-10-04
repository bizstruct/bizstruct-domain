from enum import StrEnum


class Epicenter(StrEnum):
    """
        An enumeration of the different types of epicenters.
    """
    RESOURCE_DRIVEN = "resource_driven"
    OFFER_DRIVEN = "offer_driven"
    CUSTOMER_DRIVEN = "customer_driven"
    FINANCE_DRIVEN = "finance_driven"
    MULTIPLE_EPICENTER = "multiple_epicenter"


class Pattern(StrEnum):
    """
        An enumeration of the different types of business model patterns.
    """
    UNBUNDLING = "unbundling"
    LONG_TAIL = "long_tail"
    MULTI_SIDED_PLATFORM = "multi_sided_platform"
    FREE = "free"
    OPEN_BUSINESS_MODEL = "open_business_model"


class FreePatternSubtype(StrEnum):
    """
        An enumeration of the different subtypes of the "free" business model pattern.
    """
    FREEMIUM = "freemium"
    AD_SUPPORTED = "ad_supported"
    BAIT_AND_HOOK = "bait_and_hook"


class OpenBusinessModelPatternSubtype(StrEnum):
    """
        An enumeration of the different subtypes of the "open business model" pattern.
    """
    OUTSIDE_IN = "outside_in"
    INSIDE_OUT = "inside_out"


class SegmentRelationType(StrEnum):
    """
        An enumeration of the different types of segment relations.

        The book's Customer Segments building block (pp. 20-21) describes
        five segment types: Mass market, Niche market, Segmented,
        Diversified, and Multi-sided platforms. Only the last three
        describe a relationship BETWEEN two or more distinct segments;
        Mass market and Niche market describe a single-segment model and
        therefore have no "relation" to classify. Since this enum exists
        specifically to tag how multiple segments relate to each other
        within one canvas group, only those three carry over here.
    """
    MULTI_SIDED = "multi_sided"
    SEGMENTED = "segmented"
    DIVERSIFIED = "diversified"


class CanvasBranch(StrEnum):
    UNIFIED_MODEL = "unified_model"
    SPLIT_MODEL = "split_model"


class CanvasSection(StrEnum):
    """
        An enumeration of the different sections of a business model canvas.
    """
    VALUE_PROPOSITIONS = "value_propositions" # VP
    CUSTOMER_SEGMENTS = "customer_segments" # CS
    CHANNELS = "channels" # CH
    CUSTOMER_RELATIONSHIPS = "customer_relationships" # CR
    REVENUE_STREAMS = "revenue_streams" # R$
    KEY_RESOURCES = "key_resources" # KR
    KEY_ACTIVITIES = "key_activities" # KA
    KEY_PARTNERSHIPS = "key_partnerships" # KP
    COST_STRUCTURE = "cost_structure" # C$


class SwotCluster(StrEnum):
    """
        An enumeration of the different clusters in a SWOT analysis.
    """
    VALUE_PROPOSITION = "value_proposition"  # VP
    COST_REVENUE = "cost_revenue"  # R$ + C$
    INFRASTRUCTURE = "infrastructure"  # KR + KA + KP
    CUSTOMER_INTERFACE = "customer_interface"  # CS + CH + CR


class ThreatQuestion(StrEnum):
    """
        The fixed catalog of 21 threats rated in every SWOT iteration, so the
        threat part of `weighted_weakness_threat_score` always sums over the
        same questions (range 21..105) and is comparable between iterations.
        The values are stable contract ids. The comments are paraphrases, one
        per question, of the threat the id stands for.
    """
    # value_proposition
    SUBSTITUTES_AVAILABLE = "substitutes_available"  # customers can get the same job done with a different product
    COMPETITOR_PRICE_OR_VALUE_PRESSURE = "competitor_price_or_value_pressure"  # rivals undercut our price or beat our value
    # cost_revenue
    MARGIN_PRESSURE = "margin_pressure"  # our margins are being squeezed
    REVENUE_CONCENTRATION = "revenue_concentration"  # too much income rests on too few payers or sources
    REVENUE_STREAM_DECLINE = "revenue_stream_decline"  # a stream we rely on is shrinking
    COST_UNPREDICTABILITY = "cost_unpredictability"  # key costs are hard to forecast or control
    COST_OUTGROWING_REVENUE = "cost_outgrowing_revenue"  # costs may rise faster than income
    # infrastructure
    RESOURCE_SUPPLY_DISRUPTION = "resource_supply_disruption"  # a key resource may become unavailable
    RESOURCE_QUALITY_RISK = "resource_quality_risk"  # a key resource may degrade in quality
    KEY_ACTIVITY_DISRUPTION = "key_activity_disruption"  # a core activity may be interrupted
    ACTIVITY_QUALITY_RISK = "activity_quality_risk"  # a core activity may be carried out worse than needed
    PARTNER_LOSS = "partner_loss"  # a key partner may leave
    PARTNER_DEFECTION_TO_COMPETITORS = "partner_defection_to_competitors"  # a partner may start serving rivals
    PARTNER_OVER_DEPENDENCE = "partner_over_dependence"  # we lean too heavily on one partner
    # customer_interface
    MARKET_SATURATION = "market_saturation"  # the market may have no room left to grow into
    MARKET_SHARE_PRESSURE = "market_share_pressure"  # our share of the market may be eroding
    CUSTOMER_DEFECTION = "customer_defection"  # customers may leave us
    COMPETITION_INTENSIFYING = "competition_intensifying"  # the competitive field may get harsher
    CHANNEL_THREAT_FROM_COMPETITORS = "channel_threat_from_competitors"  # rivals may take over the routes to our customers
    CHANNEL_IRRELEVANCE = "channel_irrelevance"  # our channels may stop being where customers are
    RELATIONSHIP_DETERIORATION = "relationship_deterioration"  # customer relationships may weaken


# The catalog per SWOT cluster: 2, 5, 7 and 7 questions. Each question belongs
# to exactly one cluster; together they are all 21.
THREAT_QUESTIONS_BY_CLUSTER: dict[SwotCluster, tuple[ThreatQuestion, ...]] = {
    SwotCluster.VALUE_PROPOSITION: (
        ThreatQuestion.SUBSTITUTES_AVAILABLE,
        ThreatQuestion.COMPETITOR_PRICE_OR_VALUE_PRESSURE,
    ),
    SwotCluster.COST_REVENUE: (
        ThreatQuestion.MARGIN_PRESSURE,
        ThreatQuestion.REVENUE_CONCENTRATION,
        ThreatQuestion.REVENUE_STREAM_DECLINE,
        ThreatQuestion.COST_UNPREDICTABILITY,
        ThreatQuestion.COST_OUTGROWING_REVENUE,
    ),
    SwotCluster.INFRASTRUCTURE: (
        ThreatQuestion.RESOURCE_SUPPLY_DISRUPTION,
        ThreatQuestion.RESOURCE_QUALITY_RISK,
        ThreatQuestion.KEY_ACTIVITY_DISRUPTION,
        ThreatQuestion.ACTIVITY_QUALITY_RISK,
        ThreatQuestion.PARTNER_LOSS,
        ThreatQuestion.PARTNER_DEFECTION_TO_COMPETITORS,
        ThreatQuestion.PARTNER_OVER_DEPENDENCE,
    ),
    SwotCluster.CUSTOMER_INTERFACE: (
        ThreatQuestion.MARKET_SATURATION,
        ThreatQuestion.MARKET_SHARE_PRESSURE,
        ThreatQuestion.CUSTOMER_DEFECTION,
        ThreatQuestion.COMPETITION_INTENSIFYING,
        ThreatQuestion.CHANNEL_THREAT_FROM_COMPETITORS,
        ThreatQuestion.CHANNEL_IRRELEVANCE,
        ThreatQuestion.RELATIONSHIP_DETERIORATION,
    ),
}


# Which canvas sections each SWOT cluster covers (see the comments on
# SwotCluster). Disjoint, and together exactly the nine sections.
SWOT_CLUSTER_SECTIONS: dict[SwotCluster, frozenset[CanvasSection]] = {
    SwotCluster.VALUE_PROPOSITION: frozenset({CanvasSection.VALUE_PROPOSITIONS}),
    SwotCluster.COST_REVENUE: frozenset({CanvasSection.REVENUE_STREAMS, CanvasSection.COST_STRUCTURE}),
    SwotCluster.INFRASTRUCTURE: frozenset(
        {CanvasSection.KEY_RESOURCES, CanvasSection.KEY_ACTIVITIES, CanvasSection.KEY_PARTNERSHIPS}
    ),
    SwotCluster.CUSTOMER_INTERFACE: frozenset(
        {CanvasSection.CUSTOMER_SEGMENTS, CanvasSection.CHANNELS, CanvasSection.CUSTOMER_RELATIONSHIPS}
    ),
}


class ERRCActionType(StrEnum):
    """
        An enumeration of the different types of ERRC actions.
    """
    ELIMINATE = "eliminate"
    REDUCE = "reduce"
    RAISE = "raise"
    CREATE = "create"


class StorytellingPerspective(StrEnum):
    """
        An enumeration of the different perspectives in storytelling.
    """
    COMPANY = "company"
    CUSTOMER = "customer"


class StorytellingGoal(StrEnum):
    """
        An enumeration of the different goals in storytelling.
    """
    INTRODUCING_NEW = "introducing_new"
    ENGAGING_EMPLOYEES = "engaging_employees"
    PITCHING_INVESTORS = "pitching_investors"


class StorytellingFormat(StrEnum):
    """
        An enumeration of the different formats in storytelling.
    """
    TALK_AND_IMAGE = "talk_and_image"
    VIDEO_CLIP = "video_clip"
    ROLE_PLAY = "role_play"
    TEXT_AND_IMAGE = "text_and_image"
    COMIC_STRIP = "comic_strip"


class PricingTier(StrEnum):
    """
        An enumeration of the different pricing tiers.
    """
    PREMIUM = "premium"
    MID_MARKET = "mid_market"
    LOW_COST = "low_cost"


class Stage(StrEnum):
    """
    Enum representing the different stages of a chain.
    """
    BRIEF = "brief"
    EMPATHY_MAP = "empathy_map"
    CUSTOMER_SCENARIO = "customer_scenario"
    IDEATION = "ideation"
    PATTERNS = "patterns"
    CANVAS = "canvas"
    SWOT_ERRC_CYCLE = "swot_errc_cycle"
    STORYTELLING = "storytelling"
    FUTURE_SCENARIO = "future_scenario"
    PITCH = "pitch"
    
    TEAM_INFO = "team_info"
    BUSINESS_CASE = "business_case"
    ENVIRONMENT_SCAN = "environment_scan"


class StageStatus(StrEnum):
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


class StageErrorCode(StrEnum):
    """Reason a stage entered `StageStatus.ERROR`.

    `error` is reserved for external failures and cancellation, never for
    reaching the retry limit (that goes to `awaiting_decision` instead).
    """

    GENERATION_FAILED = "generation_failed"
    CHECK_FAILED = "check_failed"
    QUEUE_UNAVAILABLE = "queue_unavailable"
    CANCELED_BY_USER = "canceled_by_user"
    STUCK_TIMEOUT = "stuck_timeout"


class StageAction(StrEnum):
    """A user-facing action offered for a stage, given its current status.

    See `bizstruct_domain.stage_machine.available_actions`.
    """

    APPROVE = "approve"
    REGENERATE = "regenerate"
    RETRY = "retry"
