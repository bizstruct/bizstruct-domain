"""Generation contracts: what the LLM writes, per stage (schemas/generation.py)."""

import re
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

import schema_builders as b
from bizstruct_domain.schemas import (
    GENERATION_CONTRACTS,
    Brief,
    BusinessCase,
    BusinessCaseGenerated,
    Canvas,
    CanvasGenerated,
    CanvasGroupGenerated,
    CanvasSection,
    CustomerScenario,
    CustomerScenarioGenerated,
    EmpathyMap,
    EmpathyMapGenerated,
    Epicenter,
    EpicenterClassification,
    EnvironmentScan,
    EnvironmentScanGenerated,
    Errc,
    ErrcGenerated,
    ERRCActionType,
    FutureScenario,
    FutureScenarioGenerated,
    Ideation,
    IdeationGenerated,
    PairwiseSegmentScoreGenerated,
    Pattern,
    Patterns,
    PatternsGenerated,
    PatternTag,
    Pitch,
    PitchGenerated,
    SanitizedModel,
    SegmentPairGenerated,
    SegmentRelationType,
    Stage,
    Storytelling,
    StorytellingGenerated,
    Swot,
    SwotCluster,
    SwotGenerated,
    patterns_from_generated,
)
from bizstruct_domain.schemas.canvas import CanvasSections
from bizstruct_domain.schemas.future_scenario import AdaptationQuestion, FutureScenarioVariant
from bizstruct_domain.schemas.enums import (
    CanvasBranch,
    FreePatternSubtype,
    StorytellingFormat,
    StorytellingGoal,
    StorytellingPerspective,
)
from bizstruct_domain.schemas.optional_inputs import SalesScenario
from bizstruct_domain.schemas.storytelling import CanvasReference

# contract -> (persisted model, its system fields)
CONTRACTS: dict[type[BaseModel], tuple[type[BaseModel], set[str]]] = {
    Brief: (Brief, set()),
    EmpathyMapGenerated: (EmpathyMap, {"id", "project_id"}),
    CustomerScenarioGenerated: (CustomerScenario, {"id", "empathy_map_id"}),
    IdeationGenerated: (Ideation, {"id", "empathy_map_id"}),
    SwotGenerated: (Swot, {"id", "canvas_id", "canvas_version", "environment_scan_id"}),
    ErrcGenerated: (Errc, {"id", "canvas_id", "swot_id", "from_version", "to_version", "result_canvas_id"}),
    StorytellingGenerated: (Storytelling, {"id", "canvas_id"}),
    FutureScenarioGenerated: (FutureScenario, {"id", "canvas_id"}),
    PitchGenerated: (
        Pitch,
        {"id", "project_id", "storytelling_id", "canvas_id", "swot_id", "team_info_id", "business_case_id"},
    ),
    # `sources` comes from the retrieval step, never from the LLM.
    BusinessCaseGenerated: (BusinessCase, {"id", "project_id", "sources"}),
    EnvironmentScanGenerated: (EnvironmentScan, {"id", "project_id", "sources"}),
    # Different structure (no inheritance); the system side is documented here.
    CanvasGenerated: (
        Canvas,
        {"id", "group_id", "empathy_map_ids", "version", "previous_version_id", "is_generated"},
    ),
    # `branch_decision` is derived; group ids and real segment ids are system-side
    # (aliases replace them inside the nested models).
    PatternsGenerated: (Patterns, {"id", "project_id", "branch_decision"}),
}
INHERITING = [g for g in CONTRACTS if g not in (Brief, CanvasGenerated, PatternsGenerated)]

SYSTEM_NAME = re.compile(r"(^id$|_id$|_ids$|version)")
# property names allowed in a generation schema although they match SYSTEM_NAME
ALLOWED_SYSTEM_LIKE: set[str] = set()


def _property_names(schema: Any) -> set[str]:
    """Every property name in a JSON Schema, including $defs."""
    names: set[str] = set()
    if isinstance(schema, dict):
        for key, value in schema.items():
            if key == "properties" and isinstance(value, dict):
                names |= set(value)
            names |= _property_names(value)
    elif isinstance(schema, list):
        for item in schema:
            names |= _property_names(item)
    return names


