import importlib.util
import sys
from datetime import date
from enum import StrEnum

import pytest
from pydantic import BaseModel, ValidationError, create_model

import bizstruct_domain.schemas.canvas as canvas_module
from bizstruct_domain.schemas.brief import MAX_SEGMENTS, Brief
from bizstruct_domain.schemas.canvas import (
    GENERATED_CARDS_PER_SECTION_MAX,
    GENERATED_CARDS_PER_SECTION_MIN,
    Canvas,
    CanvasCard,
    CanvasCardDraft,
    CanvasGenerated,
    CanvasSections,
)
from bizstruct_domain.schemas.enums import (
    THREAT_QUESTIONS_BY_CLUSTER,
    ThreatQuestion,
    CanvasBranch,
    CanvasSection,
    Epicenter,
    ERRCActionType,
    FreePatternSubtype,
    OpenBusinessModelPatternSubtype,
    Pattern,
    SegmentRelationType,
    StorytellingFormat,
    StorytellingGoal,
    StorytellingPerspective,
    SwotCluster,
)
from bizstruct_domain.schemas.errc import Errc
from bizstruct_domain.schemas.swot import SwotAxisStatement, SwotClusterResult
from bizstruct_domain.schemas.future_scenario import (
    AdaptationQuestion,
    FutureScenario,
    FutureScenarioVariant,
)
from bizstruct_domain.schemas.ideation import EpicenterClassification, Ideation
from bizstruct_domain.schemas.optional_inputs import (
    BusinessCase,
    EnvironmentScan,
    SalesScenario,
    Source,
    TeamInfo,
    TeamMember,
)
from bizstruct_domain.schemas.pattern import (
    PairwiseSegmentScore,
    SegmentPair,
)
from bizstruct_domain.schemas.storytelling import CanvasReference, Storytelling

import schema_builders as b

MULTI = SegmentRelationType.MULTI_SIDED
SEGMENTED = SegmentRelationType.SEGMENTED


# --------------------------------------------------------------------------- brief


class TestBriefSegmentCap:
    @staticmethod
    def _brief(n: int) -> Brief:
        return Brief(
            idea_summary="i",
            industry="x",
            customer_segment_candidates=[f"segment {i}" for i in range(n)],
            existing_resources=[],
            gaps=[],
        )

    def test_constant(self):
        assert MAX_SEGMENTS == 3

    @pytest.mark.parametrize("n", [1, 2, 3])
    def test_one_to_three_segments_accepted(self, n):
        assert len(self._brief(n).customer_segment_candidates) == n

    @pytest.mark.parametrize("n", [0, 4, 10])
    def test_zero_and_more_than_three_rejected(self, n):
        with pytest.raises(ValidationError):
            self._brief(n)

    def test_json_schema_carries_the_bounds(self):
        prop = Brief.model_json_schema()["properties"]["customer_segment_candidates"]
        assert (prop["minItems"], prop["maxItems"]) == (1, MAX_SEGMENTS)

    def test_the_field_example_respects_the_cap(self):
        for example in Brief.model_fields["customer_segment_candidates"].examples:
            assert 1 <= len(example) <= MAX_SEGMENTS


# --------------------------------------------------------------------------- patterns


class TestPatternsBranchDecision:
    def test_one_group_requires_unified(self):
        b.patterns(branch_decision=CanvasBranch.UNIFIED_MODEL)
        with pytest.raises(ValidationError, match="branch decision"):
            b.patterns(branch_decision=CanvasBranch.SPLIT_MODEL)

    def test_several_groups_require_split(self):
        groups = [b.group("g1", 1, SEGMENTED), b.group("g2", 1, SEGMENTED)]
        b.patterns(groups=groups, branch_decision=CanvasBranch.SPLIT_MODEL)
        with pytest.raises(ValidationError, match="branch decision"):
            b.patterns(groups=groups, branch_decision=CanvasBranch.UNIFIED_MODEL)

    def test_requires_at_least_one_group(self):
        with pytest.raises(ValidationError):
            b.patterns(groups=[])


class TestPatternsMultiSided:
    msp = [b.tag(Pattern.MULTI_SIDED_PLATFORM)]

    def test_accepted_with_multi_sided_group_of_two_maps(self):
        b.patterns(
            groups=[b.group("g1", 2, MULTI)],
            pattern_tags=self.msp,
        )

    def test_rejected_when_group_is_multi_sided_but_has_one_map(self):
        with pytest.raises(ValidationError, match="multi-sided"):
            b.patterns(groups=[b.group("g1", 1, MULTI)], pattern_tags=self.msp)

    def test_rejected_when_group_has_two_maps_but_is_not_multi_sided(self):
        with pytest.raises(ValidationError, match="multi-sided"):
            b.patterns(groups=[b.group("g1", 2, SEGMENTED)], pattern_tags=self.msp)

    def test_rejected_when_conditions_hold_only_in_different_groups(self):
        # One MULTI_SIDED group of size 1 + one SEGMENTED group of size 2:
        # each half of the condition holds, but never in the same group.
        with pytest.raises(ValidationError, match="multi-sided"):
            b.patterns(
                groups=[b.group("g1", 1, MULTI), b.group("g2", 2, SEGMENTED)],
                branch_decision=CanvasBranch.SPLIT_MODEL,
                pattern_tags=self.msp,
            )

    def test_accepted_when_one_of_several_groups_qualifies(self):
        b.patterns(
            groups=[b.group("g1", 1, SEGMENTED), b.group("g2", 3, MULTI)],
            branch_decision=CanvasBranch.SPLIT_MODEL,
            pattern_tags=self.msp,
        )

    def test_no_constraint_without_the_tag(self):
        b.patterns(groups=[b.group("g1", 1, MULTI)], pattern_tags=[])


