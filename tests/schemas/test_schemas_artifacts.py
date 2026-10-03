import importlib.util
import sys
from enum import StrEnum

import pytest
from pydantic import BaseModel, ValidationError, create_model

import bizstruct_domain.schemas.canvas as canvas_module
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
from bizstruct_domain.schemas.future_scenario import (
    AdaptationQuestion,
    FutureScenario,
    FutureScenarioVariant,
)
from bizstruct_domain.schemas.ideation import EpicenterClassification
from bizstruct_domain.schemas.optional_inputs import (
    BusinessCase,
    EnvironmentScan,
    SalesScenario,
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
    @staticmethod
    def _make(tags: list[Epicenter]) -> EpicenterClassification:
        return EpicenterClassification(tags=tags, rationale="r")

    def test_single_tag_needs_no_marker(self):
        self._make([Epicenter.FINANCE_DRIVEN])

    def test_multiple_epicenter_alone_is_allowed(self):
        self._make([Epicenter.MULTIPLE_EPICENTER])

    def test_multiple_tags_without_marker_rejected(self):
        with pytest.raises(ValidationError, match="MULTIPLE_EPICENTER"):
            self._make([Epicenter.FINANCE_DRIVEN, Epicenter.OFFER_DRIVEN])

    def test_multiple_tags_with_marker_accepted(self):
        self._make(
            [Epicenter.FINANCE_DRIVEN, Epicenter.OFFER_DRIVEN, Epicenter.MULTIPLE_EPICENTER]
        )

    def test_empty_tags_rejected(self):
        with pytest.raises(ValidationError):
            self._make([])


# --------------------------------------------------------------------------- swot


class TestSwot:
    def test_valid(self):
        b.swot()

    def test_axis_score_zero_rejected(self):
        with pytest.raises(ValidationError, match="cannot be zero"):
            b.axis(0)

    @pytest.mark.parametrize("score", [-5, -1, 1, 5])
    def test_axis_score_nonzero_in_range_accepted(self, score):
        assert b.axis(score).score == score

    @pytest.mark.parametrize("score", [-6, 6])
    def test_axis_score_out_of_range_rejected(self, score):
        with pytest.raises(ValidationError):
            b.axis(score)

    @pytest.mark.parametrize("score", [0, 6])
    def test_opportunity_threat_score_must_be_1_to_5(self, score):
        with pytest.raises(ValidationError):
            b.threat(score)

    def test_duplicate_cluster_type_rejected(self):
        clusters = [b.cluster(k) for k in SwotCluster]
        clusters[3] = b.cluster(SwotCluster.VALUE_PROPOSITION)  # CUSTOMER_INTERFACE lost
        with pytest.raises(ValidationError, match="All four SWOT clusters"):
            b.swot(clusters)

    def test_wrong_cluster_count_rejected(self):
        with pytest.raises(ValidationError):
            b.swot([b.cluster(k) for k in list(SwotCluster)[:3]])

    def test_weighted_weakness_threat_score_by_hand(self):
        # Only negative axis statements count (|score| * importance); every
        # threat contributes its own 1-5 score; positives and opportunities
        # contribute nothing.
        clusters = [
            b.cluster(  # 3*8 + 0 (positive) + (2 + 3) = 29
                SwotCluster.VALUE_PROPOSITION,
                axes=[b.axis(-3, 8), b.axis(4, 9)],
                threats=[b.threat(2), b.threat(3)],
                opportunities=[b.opportunity(5)],
            ),
            b.cluster(  # 1*10 = 10
                SwotCluster.COST_REVENUE, axes=[b.axis(-1, 10)]
            ),
            b.cluster(  # 0 + 5 = 5
                SwotCluster.INFRASTRUCTURE, axes=[b.axis(2, 7)], threats=[b.threat(5)]
            ),
            b.cluster(  # 5*2 + (1 + 1) = 12
                SwotCluster.CUSTOMER_INTERFACE,
                axes=[b.axis(-5, 2)],
                threats=[b.threat(1), b.threat(1)],
            ),
        ]
        assert b.swot(clusters).weighted_weakness_threat_score == 29 + 10 + 5 + 12

    def test_weighted_score_is_zero_without_weaknesses_or_threats(self):
        s = b.swot([b.cluster(k, axes=[b.axis(3)]) for k in SwotCluster])
        assert s.weighted_weakness_threat_score == 0

    def test_threat_contributes_its_own_score_not_a_flat_count(self):
        low = b.swot([b.cluster(k, threats=[b.threat(1)]) for k in SwotCluster])
        high = b.swot([b.cluster(k, threats=[b.threat(5)]) for k in SwotCluster])
        assert low.weighted_weakness_threat_score == 4
        assert high.weighted_weakness_threat_score == 20


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


class TestErrcMove:
    def test_create_with_new_text_only(self):
        b.move(CREATE, new_text="x")

    def test_create_without_new_text_rejected(self):
        with pytest.raises(ValidationError, match="new_text must be provided"):
            b.move(CREATE)

    def test_create_with_target_card_text_rejected(self):
        with pytest.raises(ValidationError, match="target_card_text must be None"):
            b.move(CREATE, target_card_text="old", new_text="x")

    def test_create_with_only_target_card_text_rejected(self):
        with pytest.raises(ValidationError, match="new_text must be provided"):
            b.move(CREATE, target_card_text="old")

    @pytest.mark.parametrize("action", NON_CREATE)
    def test_other_actions_with_target_only(self, action):
        b.move(action, target_card_text="old")

    @pytest.mark.parametrize("action", NON_CREATE)
    def test_other_actions_without_target_rejected(self, action):
        with pytest.raises(ValidationError, match="target_card_text must be provided"):
            b.move(action)

    @pytest.mark.parametrize("action", NON_CREATE)
    def test_other_actions_with_new_text_rejected(self, action):
        with pytest.raises(ValidationError, match="new_text must be None"):
            b.move(action, target_card_text="old", new_text="x")

    @pytest.mark.parametrize("action", NON_CREATE)
    def test_other_actions_with_only_new_text_rejected(self, action):
        with pytest.raises(ValidationError, match="target_card_text must be provided"):
            b.move(action, new_text="x")

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

    @pytest.mark.parametrize("n", [LO, 3, HI])
    def test_generated_accepts_2_to_4_cards_everywhere(self, n):
        assert b.canvas(sections=b.sections(n), is_generated=True).is_generated

    @pytest.mark.parametrize("n", [0, 1, 5])
    def test_generated_rejects_other_counts(self, n):
        with pytest.raises(ValidationError, match="between 2 and 4"):
            b.canvas(sections=b.sections(n), is_generated=True)

    def test_generated_is_the_default(self):
        with pytest.raises(ValidationError, match="between 2 and 4"):
            b.canvas(sections=b.sections(1))

    @pytest.mark.parametrize("name", b.SECTION_NAMES)
    def test_one_bad_section_is_enough_and_is_named(self, name):
        sections = b.sections(2, **{name: b.cards(name, 5)})
        with pytest.raises(ValidationError, match=name):
            b.canvas(sections=sections)

    @pytest.mark.parametrize("n", [0, 1, 7])
    def test_not_generated_accepts_any_count(self, n):
        assert not b.canvas(sections=b.sections(n), is_generated=False).is_generated

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