# --------------------------------------------------------------------------- registry


class TestRegistry:
    def test_every_stage_but_team_info_has_a_contract(self):
        assert set(GENERATION_CONTRACTS) == set(Stage) - {Stage.TEAM_INFO}

    def test_swot_errc_cycle_has_two_the_others_one(self):
        for stage, models in GENERATION_CONTRACTS.items():
            assert len(models) == (2 if stage is Stage.SWOT_ERRC_CYCLE else 1), stage
        assert GENERATION_CONTRACTS[Stage.SWOT_ERRC_CYCLE] == (SwotGenerated, ErrcGenerated)

    def test_registry_matches_the_contract_table(self):
        registered = {m for models in GENERATION_CONTRACTS.values() for m in models}
        assert registered == set(CONTRACTS)

    def test_brief_and_canvas_contracts(self):
        assert GENERATION_CONTRACTS[Stage.BRIEF] == (Brief,)
        assert GENERATION_CONTRACTS[Stage.CANVAS] == (CanvasGenerated,)

    @pytest.mark.parametrize("contract", CONTRACTS, ids=lambda c: c.__name__)
    def test_json_schema_builds(self, contract):
        assert contract.model_json_schema()["properties"]


# --------------------------------------------------------------------------- guards


@pytest.mark.parametrize("contract", CONTRACTS, ids=lambda c: c.__name__)
class TestGuards:
    def test_generation_and_system_fields_are_disjoint_and_cover_the_persisted_fields(self, contract):
        persisted, system = CONTRACTS[contract]
        generated_fields = set(contract.model_fields)
        persisted_fields = set(persisted.model_fields)
        if contract is Brief:
            assert generated_fields == persisted_fields and not system
            return
        assert system <= persisted_fields, "a system field that the persisted model does not have"
        content_in_persisted = persisted_fields - system
        # Patterns and Canvas keep the same field names with different element
        # types (aliases / text-only drafts), so this holds for them as well.
        assert generated_fields == content_in_persisted
        assert not generated_fields & system, "a system field leaks into the generation contract"

    def test_no_system_like_property_in_the_json_schema(self, contract):
        if contract is Brief:
            pytest.skip("Brief is its own contract and has no system fields")
        names = _property_names(contract.model_json_schema())
        leaked = {n for n in names if SYSTEM_NAME.search(n)} - ALLOWED_SYSTEM_LIKE
        assert not leaked, f"{contract.__name__} exposes system-like properties: {sorted(leaked)}"

    def test_no_source_or_retrieval_property_in_the_json_schema(self, contract):
        names = _property_names(contract.model_json_schema())
        assert not names & {"sources", "retrieved_at"}

    def test_inherits_sanitized_model(self, contract):
        assert issubclass(contract, SanitizedModel)


@pytest.mark.parametrize("contract", INHERITING, ids=lambda c: c.__name__)
def test_persisted_model_extends_its_generation_model(contract):
    persisted, _ = CONTRACTS[contract]
    assert issubclass(persisted, contract)
    assert hasattr(persisted, "from_generated")


def test_new_models_are_covered_by_the_generic_examples_guard():
    from test_schemas_guards import MODELS

    for contract in CONTRACTS:
        assert contract in MODELS
    for nested in (SegmentPairGenerated, PairwiseSegmentScoreGenerated, CanvasGroupGenerated):
        assert nested in MODELS


# --------------------------------------------------------------------------- content validators on the generation models


class TestSwotGenerated:
    def test_accepted(self):
        SwotGenerated(clusters=[b.cluster(k) for k in SwotCluster])

    def test_duplicate_cluster_type_rejected(self):
        clusters = [b.cluster(k) for k in SwotCluster]
        clusters[3] = b.cluster(SwotCluster.VALUE_PROPOSITION)
        with pytest.raises(ValidationError, match="All four SWOT clusters"):
            SwotGenerated(clusters=clusters)

    def test_wrong_cluster_count_rejected(self):
        with pytest.raises(ValidationError):
            SwotGenerated(clusters=[b.cluster(k) for k in list(SwotCluster)[:3]])

    def test_weighted_score_is_available_on_the_generation_model(self):
        generated = SwotGenerated(clusters=[b.cluster(k) for k in SwotCluster])
        assert generated.weighted_weakness_threat_score == 21