class TestPatternsUniqueTags:
    def test_distinct_patterns_accepted(self):
        b.patterns(pattern_tags=[b.tag(Pattern.UNBUNDLING), b.tag(Pattern.LONG_TAIL)])

    def test_repeated_pattern_rejected(self):
        with pytest.raises(ValidationError, match="only once"):
            b.patterns(pattern_tags=[b.tag(Pattern.UNBUNDLING), b.tag(Pattern.UNBUNDLING)])

    def test_repeated_pattern_with_different_subtypes_still_rejected(self):
        tags = [
            b.tag(Pattern.FREE, FreePatternSubtype.FREEMIUM),
            b.tag(Pattern.FREE, FreePatternSubtype.AD_SUPPORTED),
        ]
        with pytest.raises(ValidationError, match="free"):
            b.patterns(pattern_tags=tags)


class TestPatternTagSubtype:
    @pytest.mark.parametrize("subtype", list(FreePatternSubtype))
    def test_free_accepts_free_subtypes(self, subtype):
        assert b.tag(Pattern.FREE, subtype).subtype == subtype

    @pytest.mark.parametrize("subtype", [None, *OpenBusinessModelPatternSubtype])
    def test_free_rejects_none_and_foreign_subtypes(self, subtype):
        with pytest.raises(ValidationError, match="FreePatternSubtype"):
            b.tag(Pattern.FREE, subtype)

    @pytest.mark.parametrize("subtype", list(OpenBusinessModelPatternSubtype))
    def test_open_business_model_accepts_its_subtypes(self, subtype):
        assert b.tag(Pattern.OPEN_BUSINESS_MODEL, subtype).subtype == subtype

    @pytest.mark.parametrize("subtype", [None, *FreePatternSubtype])
    def test_open_business_model_rejects_none_and_foreign_subtypes(self, subtype):
        with pytest.raises(ValidationError, match="OpenBusinessModelPatternSubtype"):
            b.tag(Pattern.OPEN_BUSINESS_MODEL, subtype)

    @pytest.mark.parametrize(
        "pattern", [Pattern.UNBUNDLING, Pattern.LONG_TAIL, Pattern.MULTI_SIDED_PLATFORM]
    )
    def test_other_patterns_take_no_subtype(self, pattern):
        assert b.tag(pattern).subtype is None
        for subtype in (FreePatternSubtype.FREEMIUM, OpenBusinessModelPatternSubtype.INSIDE_OUT):
            with pytest.raises(ValidationError, match="must be None"):
                b.tag(pattern, subtype)


class TestSegmentPairAndScore:
    def test_pair_ids_must_differ(self):
        SegmentPair(empathy_map_id_a="a", empathy_map_id_b="b")
        with pytest.raises(ValidationError, match="must be different"):
            SegmentPair(empathy_map_id_a="a", empathy_map_id_b="a")

    @staticmethod
    def _score(synergy: int, conflict: int) -> PairwiseSegmentScore:
        return PairwiseSegmentScore(
            segment_pair=SegmentPair(empathy_map_id_a="a", empathy_map_id_b="b"),
            synergy=synergy,
            conflict=conflict,
        )

    @pytest.mark.parametrize("synergy", [0, 5])
    def test_synergy_bounds_inclusive(self, synergy):
        assert self._score(synergy, 0).synergy == synergy

    @pytest.mark.parametrize("synergy", [-1, 6])
    def test_synergy_out_of_bounds(self, synergy):
        with pytest.raises(ValidationError):
            self._score(synergy, 0)

    @pytest.mark.parametrize("conflict", [-7, 0])
    def test_conflict_bounds_inclusive(self, conflict):
        assert self._score(0, conflict).conflict == conflict

    @pytest.mark.parametrize("conflict", [-8, 1])
    def test_conflict_out_of_bounds(self, conflict):
        with pytest.raises(ValidationError):
            self._score(0, conflict)

    @pytest.mark.parametrize(
        ("synergy", "conflict", "expected"),
        [(5, 0, 5), (3, -2, 1), (0, -7, -7), (4, -7, -3), (0, 0, 0)],
    )
    def test_net_score(self, synergy, conflict, expected):
        assert self._score(synergy, conflict).net_score == expected


# --------------------------------------------------------------------------- epicenter


