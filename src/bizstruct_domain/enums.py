"""Shared enums for the BizStruct domain model.

All enums are `str, Enum` so they serialize as plain strings in JSON /
OpenAI structured output and compare equal to their string values.
"""

from enum import Enum


class Epicenter(str, Enum):
    """Epicentres of business model innovation.

    Osterwalder & Pigneur, "Business Model Generation" — Epicentres of
    Business Model Innovation. Exactly 5 canonical values; do not add
    invented values (e.g. a "competitor-driven" epicenter is not part
    of the methodology).
    """

    RESOURCE_DRIVEN = "resource_driven"
    OFFER_DRIVEN = "offer_driven"
    CUSTOMER_DRIVEN = "customer_driven"
    FINANCE_DRIVEN = "finance_driven"
    MULTIPLE_EPICENTER = "multiple_epicenter"


class Pattern(str, Enum):
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


class PatternSubtype(str, Enum):
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


class HypothesisCategory(str, Enum):
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


class WhatIfStatus(str, Enum):
    """Lifecycle status of a what-if (ERRC) alternative."""

    DRAFT = "draft"
    APPLIED = "applied"


class ERRCAction(str, Enum):
    """Blue Ocean Strategy ERRC grid actions.

    `raise` is a reserved Python keyword, so the member name is `RAISE_`
    while the serialized value stays the plain string "raise".
    """

    ELIMINATE = "eliminate"
    REDUCE = "reduce"
    RAISE_ = "raise"
    CREATE = "create"


class PitchAudience(str, Enum):
    """Target audience for a generated pitch."""

    INVESTOR = "investor"
    CUSTOMER = "customer"


class MonetizationType(str, Enum):
    """How a business model option makes money."""

    SUBSCRIPTION = "subscription"
    TRANSACTION_FEE = "transaction_fee"
    RETAINER_PLUS_SAAS = "retainer_plus_saas"
    ADVERTISING = "advertising"
    LICENSING = "licensing"
    MARKETPLACE_TAKE_RATE = "marketplace_take_rate"


class CanvasSection(str, Enum):
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