class TestPatternsGenerated:
    @staticmethod
    def _pair(a: str = "S1", c: str = "S2", synergy: int = 3, conflict: int = -1):
        return PairwiseSegmentScoreGenerated(
            segment_pair=SegmentPairGenerated(segment_alias_a=a, segment_alias_b=c),
            synergy=synergy,
            conflict=conflict,
        )

    @staticmethod
    def _group(aliases: list[str], relation=SegmentRelationType.SEGMENTED) -> CanvasGroupGenerated:
        return CanvasGroupGenerated(segment_aliases=aliases, relation_type=relation)

    @classmethod
    def _make(cls, groups=None, tags=None, scores=None) -> PatternsGenerated:
        return PatternsGenerated(
            pairwise_scores=scores if scores is not None else [cls._pair()],
            groups=groups if groups is not None else [cls._group(["S1", "S2"])],
            pattern_tags=tags if tags is not None else [],
        )

    def test_accepted(self):
        self._make()

    def test_pair_aliases_must_differ(self):
        with pytest.raises(ValidationError, match="must be different"):
            self._pair("S1", "S1")

    @pytest.mark.parametrize("synergy", [-1, 6])
    def test_synergy_bounds(self, synergy):
        with pytest.raises(ValidationError):
            self._pair(synergy=synergy)

    @pytest.mark.parametrize("conflict", [-8, 1])
    def test_conflict_bounds(self, conflict):
        with pytest.raises(ValidationError):
            self._pair(conflict=conflict)

    def test_net_score(self):
        assert self._pair(synergy=4, conflict=-7).net_score == -3

    def test_requires_at_least_one_group(self):
        with pytest.raises(ValidationError):
            self._make(groups=[])

    def test_group_needs_a_segment(self):
        with pytest.raises(ValidationError):
            self._group([])

    msp = [b.tag(Pattern.MULTI_SIDED_PLATFORM)]

    def test_multi_sided_platform_accepted_with_a_multi_sided_group_of_two(self):
        self._make(groups=[self._group(["S1", "S2"], SegmentRelationType.MULTI_SIDED)], tags=self.msp)

    def test_multi_sided_platform_rejected_for_a_multi_sided_group_of_one(self):
        with pytest.raises(ValidationError, match="multi-sided"):
            self._make(groups=[self._group(["S1"], SegmentRelationType.MULTI_SIDED)], tags=self.msp)

    def test_multi_sided_platform_rejected_for_a_segmented_group_of_two(self):
        with pytest.raises(ValidationError, match="multi-sided"):
            self._make(groups=[self._group(["S1", "S2"])], tags=self.msp)

    def test_multi_sided_platform_rejected_when_the_halves_are_in_different_groups(self):
        groups = [self._group(["S1"], SegmentRelationType.MULTI_SIDED), self._group(["S2", "S3"])]
        with pytest.raises(ValidationError, match="multi-sided"):
            self._make(groups=groups, tags=self.msp)

    def test_repeated_pattern_rejected(self):
        with pytest.raises(ValidationError, match="only once"):
            self._make(tags=[b.tag(Pattern.UNBUNDLING), b.tag(Pattern.UNBUNDLING)])

    def test_pattern_tag_subtype_rule_is_reused(self):
        self._make(tags=[b.tag(Pattern.FREE, FreePatternSubtype.FREEMIUM)])
        with pytest.raises(ValidationError, match="FreePatternSubtype"):
            self._make(tags=[b.tag(Pattern.FREE)])
        with pytest.raises(ValidationError, match="must be None"):
            self._make(tags=[b.tag(Pattern.UNBUNDLING, FreePatternSubtype.FREEMIUM)])
        assert PatternsGenerated.model_fields["pattern_tags"].annotation == list[PatternTag]

    def test_at_most_five_tags(self):
        with pytest.raises(ValidationError):
            self._make(tags=[b.tag(Pattern.UNBUNDLING)] * 6)

    def test_schema_exposes_aliases_and_no_ids(self):
        names = _property_names(PatternsGenerated.model_json_schema())
        assert {"segment_alias_a", "segment_alias_b", "segment_aliases"} <= names
        assert "branch_decision" not in names and "empathy_map_ids" not in names