class TestEpicenterClassification:
    F, O, R, C, M = (
        Epicenter.FINANCE_DRIVEN,
        Epicenter.OFFER_DRIVEN,
        Epicenter.RESOURCE_DRIVEN,
        Epicenter.CUSTOMER_DRIVEN,
        Epicenter.MULTIPLE_EPICENTER,
    )

    @staticmethod
    def _make(tags: list[Epicenter]) -> EpicenterClassification:
        return EpicenterClassification(tags=tags, rationale="r")

    @pytest.mark.parametrize("tag", [Epicenter.FINANCE_DRIVEN, Epicenter.OFFER_DRIVEN,
                                     Epicenter.RESOURCE_DRIVEN, Epicenter.CUSTOMER_DRIVEN])
    def test_single_concrete_tag_accepted(self, tag):
        assert self._make([tag]).tags == [tag]

    def test_two_concrete_tags_with_marker_accepted(self):
        self._make([self.F, self.O, self.M])

    def test_marker_position_does_not_matter(self):
        self._make([self.M, self.F, self.O])

    def test_all_four_concrete_tags_with_marker_accepted(self):
        self._make([self.R, self.O, self.C, self.F, self.M])

    def test_multiple_epicenter_alone_rejected(self):
        with pytest.raises(ValidationError, match="At least one concrete"):
            self._make([self.M])

    def test_one_concrete_tag_with_marker_rejected(self):
        with pytest.raises(ValidationError, match="at least two concrete"):
            self._make([self.F, self.M])

    def test_two_concrete_tags_without_marker_rejected(self):
        with pytest.raises(ValidationError, match="MULTIPLE_EPICENTER"):
            self._make([self.F, self.O])

    def test_all_four_concrete_tags_without_marker_rejected(self):
        with pytest.raises(ValidationError, match="MULTIPLE_EPICENTER"):
            self._make([self.R, self.O, self.C, self.F])

    @pytest.mark.parametrize(
        "tags",
        [
            [Epicenter.FINANCE_DRIVEN, Epicenter.FINANCE_DRIVEN],
            [Epicenter.FINANCE_DRIVEN, Epicenter.FINANCE_DRIVEN, Epicenter.MULTIPLE_EPICENTER],
            [Epicenter.FINANCE_DRIVEN, Epicenter.OFFER_DRIVEN, Epicenter.MULTIPLE_EPICENTER,
             Epicenter.MULTIPLE_EPICENTER],
        ],
    )
    def test_duplicate_tags_rejected(self, tags):
        with pytest.raises(ValidationError, match="duplicates"):
            self._make(tags)

    def test_five_concrete_values_together_rejected(self):
        # Only four concrete epicenters exist, so five tags always repeat one
        # (or are all four plus the marker, which is valid: see above).
        with pytest.raises(ValidationError):
            self._make([self.R, self.O, self.C, self.F, self.F, self.M])

    def test_five_values_together_with_marker_and_four_concrete_is_the_maximum(self):
        assert len(self._make([self.R, self.O, self.C, self.F, self.M]).tags) == 5

    def test_empty_tags_rejected(self):
        with pytest.raises(ValidationError):
            self._make([])


# --------------------------------------------------------------------------- swot


class TestSwot:
    def test_valid(self):
        b.swot()

    def test_axis_score_zero_rejected(self):
        with pytest.raises(ValidationError):
            b.axis(0)

    @pytest.mark.parametrize("score", [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5])
    def test_axis_score_every_nonzero_value_accepted(self, score):
        assert b.axis(score).score == score

    @pytest.mark.parametrize("score", [-6, 6, -100, 100])
    def test_axis_score_out_of_range_rejected(self, score):
        with pytest.raises(ValidationError):
            b.axis(score)

    def test_axis_score_json_schema_is_an_enum_without_zero(self):
        prop = SwotAxisStatement.model_json_schema()["properties"]["score"]
        assert sorted(prop["enum"]) == [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5]
        assert 0 not in prop["enum"]
        assert prop["type"] == "integer"

    def test_axis_score_has_no_validator_left(self):
        assert "score_not_zero" not in SwotAxisStatement.__pydantic_decorators__.field_validators

    @pytest.mark.parametrize("score", [0, 6])
    def test_opportunity_and_threat_score_must_be_1_to_5(self, score):
        with pytest.raises(ValidationError):
            b.opportunity(score)
        with pytest.raises(ValidationError):
            b.threat(ThreatQuestion.PARTNER_LOSS, score)

    def test_duplicate_cluster_type_rejected(self):
        clusters = [b.cluster(k) for k in SwotCluster]
        clusters[3] = b.cluster(SwotCluster.VALUE_PROPOSITION)  # CUSTOMER_INTERFACE lost
        with pytest.raises(ValidationError, match="All four SWOT clusters"):
            b.swot(clusters)

    def test_wrong_cluster_count_rejected(self):
        with pytest.raises(ValidationError):
            b.swot([b.cluster(k) for k in list(SwotCluster)[:3]])

    def test_weighted_weakness_threat_score_by_hand(self):
        # Weakness part: |score| * importance over the negative axis statements.
        # Threat part: the sum of the scores over the cluster's fixed catalog.
        # Positive statements and opportunities contribute nothing.
        clusters = [
            b.cluster(  # weakness 3*8 = 24; threats (2 questions) 2 + 3 = 5
                SwotCluster.VALUE_PROPOSITION,
                axes=[b.axis(-3, 8), b.axis(4, 9)],
                threats=b.catalog(SwotCluster.VALUE_PROPOSITION, [2, 3]),
                opportunities=[b.opportunity(5)],
            ),
            b.cluster(  # weakness 1*10 = 10; threats (5 questions) 1+1+1+1+1 = 5
                SwotCluster.COST_REVENUE,
                axes=[b.axis(-1, 10), b.axis(1, 3)],
                threats=b.catalog(SwotCluster.COST_REVENUE, 1),
            ),
            b.cluster(  # weakness 0; threats (7 questions) 5+4+3+2+1+1+1 = 17
                SwotCluster.INFRASTRUCTURE,
                axes=[b.axis(2, 7), b.axis(1, 7)],
                threats=b.catalog(SwotCluster.INFRASTRUCTURE, [5, 4, 3, 2, 1, 1, 1]),
            ),
            b.cluster(  # weakness 5*2 + 2*4 = 18; threats (7 questions) 7 * 1 = 7
                SwotCluster.CUSTOMER_INTERFACE,
                axes=[b.axis(-5, 2), b.axis(-2, 4)],
                threats=b.catalog(SwotCluster.CUSTOMER_INTERFACE, 1),
            ),
        ]
        weakness_part = 24 + 10 + 0 + 18
        threat_part = 5 + 5 + 17 + 7
        assert (weakness_part, threat_part) == (52, 34)
        assert b.swot(clusters).weighted_weakness_threat_score == 86

    def test_without_weaknesses_the_score_is_the_threat_sum_over_the_catalog(self):
        s = b.swot([b.cluster(k, axes=[b.axis(3), b.axis(4)], threats=b.catalog(k, 1)) for k in SwotCluster])
        assert s.weighted_weakness_threat_score == 21

    def test_threat_part_ranges_from_21_to_105(self):
        low = b.swot([b.cluster(k, threats=b.catalog(k, 1)) for k in SwotCluster])
        high = b.swot([b.cluster(k, threats=b.catalog(k, 5)) for k in SwotCluster])
        # default axis statements are positive (+1, +2): no weakness part
        assert low.weighted_weakness_threat_score == 21
        assert high.weighted_weakness_threat_score == 105

    def test_threat_part_is_independent_of_how_many_threats_the_model_lists(self):
        # The catalog fixes the number of rated questions, so the threat part
        # cannot drift with list length (the weakness part still can).
        for kind in SwotCluster:
            assert len(b.cluster(kind).threats) == len(THREAT_QUESTIONS_BY_CLUSTER[kind])


