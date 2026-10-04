"""Pins the exact members and values of every enum.

Enum values are persisted (database rows, canvas JSON) and appear in the
exported JSON Schemas, so adding, removing or renaming a member is a
contract change that must be a deliberate edit here and a version bump, not a
silent drift that consumers find at runtime. (Replaces the old test_enums,
whose count/subtype checks pinned the previous design's enums.)
"""

import enum

import pytest

import bizstruct_domain.schemas.enums as enums_module

EXPECTED: dict[str, dict[str, str]] = {
    "Epicenter": {
        "RESOURCE_DRIVEN": "resource_driven",
        "OFFER_DRIVEN": "offer_driven",
        "CUSTOMER_DRIVEN": "customer_driven",
        "FINANCE_DRIVEN": "finance_driven",
        "MULTIPLE_EPICENTER": "multiple_epicenter",
    },
    "Pattern": {
        "UNBUNDLING": "unbundling",
        "LONG_TAIL": "long_tail",
        "MULTI_SIDED_PLATFORM": "multi_sided_platform",
        "FREE": "free",
        "OPEN_BUSINESS_MODEL": "open_business_model",
    },
    "FreePatternSubtype": {
        "FREEMIUM": "freemium",
        "AD_SUPPORTED": "ad_supported",
        "BAIT_AND_HOOK": "bait_and_hook",
    },
    "OpenBusinessModelPatternSubtype": {"OUTSIDE_IN": "outside_in", "INSIDE_OUT": "inside_out"},
    "SegmentRelationType": {"MULTI_SIDED": "multi_sided", "SEGMENTED": "segmented", "DIVERSIFIED": "diversified"},
    "CanvasBranch": {"UNIFIED_MODEL": "unified_model", "SPLIT_MODEL": "split_model"},
    "CanvasSection": {
        "VALUE_PROPOSITIONS": "value_propositions",
        "CUSTOMER_SEGMENTS": "customer_segments",
        "CHANNELS": "channels",
        "CUSTOMER_RELATIONSHIPS": "customer_relationships",
        "REVENUE_STREAMS": "revenue_streams",
        "KEY_RESOURCES": "key_resources",
        "KEY_ACTIVITIES": "key_activities",
        "KEY_PARTNERSHIPS": "key_partnerships",
        "COST_STRUCTURE": "cost_structure",
    },
    "SwotCluster": {
        "VALUE_PROPOSITION": "value_proposition",
        "COST_REVENUE": "cost_revenue",
        "INFRASTRUCTURE": "infrastructure",
        "CUSTOMER_INTERFACE": "customer_interface",
    },
    "ERRCActionType": {"ELIMINATE": "eliminate", "REDUCE": "reduce", "RAISE": "raise", "CREATE": "create"},
    "StorytellingPerspective": {"COMPANY": "company", "CUSTOMER": "customer"},
    "StorytellingGoal": {
        "INTRODUCING_NEW": "introducing_new",
        "ENGAGING_EMPLOYEES": "engaging_employees",
        "PITCHING_INVESTORS": "pitching_investors",
    },
    "StorytellingFormat": {
        "TALK_AND_IMAGE": "talk_and_image",
        "VIDEO_CLIP": "video_clip",
        "ROLE_PLAY": "role_play",
        "TEXT_AND_IMAGE": "text_and_image",
        "COMIC_STRIP": "comic_strip",
    },
    "PricingTier": {"PREMIUM": "premium", "MID_MARKET": "mid_market", "LOW_COST": "low_cost"},
    "ThreatQuestion": {
        "SUBSTITUTES_AVAILABLE": "substitutes_available",
        "COMPETITOR_PRICE_OR_VALUE_PRESSURE": "competitor_price_or_value_pressure",
        "MARGIN_PRESSURE": "margin_pressure",
        "REVENUE_CONCENTRATION": "revenue_concentration",
        "REVENUE_STREAM_DECLINE": "revenue_stream_decline",
        "COST_UNPREDICTABILITY": "cost_unpredictability",
        "COST_OUTGROWING_REVENUE": "cost_outgrowing_revenue",
        "RESOURCE_SUPPLY_DISRUPTION": "resource_supply_disruption",
        "RESOURCE_QUALITY_RISK": "resource_quality_risk",
        "KEY_ACTIVITY_DISRUPTION": "key_activity_disruption",
        "ACTIVITY_QUALITY_RISK": "activity_quality_risk",
        "PARTNER_LOSS": "partner_loss",
        "PARTNER_DEFECTION_TO_COMPETITORS": "partner_defection_to_competitors",
        "PARTNER_OVER_DEPENDENCE": "partner_over_dependence",
        "MARKET_SATURATION": "market_saturation",
        "MARKET_SHARE_PRESSURE": "market_share_pressure",
        "CUSTOMER_DEFECTION": "customer_defection",
        "COMPETITION_INTENSIFYING": "competition_intensifying",
        "CHANNEL_THREAT_FROM_COMPETITORS": "channel_threat_from_competitors",
        "CHANNEL_IRRELEVANCE": "channel_irrelevance",
        "RELATIONSHIP_DETERIORATION": "relationship_deterioration",
    },
    "Stage": {
        "BRIEF": "brief",
        "EMPATHY_MAP": "empathy_map",
        "CUSTOMER_SCENARIO": "customer_scenario",
        "IDEATION": "ideation",
        "PATTERNS": "patterns",
        "CANVAS": "canvas",
        "SWOT_ERRC_CYCLE": "swot_errc_cycle",
        "STORYTELLING": "storytelling",
        "FUTURE_SCENARIO": "future_scenario",
        "PITCH": "pitch",
        "TEAM_INFO": "team_info",
        "BUSINESS_CASE": "business_case",
        "ENVIRONMENT_SCAN": "environment_scan",
    },
    "StageStatus": {
        "PENDING": "pending",
        "RUNNING": "running",
        "CONSISTENCY_CHECK": "consistency_check",
        "AWAITING_DECISION": "awaiting_decision",
        "NEEDS_RETRY": "needs_retry",
        "DONE": "done",
        "ERROR": "error",
    },
    "StageErrorCode": {
        "GENERATION_FAILED": "generation_failed",
        "CHECK_FAILED": "check_failed",
        "QUEUE_UNAVAILABLE": "queue_unavailable",
        "CANCELED_BY_USER": "canceled_by_user",
        "STUCK_TIMEOUT": "stuck_timeout",
    },
    "StageAction": {"APPROVE": "approve", "REGENERATE": "regenerate", "RETRY": "retry"},
}