# --------------------------------------------------------------------------- conversion


def _generated_instances() -> dict[type[BaseModel], tuple[BaseModel, dict[str, Any]]]:
    """contract -> (realistic generated instance, realistic system fields)."""
    sections = {name: [{"text": f"{name} {i}"} for i in range(2)] for name in b.SECTION_NAMES}
    return {
        EmpathyMapGenerated: (
            EmpathyMapGenerated(
                persona_name="P", persona_demographics="D", sees=["s"], hears=["h"],
                thinks_and_feels=["t"], says_and_does=["d"], pains=["p"], gains=["g"],
            ),
            {"id": "em_1", "project_id": "pr_1"},
        ),
        CustomerScenarioGenerated: (
            CustomerScenarioGenerated(situation_narrative="n", open_questions=["q?"]),
            {"id": "cs_1", "empathy_map_id": "em_1"},
        ),
        IdeationGenerated: (
            IdeationGenerated(
                epicenter=EpicenterClassification(tags=[Epicenter.FINANCE_DRIVEN], rationale="r"),
                what_if_questions=["What if?"],
            ),
            {"id": "id_1", "empathy_map_id": "em_1"},
        ),
        SwotGenerated: (
            SwotGenerated(clusters=[b.cluster(k) for k in SwotCluster]),
            {"id": "sw_1", "canvas_id": "cv_1", "canvas_version": 2, "environment_scan_id": None},
        ),
        ErrcGenerated: (
            ErrcGenerated(moves=[b.move(ERRCActionType.CREATE, new_text="new card")]),
            {"id": "er_1", "canvas_id": "cv_1", "swot_id": "sw_1", "from_version": 1, "to_version": 2,
             "result_canvas_id": "cv_2"},
        ),
        StorytellingGenerated: (
            StorytellingGenerated(
                perspective=StorytellingPerspective.COMPANY, goal=StorytellingGoal.PITCHING_INVESTORS,
                format=StorytellingFormat.VIDEO_CLIP, narrative_text="t",
                canvas_references=[CanvasReference(section=CanvasSection.CHANNELS, note="n")],
            ),
            {"id": "st_1", "canvas_id": "cv_1"},
        ),
        FutureScenarioGenerated: (
            FutureScenarioGenerated(
                uncertainty_drivers=["a", "b"],
                variants=[
                    FutureScenarioVariant(
                        name=f"v{i}", narrative="n",
                        adaptation_questions=[AdaptationQuestion(section=CanvasSection.CHANNELS, question="q")],
                    )
                    for i in range(2)
                ],
            ),
            {"id": "fs_1", "canvas_id": "cv_1"},
        ),
        PitchGenerated: (
            PitchGenerated(
                hook="h", business_model_summary="s", competitive_advantages=["a"], risk_analysis=["r"],
                team_section="team", financial_analysis_section="fin",
            ),
            {"id": "pi_1", "project_id": "pr_1", "storytelling_id": "st_1", "canvas_id": "cv_1",
             "swot_id": "sw_1", "team_info_id": "ti_1", "business_case_id": "bc_1"},
        ),
        BusinessCaseGenerated: (
            BusinessCaseGenerated(
                market_benchmarks="m", breakeven_formula="f",
                sales_scenarios=[SalesScenario(name="n", description="d")],
                capital_and_operating_costs="c", funding_requirements="f", profit_potential_notes="p",
            ),
            {"id": "bc_1", "project_id": "pr_1", "sources": [b.source()]},
        ),
        EnvironmentScanGenerated: (
            EnvironmentScanGenerated(
                market_forces=["m"], industry_forces=["i"], key_trends=["t"], macroeconomic_forces=["e"],
            ),
            {"id": "es_1", "project_id": "pr_1", "sources": [b.source()]},
        ),
    }