class TestThreatCatalog:
    @pytest.mark.parametrize("kind", list(SwotCluster))
    def test_exact_catalog_accepted(self, kind):
        assert len(b.cluster(kind, threats=b.catalog(kind, 3)).threats) == len(THREAT_QUESTIONS_BY_CLUSTER[kind])

    @pytest.mark.parametrize("kind", list(SwotCluster))
    def test_order_is_free(self, kind):
        b.cluster(kind, threats=list(reversed(b.catalog(kind))))

    def test_catalog_sizes_are_2_5_7_7(self):
        sizes = [len(THREAT_QUESTIONS_BY_CLUSTER[k]) for k in SwotCluster]
        assert sizes == [2, 5, 7, 7]
        assert sum(sizes) == 21 == len(ThreatQuestion)

    @pytest.mark.parametrize("kind", [SwotCluster.COST_REVENUE, SwotCluster.INFRASTRUCTURE, SwotCluster.CUSTOMER_INTERFACE])
    def test_missing_question_rejected(self, kind):
        with pytest.raises(ValidationError, match="Missing"):
            b.cluster(kind, threats=b.catalog(kind)[:-1])

    @pytest.mark.parametrize("kind", [SwotCluster.COST_REVENUE, SwotCluster.INFRASTRUCTURE])
    def test_duplicate_question_rejected(self, kind):
        threats = b.catalog(kind)
        threats[-1] = threats[0]  # same length, one question twice and one missing
        with pytest.raises(ValidationError, match="only once"):
            b.cluster(kind, threats=threats)

    def test_extra_duplicate_beyond_the_catalog_rejected(self):
        kind = SwotCluster.VALUE_PROPOSITION
        with pytest.raises(ValidationError, match="only once"):
            b.cluster(kind, threats=[*b.catalog(kind), b.threat(THREAT_QUESTIONS_BY_CLUSTER[kind][0])])

    def test_question_from_another_cluster_rejected(self):
        kind = SwotCluster.VALUE_PROPOSITION
        threats = [b.threat(ThreatQuestion.SUBSTITUTES_AVAILABLE), b.threat(ThreatQuestion.PARTNER_LOSS)]
        with pytest.raises(ValidationError, match="Not in this cluster: partner_loss"):
            b.cluster(kind, threats=threats)

    def test_full_catalog_plus_a_foreign_question_rejected(self):
        # Nothing is missing and nothing repeats: only the foreign question is wrong.
        kind = SwotCluster.COST_REVENUE
        threats = [*b.catalog(kind), b.threat(ThreatQuestion.PARTNER_LOSS)]
        with pytest.raises(ValidationError, match="Not in this cluster: partner_loss"):
            b.cluster(kind, threats=threats)

    def test_catalog_of_another_cluster_rejected(self):
        with pytest.raises(ValidationError, match="exactly its catalog"):
            b.cluster(SwotCluster.INFRASTRUCTURE, threats=b.catalog(SwotCluster.CUSTOMER_INTERFACE))

    def test_swot_with_each_cluster_on_its_own_catalog(self):
        assert b.swot()  # builders give every cluster its own exact catalog

    def test_json_schema_has_the_21_value_enum_and_the_envelope(self):
        schema = SwotClusterResult.model_json_schema()
        defs = schema["$defs"]
        assert sorted(defs["ThreatQuestion"]["enum"]) == sorted(q.value for q in ThreatQuestion)
        assert len(defs["ThreatQuestion"]["enum"]) == 21
        assert defs["SwotThreat"]["properties"]["question"]["$ref"].endswith("/ThreatQuestion")
        threats = schema["properties"]["threats"]
        assert (threats["minItems"], threats["maxItems"]) == (2, 7)

    def test_catalog_partition_is_disjoint_and_complete(self):
        questions = [q for qs in THREAT_QUESTIONS_BY_CLUSTER.values() for q in qs]
        assert len(questions) == len(set(questions))
        assert set(questions) == set(ThreatQuestion)