def _defined_enums() -> dict[str, type[enum.Enum]]:
    return {
        name: obj
        for name, obj in vars(enums_module).items()
        if isinstance(obj, type) and issubclass(obj, enum.Enum) and obj.__module__ == enums_module.__name__
    }


def test_every_enum_is_pinned():
    assert set(_defined_enums()) == set(EXPECTED)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_members_and_values_are_exactly_the_contract(name):
    actual = {member.name: member.value for member in _defined_enums()[name]}
    assert actual == EXPECTED[name]


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_enums_are_str_enums(name):
    cls = _defined_enums()[name]
    assert issubclass(cls, enum.StrEnum)


def test_canvas_section_values_are_the_canvas_sections_field_names():
    # Canvas.get_section does getattr(sections, section.value).
    from bizstruct_domain.schemas import CanvasSections

    assert {s.value for s in enums_module.CanvasSection} == set(CanvasSections.model_fields)


def test_removed_values_stay_removed():
    values = {e.value for e in enums_module.Epicenter}
    assert "competitor_driven" not in values  # not part of the methodology
    assert "paid" not in {p.value for p in enums_module.Pattern}
    assert "key_partners" not in {s.value for s in enums_module.CanvasSection}


def test_swot_clusters_partition_the_nine_canvas_sections():
    mapping = enums_module.SWOT_CLUSTER_SECTIONS
    assert set(mapping) == set(enums_module.SwotCluster)
    covered = [section for sections in mapping.values() for section in sections]
    assert len(covered) == len(set(covered)), "a section belongs to two clusters"
    assert set(covered) == set(enums_module.CanvasSection)


def test_swot_cluster_sections_are_the_contract():
    S, C = enums_module.SwotCluster, enums_module.CanvasSection
    assert enums_module.SWOT_CLUSTER_SECTIONS == {
        S.VALUE_PROPOSITION: {C.VALUE_PROPOSITIONS},
        S.COST_REVENUE: {C.REVENUE_STREAMS, C.COST_STRUCTURE},
        S.INFRASTRUCTURE: {C.KEY_RESOURCES, C.KEY_ACTIVITIES, C.KEY_PARTNERSHIPS},
        S.CUSTOMER_INTERFACE: {C.CUSTOMER_SEGMENTS, C.CHANNELS, C.CUSTOMER_RELATIONSHIPS},
    }


def test_swot_cluster_sections_values_are_immutable():
    assert all(isinstance(v, frozenset) for v in enums_module.SWOT_CLUSTER_SECTIONS.values())


def test_threat_questions_by_cluster_is_the_contract():
    S, T = enums_module.SwotCluster, enums_module.ThreatQuestion
    assert enums_module.THREAT_QUESTIONS_BY_CLUSTER == {
        S.VALUE_PROPOSITION: (T.SUBSTITUTES_AVAILABLE, T.COMPETITOR_PRICE_OR_VALUE_PRESSURE),
        S.COST_REVENUE: (
            T.MARGIN_PRESSURE, T.REVENUE_CONCENTRATION, T.REVENUE_STREAM_DECLINE,
            T.COST_UNPREDICTABILITY, T.COST_OUTGROWING_REVENUE,
        ),
        S.INFRASTRUCTURE: (
            T.RESOURCE_SUPPLY_DISRUPTION, T.RESOURCE_QUALITY_RISK, T.KEY_ACTIVITY_DISRUPTION,
            T.ACTIVITY_QUALITY_RISK, T.PARTNER_LOSS, T.PARTNER_DEFECTION_TO_COMPETITORS,
            T.PARTNER_OVER_DEPENDENCE,
        ),
        S.CUSTOMER_INTERFACE: (
            T.MARKET_SATURATION, T.MARKET_SHARE_PRESSURE, T.CUSTOMER_DEFECTION,
            T.COMPETITION_INTENSIFYING, T.CHANNEL_THREAT_FROM_COMPETITORS, T.CHANNEL_IRRELEVANCE,
            T.RELATIONSHIP_DETERIORATION,
        ),
    }
    assert [len(v) for v in enums_module.THREAT_QUESTIONS_BY_CLUSTER.values()] == [2, 5, 7, 7]


def test_threat_questions_partition_into_the_clusters():
    questions = [q for qs in enums_module.THREAT_QUESTIONS_BY_CLUSTER.values() for q in qs]
    assert len(questions) == len(set(questions)) == 21
    assert set(questions) == set(enums_module.ThreatQuestion)