GENERATED = _generated_instances()


@pytest.mark.parametrize("contract", GENERATED, ids=lambda c: c.__name__)
class TestRoundTrip:
    def test_generated_to_persisted_keeps_content_and_adds_system_fields(self, contract):
        generated, system = GENERATED[contract]
        persisted_cls, system_names = CONTRACTS[contract]
        persisted = persisted_cls.from_generated(generated, **system)
        assert isinstance(persisted, persisted_cls)
        assert set(system) == system_names
        for name in type(generated).model_fields:
            assert getattr(persisted, name) == getattr(generated, name), name
        for name, value in system.items():
            assert getattr(persisted, name) == value, name

    def test_persisted_content_dumps_back_to_the_generated_instance(self, contract):
        generated, system = GENERATED[contract]
        persisted = CONTRACTS[contract][0].from_generated(generated, **system)
        again = contract.model_validate(persisted.model_dump(include=set(type(generated).model_fields)))
        assert again == generated

    def test_missing_system_field_is_a_validation_error(self, contract):
        generated, system = GENERATED[contract]
        incomplete = {k: v for k, v in system.items() if k != "id"}
        with pytest.raises(ValidationError):
            CONTRACTS[contract][0].from_generated(generated, **incomplete)


class TestConversionRunsPersistedValidators:
    def test_errc_versions_must_increment(self):
        generated, system = GENERATED[ErrcGenerated]
        with pytest.raises(ValidationError, match="exactly one greater"):
            Errc.from_generated(generated, **{**system, "from_version": 1, "to_version": 3})

    def test_pitch_section_without_its_input_id_is_rejected(self):
        generated, system = GENERATED[PitchGenerated]
        with pytest.raises(ValidationError, match="team_info_id and team_section"):
            Pitch.from_generated(generated, **{**system, "team_info_id": None})
        with pytest.raises(ValidationError, match="business_case_id and financial"):
            Pitch.from_generated(generated, **{**system, "business_case_id": None})

    def test_pitch_without_sections_and_without_ids_is_accepted(self):
        generated, system = GENERATED[PitchGenerated]
        bare = generated.model_copy(update={"team_section": None, "financial_analysis_section": None})
        pitch = Pitch.from_generated(bare, **{**system, "team_info_id": None, "business_case_id": None})
        assert pitch.team_section is None and pitch.team_info_id is None

    def test_business_case_needs_sources(self):
        generated, system = GENERATED[BusinessCaseGenerated]
        with pytest.raises(ValidationError):
            BusinessCase.from_generated(generated, **{**system, "sources": []})

    def test_environment_scan_needs_sources(self):
        generated, system = GENERATED[EnvironmentScanGenerated]
        with pytest.raises(ValidationError):
            EnvironmentScan.from_generated(generated, **{**system, "sources": []})

    def test_swot_canvas_version_range_is_enforced(self):
        generated, system = GENERATED[SwotGenerated]
        with pytest.raises(ValidationError):
            Swot.from_generated(generated, **{**system, "canvas_version": 6})

    def test_text_is_sanitized_on_conversion(self):
        generated, system = GENERATED[CustomerScenarioGenerated]
        dirty = generated.model_copy(update={"situation_narrative": "a\x00b"})
        assert CustomerScenario.from_generated(dirty, **system).situation_narrative == "ab"