# --------------------------------------------------------------------------- list bounds


def _ideation(n: int) -> Ideation:
    return Ideation(
        id="i",
        empathy_map_id="e",
        epicenter=EpicenterClassification(tags=[Epicenter.FINANCE_DRIVEN], rationale="r"),
        what_if_questions=[f"What if {i}?" for i in range(n)],
    )


def _errc_moves(n: int) -> Errc:
    return b.errc([b.move(ERRCActionType.CREATE, new_text=f"new {i}") for i in range(n)])


def _axis_cluster(n: int) -> SwotClusterResult:
    return b.cluster(SwotCluster.VALUE_PROPOSITION, axes=[b.axis(1) for _ in range(n)])


def _opportunity_cluster(n: int) -> SwotClusterResult:
    return b.cluster(SwotCluster.VALUE_PROPOSITION, opportunities=[b.opportunity(2) for _ in range(n)])


def _threat_cluster(n: int) -> SwotClusterResult:
    """n threats: 2 and 7 are exact catalogs (value_proposition / infrastructure);
    1 and 8 are outside the 2..7 envelope."""
    if n == 2:
        return b.cluster(SwotCluster.VALUE_PROPOSITION)
    infra = b.catalog(SwotCluster.INFRASTRUCTURE)
    if n == 7:
        return b.cluster(SwotCluster.INFRASTRUCTURE)
    if n == 8:
        return b.cluster(SwotCluster.INFRASTRUCTURE, threats=[*infra, infra[0]])
    return b.cluster(SwotCluster.INFRASTRUCTURE, threats=infra[:n])


# name -> (builder taking a count, min, max, model class, field name)
BOUNDED_LISTS = {
    "Ideation.what_if_questions": (_ideation, 1, 10, Ideation, "what_if_questions"),
    "FutureScenario.uncertainty_drivers": (
        lambda n: _future_scenario([f"d{i}" for i in range(n)], 2), 2, 4, FutureScenario, "uncertainty_drivers"
    ),
    "Errc.moves": (_errc_moves, 1, 6, Errc, "moves"),
    "SwotClusterResult.axis_statements": (_axis_cluster, 2, 5, SwotClusterResult, "axis_statements"),
    "SwotClusterResult.threats": (_threat_cluster, 2, 7, SwotClusterResult, "threats"),
    "SwotClusterResult.opportunities": (_opportunity_cluster, 1, 7, SwotClusterResult, "opportunities"),
}


@pytest.mark.parametrize("name", BOUNDED_LISTS)
class TestListBounds:
    def test_below_min_rejected(self, name):
        build, lo, _, _, _ = BOUNDED_LISTS[name]
        with pytest.raises(ValidationError):
            build(lo - 1)

    def test_at_min_accepted(self, name):
        build, lo, _, _, _ = BOUNDED_LISTS[name]
        build(lo)

    def test_at_max_accepted(self, name):
        build, _, hi, _, _ = BOUNDED_LISTS[name]
        build(hi)

    def test_above_max_rejected(self, name):
        build, _, hi, _, _ = BOUNDED_LISTS[name]
        with pytest.raises(ValidationError):
            build(hi + 1)

    def test_bounds_are_in_the_json_schema_the_generator_sees(self, name):
        _, lo, hi, model, field = BOUNDED_LISTS[name]
        prop = model.model_json_schema()["properties"][field]
        assert (prop["minItems"], prop["maxItems"]) == (lo, hi)


# --------------------------------------------------------------------------- errc

CREATE, ELIMINATE = ERRCActionType.CREATE, ERRCActionType.ELIMINATE
NON_CREATE = [a for a in ERRCActionType if a != CREATE]


class TestErrcVersions:
    @pytest.mark.parametrize(("from_v", "to_v"), [(1, 2), (2, 3), (4, 5)])
    def test_increment_by_one_accepted(self, from_v, to_v):
        e = b.errc(from_version=from_v, to_version=to_v)
        assert (e.from_version, e.to_version) == (from_v, to_v)

    @pytest.mark.parametrize("from_v", [2, 3, 4, 5])
    def test_same_version_rejected(self, from_v):
        with pytest.raises(ValidationError, match="exactly one greater"):
            b.errc(from_version=from_v, to_version=from_v)

    def test_skipping_a_version_rejected(self):
        with pytest.raises(ValidationError, match="exactly one greater"):
            b.errc(from_version=1, to_version=3)

    def test_going_backwards_rejected(self):
        with pytest.raises(ValidationError):
            b.errc(from_version=3, to_version=2)

    def test_to_version_below_two_rejected(self):
        with pytest.raises(ValidationError):
            b.errc(from_version=1, to_version=1)
        with pytest.raises(ValidationError):
            b.errc(from_version=0, to_version=1)

    def test_versions_capped_at_five(self):
        with pytest.raises(ValidationError):
            b.errc(from_version=5, to_version=6)


# action -> (target_card_text required, new_text required); the other must be absent.
ERRC_MATRIX = {
    ERRCActionType.ELIMINATE: (True, False),
    ERRCActionType.REDUCE: (True, True),
    ERRCActionType.RAISE: (True, True),
    ERRCActionType.CREATE: (False, True),
}


class TestErrcMove:
    def test_matrix_covers_every_action(self):
        assert set(ERRC_MATRIX) == set(ERRCActionType)

    @pytest.mark.parametrize("action", list(ERRCActionType))
    @pytest.mark.parametrize("has_target", [False, True])
    @pytest.mark.parametrize("has_new", [False, True])
    def test_every_field_combination(self, action, has_target, has_new):
        needs_target, needs_new = ERRC_MATRIX[action]
        kwargs = dict(
            target_card_text="old" if has_target else None,
            new_text="new" if has_new else None,
        )
        if (has_target, has_new) == (needs_target, needs_new):
            move = b.move(action, **kwargs)
            assert (move.target_card_text, move.new_text) == (kwargs["target_card_text"], kwargs["new_text"])
        else:
            with pytest.raises(ValidationError):
                b.move(action, **kwargs)

    @pytest.mark.parametrize("action", list(ERRCActionType))
    def test_each_violation_names_its_field(self, action):
        needs_target, needs_new = ERRC_MATRIX[action]
        valid = dict(
            target_card_text="old" if needs_target else None,
            new_text="new" if needs_new else None,
        )
        for field, needed in (("target_card_text", needs_target), ("new_text", needs_new)):
            broken = {**valid, field: None if needed else "x"}
            verb = "provided" if needed else "None"
            with pytest.raises(ValidationError, match=rf"{field} must be {verb} when action is {action.name}"):
                b.move(action, **broken)

    @pytest.mark.parametrize("action", [ERRCActionType.REDUCE, ERRCActionType.RAISE])
    def test_reduce_and_raise_carry_the_rewritten_text(self, action):
        move = b.move(action, target_card_text="Fast delivery", new_text="Same-day delivery")
        assert move.new_text == "Same-day delivery"

    @pytest.mark.parametrize("action", list(ERRCActionType))
    @pytest.mark.parametrize("field", ["target_card_text", "new_text"])
    def test_empty_string_is_rejected_whether_required_or_forbidden(self, action, field):
        needs_target, needs_new = ERRC_MATRIX[action]
        kwargs = {
            "target_card_text": "old" if needs_target else None,
            "new_text": "new" if needs_new else None,
        }
        kwargs[field] = ""
        with pytest.raises(ValidationError):
            b.move(action, **kwargs)

    def test_errc_requires_at_least_one_move(self):
        data = b.errc().model_dump() | {"moves": []}
        with pytest.raises(ValidationError):
            Errc(**data)


# --------------------------------------------------------------------------- canvas

LO, HI = GENERATED_CARDS_PER_SECTION_MIN, GENERATED_CARDS_PER_SECTION_MAX


def _generated(per_section: int = 2, **counts: int) -> dict:
    """CanvasGenerated payload; `counts` overrides the card count per section."""
    return {
        "sections": {
            name: [{"text": f"{name} {i}"} for i in range(counts.get(name, per_section))]
            for name in b.SECTION_NAMES
        }
    }


class TestCanvasVersion:
    @pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
    def test_valid_versions(self, version):
        assert b.canvas(version=version).version == version

    @pytest.mark.parametrize("version", [0, 6, -1])
    def test_invalid_versions(self, version):
        with pytest.raises(ValidationError):
            b.canvas(version=version)


class TestCanvasIsGenerated:
    def test_constants(self):
        assert (LO, HI) == (2, 4)

    @pytest.mark.parametrize("is_generated", [True, False])
    @pytest.mark.parametrize("n", [0, 1, 2, 4, 5, 7])
    def test_persisted_canvas_accepts_any_card_count_per_section(self, n, is_generated):
        # ERRC moves and manual edits legitimately leave the 2-4 range; the bound
        # lives in CanvasGenerated only. is_generated is informational.
        canvas = b.canvas(sections=b.sections(n), is_generated=is_generated)
        assert canvas.is_generated is is_generated
        assert all(len(canvas.get_section(s)) == n for s in CanvasSection)

    def test_one_section_may_differ_from_the_others(self):
        canvas = b.canvas(sections=b.sections(2, channels=b.cards("channels", 5), key_resources=[]))
        assert len(canvas.sections.channels) == 5
        assert canvas.sections.key_resources == []

    def test_is_generated_defaults_to_true(self):
        assert b.canvas().is_generated is True

    def test_canvas_has_no_card_count_validator(self):
        assert not hasattr(Canvas, "generated_card_count")

    def test_get_section(self):
        c = b.canvas()
        for section in CanvasSection:
            assert c.get_section(section) is getattr(c.sections, section.value)

    def test_requires_at_least_one_empathy_map(self):
        with pytest.raises(ValidationError):
            b.canvas(empathy_map_ids=[])