class TestCanvasFromGenerated:
    @staticmethod
    def _generated(n: int = 3) -> CanvasGenerated:
        return CanvasGenerated.model_validate(
            {"sections": {name: [{"text": f"{name} {i}"} for i in range(n)] for name in b.SECTION_NAMES}}
        )

    @staticmethod
    def _counter():
        state = {"n": 0}

        def new_card_id() -> str:
            state["n"] += 1
            return f"card_{state['n']}"

        return new_card_id, state

    def test_builds_a_canvas_with_card_ids_assigned_by_the_caller(self):
        new_card_id, state = self._counter()
        canvas = Canvas.from_generated(
            self._generated(3), id="cv_1", group_id="g_1", empathy_map_ids=["em_1"], new_card_id=new_card_id
        )
        assert state["n"] == 27
        assert (canvas.id, canvas.group_id, canvas.empathy_map_ids) == ("cv_1", "g_1", ["em_1"])
        assert (canvas.version, canvas.previous_version_id) == (1, None)
        assert canvas.is_generated is True
        ids = [c.id for s in CanvasSection for c in canvas.get_section(s)]
        assert len(ids) == len(set(ids)) == 27
        assert all(c.errc_marker is None for s in CanvasSection for c in canvas.get_section(s))

    def test_ids_are_assigned_in_section_order_and_texts_preserved(self):
        new_card_id, _ = self._counter()
        generated = self._generated(2)
        canvas = Canvas.from_generated(
            generated, id="cv_1", group_id="g_1", empathy_map_ids=["em_1"], new_card_id=new_card_id
        )
        assert [c.id for c in canvas.sections.value_propositions] == ["card_1", "card_2"]
        assert [c.id for c in canvas.sections.customer_segments] == ["card_3", "card_4"]
        for name in CanvasSections.model_fields:
            assert [c.text for c in getattr(canvas.sections, name)] == [
                d.text for d in getattr(generated.sections, name)
            ]

    def test_version_and_previous_version_are_passed_through(self):
        new_card_id, _ = self._counter()
        canvas = Canvas.from_generated(
            self._generated(), id="cv_2", group_id="g_1", empathy_map_ids=["em_1"],
            version=2, previous_version_id="cv_1", new_card_id=new_card_id,
        )
        assert (canvas.version, canvas.previous_version_id) == (2, "cv_1")

    def test_persisted_validation_still_applies(self):
        new_card_id, _ = self._counter()
        with pytest.raises(ValidationError):
            Canvas.from_generated(
                self._generated(), id="cv_1", group_id="g_1", empathy_map_ids=["em_1"],
                version=6, new_card_id=new_card_id,
            )
        with pytest.raises(ValidationError):
            Canvas.from_generated(
                self._generated(), id="cv_1", group_id="g_1", empathy_map_ids=[], new_card_id=new_card_id
            )


class TestPatternsFromGenerated:
    SEGMENTS = {"S1": "em_1", "S2": "em_2", "S3": "em_3"}

    @staticmethod
    def _generated(groups=None, tags=None) -> PatternsGenerated:
        return TestPatternsGenerated._make(groups=groups, tags=tags, scores=[
            TestPatternsGenerated._pair("S1", "S2", 4, -2),
            TestPatternsGenerated._pair("S1", "S3", 1, -5),
        ])

    def test_maps_aliases_to_real_ids_and_assigns_group_ids(self):
        generated = self._generated(
            groups=[
                CanvasGroupGenerated(segment_aliases=["S1", "S2"], relation_type=SegmentRelationType.MULTI_SIDED),
                CanvasGroupGenerated(segment_aliases=["S3"], relation_type=SegmentRelationType.SEGMENTED),
            ],
            tags=[b.tag(Pattern.MULTI_SIDED_PLATFORM)],
        )
        patterns = patterns_from_generated(
            generated, id="pa_1", project_id="pr_1", segment_ids=self.SEGMENTS, group_ids=["g_1", "g_2"]
        )
        assert isinstance(patterns, Patterns)
        assert (patterns.id, patterns.project_id) == ("pa_1", "pr_1")
        assert [(g.id, g.empathy_map_ids, g.relation_type) for g in patterns.groups] == [
            ("g_1", ["em_1", "em_2"], SegmentRelationType.MULTI_SIDED),
            ("g_2", ["em_3"], SegmentRelationType.SEGMENTED),
        ]
        pairs = [(s.segment_pair.empathy_map_id_a, s.segment_pair.empathy_map_id_b, s.net_score)
                 for s in patterns.pairwise_scores]
        assert pairs == [("em_1", "em_2", 2), ("em_1", "em_3", -4)]
        assert [t.pattern for t in patterns.pattern_tags] == [Pattern.MULTI_SIDED_PLATFORM]

    def test_branch_decision_is_derived(self):
        one = patterns_from_generated(
            self._generated(), id="pa", project_id="pr", segment_ids=self.SEGMENTS, group_ids=["g_1"]
        )
        assert one.branch_decision is CanvasBranch.UNIFIED_MODEL
        two = patterns_from_generated(
            self._generated(groups=[
                CanvasGroupGenerated(segment_aliases=["S1"], relation_type=SegmentRelationType.SEGMENTED),
                CanvasGroupGenerated(segment_aliases=["S2", "S3"], relation_type=SegmentRelationType.SEGMENTED),
            ]),
            id="pa", project_id="pr", segment_ids=self.SEGMENTS, group_ids=["g_1", "g_2"],
        )
        assert two.branch_decision is CanvasBranch.SPLIT_MODEL

    def test_unknown_alias_is_a_value_error_naming_it(self):
        with pytest.raises(ValueError, match="Unknown segment alias 'S3'"):
            patterns_from_generated(
                self._generated(), id="pa", project_id="pr",
                segment_ids={"S1": "em_1", "S2": "em_2"}, group_ids=["g_1"],
            )

    @pytest.mark.parametrize("group_ids", [[], ["g_1", "g_2"]])
    def test_group_id_count_must_match_the_groups(self, group_ids):
        with pytest.raises(ValueError, match="group ids"):
            patterns_from_generated(
                self._generated(), id="pa", project_id="pr", segment_ids=self.SEGMENTS, group_ids=group_ids
            )

    def test_two_aliases_mapped_to_one_id_are_rejected_by_the_persisted_validator(self):
        with pytest.raises(ValidationError, match="must be different"):
            patterns_from_generated(
                self._generated(), id="pa", project_id="pr",
                segment_ids={"S1": "em_1", "S2": "em_1", "S3": "em_3"}, group_ids=["g_1"],
            )

    def test_result_passes_the_persisted_patterns_validators(self):
        patterns = patterns_from_generated(
            self._generated(), id="pa", project_id="pr", segment_ids=self.SEGMENTS, group_ids=["g_1"]
        )
        assert Patterns.model_validate(patterns.model_dump()) == patterns