class TestCanvasGenerated:
    @pytest.fixture()
    def schema(self) -> dict:
        return CanvasGenerated.model_json_schema()

    @pytest.fixture()
    def sections_schema(self, schema: dict) -> dict:
        return schema["$defs"]["CanvasSectionsGenerated"]

    def test_schema_has_all_nine_sections(self, sections_schema):
        assert set(sections_schema["properties"]) == set(b.SECTION_NAMES)
        assert len(b.SECTION_NAMES) == 9

    def test_every_section_is_required(self, sections_schema):
        assert set(sections_schema["required"]) == set(b.SECTION_NAMES)

    @pytest.mark.parametrize("name", b.SECTION_NAMES)
    def test_every_section_bounded_in_the_schema(self, sections_schema, name):
        prop = sections_schema["properties"][name]
        assert prop["type"] == "array"
        assert prop["minItems"] == 2
        assert prop["maxItems"] == 4

    def test_top_level_requires_sections(self, schema):
        assert schema["required"] == ["sections"]

    def test_draft_schema_exposes_only_text(self, schema):
        draft = schema["$defs"]["CanvasCardDraft"]
        assert set(draft["properties"]) == {"text"}
        assert draft["required"] == ["text"]

    @pytest.mark.parametrize("n", [2, 3, 4])
    def test_2_to_4_cards_accepted(self, n):
        assert CanvasGenerated.model_validate(_generated(n))

    @pytest.mark.parametrize("n", [0, 1, 5])
    @pytest.mark.parametrize("name", b.SECTION_NAMES)
    def test_other_counts_rejected_in_any_section(self, name, n):
        with pytest.raises(ValidationError, match=name):
            CanvasGenerated.model_validate(_generated(2, **{name: n}))

    def test_missing_section_rejected(self):
        payload = _generated()
        del payload["sections"]["channels"]
        with pytest.raises(ValidationError, match="channels"):
            CanvasGenerated.model_validate(payload)

    def test_empty_card_text_rejected(self):
        with pytest.raises(ValidationError):
            CanvasCardDraft(text="")

    def test_round_trip_to_persisted_canvas(self):
        generated = CanvasGenerated.model_validate(_generated(3))
        persisted: dict[str, list[CanvasCard]] = {}
        n = 0
        for name in b.SECTION_NAMES:
            persisted[name] = []
            for draft in getattr(generated.sections, name):
                n += 1  # the backend assigns ids; the generator never does
                persisted[name].append(CanvasCard(id=f"card_{n}", text=draft.text))

        canvas = Canvas(
            id="canvas_001",
            group_id="canvas_group_001",
            empathy_map_ids=["empathy_map_001"],
            version=1,
            sections=CanvasSections(**persisted),
        )

        assert canvas.is_generated
        for name in b.SECTION_NAMES:
            assert [c.text for c in getattr(canvas.sections, name)] == [
                d.text for d in getattr(generated.sections, name)
            ]
            assert all(c.errc_marker is None for c in getattr(canvas.sections, name))
        assert len({c.id for s in b.SECTION_NAMES for c in getattr(canvas.sections, s)}) == 27


class TestSectionNameGuard:
    def test_passes_when_in_sync(self):
        canvas_module._assert_section_names_in_sync()

    def test_guard_runs_at_import_time(self):
        # Execute a drifted copy of canvas.py as a throwaway module (never
        # registered in sys.modules, so the real classes stay untouched).
        source = canvas_module.__loader__.get_source(canvas_module.__name__)
        drifted = source.replace("    channels: list[CanvasCardDraft]", "    channelz: list[CanvasCardDraft]")
        assert drifted != source
        name = f"{canvas_module.__package__}._canvas_drift"
        spec = importlib.util.spec_from_loader(name, loader=None)
        module = importlib.util.module_from_spec(spec)
        module.__package__ = canvas_module.__package__
        sys.modules[name] = module  # pydantic resolves classes through sys.modules
        try:
            with pytest.raises(RuntimeError, match="out of sync"):
                exec(compile(drifted, "<canvas drift>", "exec"), module.__dict__)
        finally:
            del sys.modules[name]

    def test_raises_when_enum_drifts(self, monkeypatch):
        fewer = StrEnum("CanvasSection", {s.name: s.value for s in list(CanvasSection)[:-1]})
        monkeypatch.setattr(canvas_module, "CanvasSection", fewer)
        with pytest.raises(RuntimeError, match="out of sync"):
            canvas_module._assert_section_names_in_sync()

    def test_raises_when_persisted_sections_drift(self, monkeypatch):
        drifted = create_model("CanvasSections", value_propositions=(list[CanvasCard], []))
        monkeypatch.setattr(canvas_module, "CanvasSections", drifted)
        with pytest.raises(RuntimeError, match="out of sync"):
            canvas_module._assert_section_names_in_sync()

    def test_raises_when_generated_sections_drift(self, monkeypatch):
        fields = {n: (list[CanvasCardDraft], ...) for n in b.SECTION_NAMES}
        fields["extra_section"] = (list[CanvasCardDraft], ...)
        drifted: type[BaseModel] = create_model("CanvasSectionsGenerated", **fields)
        monkeypatch.setattr(canvas_module, "CanvasSectionsGenerated", drifted)
        with pytest.raises(RuntimeError, match="extra_section"):
            canvas_module._assert_section_names_in_sync()


# --------------------------------------------------------------------------- pitch


class TestPitchOptionalSections:
    def test_neither_side_set(self):
        b.pitch()

    def test_both_sides_set(self):
        b.pitch(
            team_info_id="team_001",
            team_section="team",
            business_case_id="bc_001",
            financial_analysis_section="fin",
        )

    def test_team_id_without_section_rejected(self):
        with pytest.raises(ValidationError, match="team_info_id and team_section"):
            b.pitch(team_info_id="team_001")

    def test_team_section_without_id_rejected(self):
        with pytest.raises(ValidationError, match="team_info_id and team_section"):
            b.pitch(team_section="team")

    def test_business_case_id_without_section_rejected(self):
        with pytest.raises(ValidationError, match="business_case_id and financial"):
            b.pitch(business_case_id="bc_001")

    def test_financial_section_without_id_rejected(self):
        with pytest.raises(ValidationError, match="business_case_id and financial"):
            b.pitch(financial_analysis_section="fin")

    def test_sides_are_independent(self):
        b.pitch(team_info_id="team_001", team_section="team")
        b.pitch(business_case_id="bc_001", financial_analysis_section="fin")


# --------------------------------------------------------------------------- optional inputs


class TestOptionalInputs:
    @staticmethod
    def _business_case(**overrides) -> BusinessCase:
        data = dict(
            id="bc_001",
            project_id="project_001",
            market_benchmarks="m",
            sources=[b.source()],
            breakeven_formula="f",
            sales_scenarios=[SalesScenario(name="n", description="d")],
            capital_and_operating_costs="c",
            funding_requirements="f",
            profit_potential_notes="p",
        )
        data.update(overrides)
        return BusinessCase(**data)

    def test_business_case_valid(self):
        self._business_case()

    def test_business_case_requires_sources(self):
        with pytest.raises(ValidationError):
            self._business_case(sources=[])

    def test_business_case_requires_a_sales_scenario(self):
        with pytest.raises(ValidationError):
            self._business_case(sales_scenarios=[])

    def test_environment_scan_valid(self):
        b.environment_scan()

    def test_environment_scan_requires_sources(self):
        data = b.environment_scan().model_dump() | {"sources": []}
        with pytest.raises(ValidationError):
            EnvironmentScan(**data)

    @pytest.mark.parametrize(
        "field", ["market_forces", "industry_forces", "key_trends", "macroeconomic_forces"]
    )
    def test_environment_scan_forces_must_not_be_empty(self, field):
        data = b.environment_scan().model_dump() | {field: []}
        with pytest.raises(ValidationError):
            EnvironmentScan(**data)

    def test_source_requires_retrieved_at(self):
        with pytest.raises(ValidationError, match="retrieved_at"):
            Source(title="Report", note="n")

    def test_source_parses_an_iso_date_and_rejects_garbage(self):
        assert Source(title="R", retrieved_at="2026-09-30", note="n").retrieved_at == date(2026, 9, 30)
        with pytest.raises(ValidationError):
            Source(title="R", retrieved_at="yesterday", note="n")

    def test_source_date_is_a_date_in_the_json_schema(self):
        prop = Source.model_json_schema()["properties"]["retrieved_at"]
        assert prop["format"] == "date"
        assert "retrieved_at" in Source.model_json_schema()["required"]

    def test_team_info_requires_a_member(self):
        member = TeamMember(
            name="A", role="R", relevant_experience="E", key_competencies=["c"]
        )
        TeamInfo(id="t", project_id="p", members=[member])
        with pytest.raises(ValidationError):
            TeamInfo(id="t", project_id="p", members=[])


# --------------------------------------------------------------------------- future scenario


def _variant(name: str = "v") -> FutureScenarioVariant:
    return FutureScenarioVariant(
        name=name,
        narrative="n",
        adaptation_questions=[
            AdaptationQuestion(section=CanvasSection.CHANNELS, question="q")
        ],
    )


def _future_scenario(drivers: list[str], variants: int) -> FutureScenario:
    return FutureScenario(
        id="fs_001",
        canvas_id="canvas_001",
        uncertainty_drivers=drivers,
        variants=[_variant(f"v{i}") for i in range(variants)],
    )


class TestFutureScenario:
    @pytest.mark.parametrize("n", [2, 3])
    def test_drivers_at_least_two(self, n):
        assert _future_scenario([f"d{i}" for i in range(n)], 2)

    @pytest.mark.parametrize("n", [0, 1])
    def test_too_few_drivers_rejected(self, n):
        with pytest.raises(ValidationError):
            _future_scenario([f"d{i}" for i in range(n)], 2)

    @pytest.mark.parametrize("n", [2, 3, 4])
    def test_variants_2_to_4_accepted(self, n):
        assert len(_future_scenario(["a", "b"], n).variants) == n

    @pytest.mark.parametrize("n", [0, 1, 5])
    def test_other_variant_counts_rejected(self, n):
        with pytest.raises(ValidationError):
            _future_scenario(["a", "b"], n)

    def test_variant_needs_an_adaptation_question(self):
        with pytest.raises(ValidationError):
            FutureScenarioVariant(name="v", narrative="n", adaptation_questions=[])


# --------------------------------------------------------------------------- storytelling


class TestStorytelling:
    @staticmethod
    def _make(references: list[CanvasReference]) -> Storytelling:
        return Storytelling(
            id="st_001",
            canvas_id="canvas_001",
            perspective=StorytellingPerspective.COMPANY,
            goal=StorytellingGoal.PITCHING_INVESTORS,
            format=StorytellingFormat.VIDEO_CLIP,
            narrative_text="text",
            canvas_references=references,
        )

    def test_one_reference_accepted(self):
        self._make([CanvasReference(section=CanvasSection.CHANNELS, note="n")])

    def test_no_references_rejected(self):
        with pytest.raises(ValidationError):
            self._make([])