class TestErrcGeneratedContract:
    """ErrcGenerated is the content-only view of Errc; the move matrix lives in ErrcMove."""

    def _move_schema(self) -> dict[str, Any]:
        return ErrcGenerated.model_json_schema()["$defs"]["ErrcMove"]

    def test_schema_is_moves_only_with_bounds(self):
        schema = ErrcGenerated.model_json_schema()
        assert set(schema["properties"]) == {"moves"}
        moves = schema["properties"]["moves"]
        assert (moves["minItems"], moves["maxItems"]) == (1, 6)
        assert moves["items"] == {"$ref": "#/$defs/ErrcMove"}

    def test_move_schema_keeps_both_text_fields_optional_and_documents_the_matrix(self):
        move = self._move_schema()
        # The per-action matrix is validator-only (not expressible in the schema), so the
        # descriptions are what the generator sees.
        assert set(move["required"]) == {"action", "target_section", "opposite_side_impact", "rationale"}
        target = move["properties"]["target_card_text"]["description"]
        new = move["properties"]["new_text"]["description"]
        assert "eliminate, reduce and raise" in target and "omitted for create" in target
        assert "reduce, raise and create" in new and "omitted for eliminate" in new

    def test_move_schema_examples_are_valid_moves(self):
        examples = ErrcGenerated.model_json_schema()["properties"]["moves"]["examples"][0]
        assert {m["action"] for m in examples} == {a.value for a in ERRCActionType}
        ErrcGenerated.model_validate({"moves": examples})

    @pytest.mark.parametrize(
        "bad",
        [
            {"action": "reduce", "target_card_text": "old"},
            {"action": "raise", "new_text": "new"},
            {"action": "eliminate", "target_card_text": "old", "new_text": "new"},
            {"action": "create", "target_card_text": "old", "new_text": "new"},
        ],
    )
    def test_generated_output_violating_the_matrix_is_rejected(self, bad):
        move = {"target_section": "channels", "opposite_side_impact": "i", "rationale": "r", **bad}
        with pytest.raises(ValidationError):
            ErrcGenerated.model_validate({"moves": [move]})
