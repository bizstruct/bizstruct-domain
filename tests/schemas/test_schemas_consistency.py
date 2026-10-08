import inspect
import typing

import pytest

import schema_builders as b
from bizstruct_domain.schemas.artifact_types import ARTIFACT_HOLDERS, ArtifactType
from bizstruct_domain.schemas.canvas import Canvas, CanvasCard
from bizstruct_domain.schemas.consistency import (
    CONSISTENCY_RULES,
    JUDGE_CHECKS,
    ConsistencyRule,
    JudgeCheck,
    Arity,
    RuleInput,
)
from bizstruct_domain.schemas.enums import (
    CanvasBranch,
    CanvasSection,
    ERRCActionType,
    Pattern,
    SegmentRelationType,
    Stage,
    StorytellingFormat,
    StorytellingGoal,
    StorytellingPerspective,
)
from bizstruct_domain.schemas.future_scenario import (
    AdaptationQuestion,
    FutureScenario,
    FutureScenarioVariant,
)
from bizstruct_domain.schemas.storytelling import CanvasReference, Storytelling

RULES = {r.id: r for r in CONSISTENCY_RULES}
CHANNELS = CanvasSection.CHANNELS
MSP = [b.tag(Pattern.MULTI_SIDED_PLATFORM)]


def _canvas_with_channels(*texts: str, id: str = "canvas_001", version: int = 1) -> Canvas:
    return b.canvas(
        id=id,
        version=version,
        is_generated=False,
        sections=b.sections(0, channels=[CanvasCard(id=f"{id}_{i}", text=t) for i, t in enumerate(texts)]),
    )


def _empty_channels_canvas() -> Canvas:
    return b.canvas(is_generated=False, sections=b.sections(1, channels=[]))


def _future_scenario(*sections: CanvasSection) -> FutureScenario:
    variants = [
        FutureScenarioVariant(
            name=f"v{i}",
            narrative="n",
            adaptation_questions=[AdaptationQuestion(section=s, question="q")],
        )
        for i, s in enumerate(sections)
    ]
    return FutureScenario(
        id="fs_001", canvas_id="canvas_001", uncertainty_drivers=["a", "b"], variants=variants
    )


def _storytelling(*sections: CanvasSection) -> Storytelling:
    return Storytelling(
        id="st_001",
        canvas_id="canvas_001",
        perspective=StorytellingPerspective.COMPANY,
        goal=StorytellingGoal.PITCHING_INVESTORS,
        format=StorytellingFormat.VIDEO_CLIP,
        narrative_text="t",
        canvas_references=[CanvasReference(section=s, note="n") for s in sections],
    )


# --------------------------------------------------------------------------- rules


def _scenario_for(group, k: int = 0, signal: bool = False, id: str | None = None):
    """A CustomerScenario of the k-th segment of `group` (linked through empathy_map_id)."""
    return b.customer_scenario(id or f"cs_{group.id}_{k}", empathy_map_id=group.empathy_map_ids[k], interdependence_signal=signal)


MULTI = SegmentRelationType.MULTI_SIDED
SEGMENTED = SegmentRelationType.SEGMENTED


class TestMultiSidedRequiresSignal:
    rule = RULES["multi_sided_requires_signal"]
    g1 = b.group("g1", 2, MULTI)

    def patterns(self, *groups, tags=MSP):
        return b.patterns(
            groups=list(groups),
            branch_decision=CanvasBranch.UNIFIED_MODEL if len(groups) == 1 else CanvasBranch.SPLIT_MODEL,
            pattern_tags=tags,
        )

    def test_passes_when_a_scenario_of_the_group_carries_the_signal(self):
        scenarios = [_scenario_for(self.g1, 0), _scenario_for(self.g1, 1, signal=True)]
        assert self.rule.check(scenarios, self.patterns(self.g1)) == []

    def test_violation_when_no_scenario_of_the_group_has_the_signal(self):
        scenarios = [_scenario_for(self.g1, 0), _scenario_for(self.g1, 1)]
        (v,) = self.rule.check(scenarios, self.patterns(self.g1))
        assert v.rule_id == self.rule.id
        assert v.severity == "error"
        assert v.artifact_ids == ["patterns_001", "cs_g1_0", "cs_g1_1"]
        assert "Group g1" in v.message and "g1_map_0, g1_map_1" in v.message

    def test_violation_with_no_scenarios_at_all(self):
        assert len(self.rule.check([], self.patterns(self.g1))) == 1

    def test_not_applicable_without_a_multi_sided_group(self):
        seg = b.group("g1", 2, SEGMENTED)
        assert self.rule.check([_scenario_for(seg, 0)], self.patterns(seg, tags=[])) == []

    # --- the split project: the signal must come from the group's OWN segments (ADR-0012 D5)

    def test_split_project_signal_in_group_a_does_not_cover_multi_sided_group_b(self):
        a = b.group("ga", 2, SEGMENTED)
        bb = b.group("gb", 2, MULTI)
        scenarios = [_scenario_for(a, 0, signal=True), _scenario_for(a, 1), _scenario_for(bb, 0), _scenario_for(bb, 1)]
        (v,) = self.rule.check(scenarios, self.patterns(a, bb))
        assert "Group gb" in v.message
        assert v.artifact_ids == ["patterns_001", "cs_gb_0", "cs_gb_1"]  # group A's scenarios are not blamed

    def test_split_project_signal_in_group_b_passes(self):
        a = b.group("ga", 2, SEGMENTED)
        bb = b.group("gb", 2, MULTI)
        scenarios = [_scenario_for(a, 0), _scenario_for(a, 1), _scenario_for(bb, 0, signal=True), _scenario_for(bb, 1)]
        assert self.rule.check(scenarios, self.patterns(a, bb)) == []

    def test_every_multi_sided_group_is_checked_independently(self):
        g1, g2 = b.group("g1", 2, MULTI), b.group("g2", 2, MULTI)
        scenarios = [_scenario_for(g1, 0, signal=True), _scenario_for(g1, 1), _scenario_for(g2, 0), _scenario_for(g2, 1)]
        (v,) = self.rule.check(scenarios, self.patterns(g1, g2))
        assert "Group g2" in v.message

    def test_runs_regardless_of_the_patterns_tag(self):
        # a MULTI_SIDED group with no multi_sided_platform tag is still checked (D5)
        scenarios = [_scenario_for(self.g1, 0), _scenario_for(self.g1, 1)]
        assert len(self.rule.check(scenarios, self.patterns(self.g1, tags=[]))) == 1

    def test_scenarios_of_other_segments_do_not_count_even_with_a_signal(self):
        stranger = b.customer_scenario("cs_x", empathy_map_id="somebody_else", interdependence_signal=True)
        assert len(self.rule.check([stranger], self.patterns(self.g1))) == 1


class TestCanvasGroupIdIsKnown:
    rule = RULES["canvas_group_id_is_known"]

    def test_passes_for_a_known_group(self):
        assert self.rule.check(b.patterns(), b.canvas(group_id="canvas_group_001")) == []

    def test_violation_for_a_dangling_group(self):
        (v,) = self.rule.check(b.patterns(), b.canvas(group_id="nope"))
        assert v.rule_id == self.rule.id
        assert "nope" in v.message
        assert v.artifact_ids == ["canvas_001", "patterns_001"]


class TestFutureScenarioReferencesNonemptySections:
    rule = RULES["future_scenario_references_nonempty_sections"]

    def test_passes_when_referenced_sections_have_cards(self):
        canvas = _canvas_with_channels("c")
        assert self.rule.check(canvas, _future_scenario(CHANNELS, CHANNELS)) == []

    def test_violation_for_every_question_on_an_empty_section(self):
        violations = self.rule.check(
            _empty_channels_canvas(),
            _future_scenario(CHANNELS, CanvasSection.CUSTOMER_SEGMENTS, CHANNELS),
        )
        # Two variants point at the empty channels section; the third doesn't.
        assert len(violations) == 2
        assert all(v.rule_id == self.rule.id and v.severity == "error" for v in violations)
        assert violations[0].artifact_ids == ["fs_001", "canvas_001"]


class TestErrcMoveTargetsCorrectCanvasVersion:
    rule = RULES["errc_move_targets_correct_canvas_version"]

    @staticmethod
    def _errc(card: str, section: CanvasSection = CHANNELS, **overrides):
        return b.errc(
            [b.move(ERRCActionType.ELIMINATE, target_card_text=card, section=section)],
            **overrides,
        )

    def test_passes_when_card_exists_on_the_source_canvas(self):
        v1 = _canvas_with_channels("Direct sales")
        v2 = _canvas_with_channels("Direct sales", id="canvas_002", version=2)
        assert self.rule.check([v1, v2], self._errc("Direct sales")) == []

    def test_create_moves_are_ignored(self):
        errc = b.errc([b.move(ERRCActionType.CREATE, new_text="brand new")])
        assert self.rule.check([_canvas_with_channels("x")], errc) == []

    def test_violation_when_card_exists_only_on_another_version(self):
        # "Partner shops" exists, formally identical, but only on version 2;
        # the Errc edits canvas_001 (version 1), which does not have it.
        v1 = _canvas_with_channels("Direct sales")
        v2 = _canvas_with_channels("Partner shops", id="canvas_002", version=2)
        (v,) = self.rule.check([v1, v2], self._errc("Partner shops"))
        assert v.rule_id == self.rule.id
        assert "canvas_001" in v.message and "version 1" in v.message
        assert v.artifact_ids == ["errc_001", "canvas_001"]

    def test_violation_when_text_exists_in_a_different_section(self):
        v1 = _canvas_with_channels("Direct sales")
        errc = self._errc("Direct sales", section=CanvasSection.REVENUE_STREAMS)
        assert len(self.rule.check([v1], errc)) == 1

    def test_violation_when_text_differs_slightly(self):
        v1 = _canvas_with_channels("Direct sales")
        assert len(self.rule.check([v1], self._errc("direct sales"))) == 1

    def test_violation_when_source_canvas_not_provided(self):
        other = _canvas_with_channels("Direct sales", id="canvas_999")
        (v,) = self.rule.check([other], self._errc("Direct sales"))
        assert "was not provided" in v.message
        assert v.artifact_ids == ["errc_001"]


class TestSwotEnvironmentScanReferenceIsKnown:
    rule = RULES["swot_environment_scan_reference_is_known"]

    def test_passes_when_swot_declares_no_scan(self):
        assert self.rule.check(b.swot(), b.environment_scan()) == []

    def test_passes_when_ids_match(self):
        swot = b.swot(environment_scan_id="environment_scan_001")
        assert self.rule.check(swot, b.environment_scan("environment_scan_001")) == []

    def test_violation_when_ids_differ(self):
        swot = b.swot(environment_scan_id="stale")
        (v,) = self.rule.check(swot, b.environment_scan("environment_scan_001"))
        assert v.rule_id == self.rule.id
        assert v.artifact_ids == ["swot_001", "environment_scan_001"]
        assert "stale" in v.message


class TestStorytellingReferencesNonemptySections:
    rule = RULES["storytelling_references_nonempty_sections"]

    def test_passes_when_sections_have_cards(self):
        assert self.rule.check(_canvas_with_channels("c"), _storytelling(CHANNELS)) == []

    def test_violation_per_reference_to_an_empty_section(self):
        violations = self.rule.check(
            _empty_channels_canvas(), _storytelling(CHANNELS, CanvasSection.CUSTOMER_SEGMENTS)
        )
        assert len(violations) == 1
        assert "channels" in violations[0].message
        assert violations[0].artifact_ids == ["st_001", "canvas_001"]


def test_every_registered_rule_has_a_behaviour_test():
    # Fails when someone adds a rule to the registry without extending this file.
    assert set(RULES) == {
        "multi_sided_requires_signal",
        "canvas_group_id_is_known",
        "future_scenario_references_nonempty_sections",
        "errc_move_targets_correct_canvas_version",
        "swot_environment_scan_reference_is_known",
        "storytelling_references_nonempty_sections",
    }


# --------------------------------------------------------------------------- is_checkable


def _inp(artifact: ArtifactType, optional: bool = False, arity: Arity = Arity.ONE) -> RuleInput:
    return RuleInput(artifact=artifact, arity=arity, optional=optional)


def _noop_rule(*inputs: RuleInput) -> ConsistencyRule:
    return ConsistencyRule(id="synthetic", inputs=inputs, check=lambda *a: [])


class TestIsCheckableWithoutOptionalInputs:
    rule = _noop_rule(_inp(ArtifactType.CANVAS), _inp(ArtifactType.PATTERNS))

    def test_needs_every_input_stage(self):
        assert self.rule.is_checkable({Stage.CANVAS, Stage.PATTERNS})
        assert not self.rule.is_checkable({Stage.CANVAS})
        assert not self.rule.is_checkable({Stage.PATTERNS})
        assert not self.rule.is_checkable(set())

    def test_extra_completed_stages_do_not_matter(self):
        assert self.rule.is_checkable(set(Stage))

    def test_registered_rule(self):
        rule = RULES["multi_sided_requires_signal"]
        assert not rule.is_checkable({Stage.CUSTOMER_SCENARIO})
        assert rule.is_checkable({Stage.CUSTOMER_SCENARIO, Stage.PATTERNS})


class TestIsCheckableWithOptionalInputs:
    rule = _noop_rule(
        _inp(ArtifactType.PITCH),
        _inp(ArtifactType.TEAM_INFO, optional=True),
        _inp(ArtifactType.BUSINESS_CASE, optional=True),
    )

    def test_required_input_still_mandatory(self):
        assert not self.rule.is_checkable(set())
        assert not self.rule.is_checkable({Stage.TEAM_INFO, Stage.BUSINESS_CASE})

    def test_needs_at_least_one_optional_input(self):
        assert not self.rule.is_checkable({Stage.PITCH})

    @pytest.mark.parametrize("optional", [Stage.TEAM_INFO, Stage.BUSINESS_CASE])
    def test_one_optional_input_is_enough(self, optional):
        assert self.rule.is_checkable({Stage.PITCH, optional})

    def test_both_optional_inputs(self):
        assert self.rule.is_checkable({Stage.PITCH, Stage.TEAM_INFO, Stage.BUSINESS_CASE})

    def test_only_optional_inputs_declared(self):
        rule = _noop_rule(_inp(ArtifactType.TEAM_INFO, True), _inp(ArtifactType.BUSINESS_CASE, True))
        assert not rule.is_checkable(set())
        assert rule.is_checkable({Stage.BUSINESS_CASE})

    def test_judge_check_shares_the_semantics(self):
        check = _judge("pitch_optional_sections_grounded_in_sources")
        assert not check.is_checkable({Stage.PITCH})
        assert not check.is_checkable({Stage.TEAM_INFO, Stage.BUSINESS_CASE})
        assert check.is_checkable({Stage.PITCH, Stage.TEAM_INFO})
        assert check.is_checkable({Stage.PITCH, Stage.BUSINESS_CASE})

    def test_brief_check_needs_brief_and_one_of_the_two_scans(self):
        check = _judge("business_case_environment_scan_relevant_to_brief")
        assert not check.is_checkable({Stage.BRIEF})
        assert not check.is_checkable({Stage.BUSINESS_CASE, Stage.ENVIRONMENT_SCAN})
        assert check.is_checkable({Stage.BRIEF, Stage.ENVIRONMENT_SCAN})
        assert check.is_checkable({Stage.BRIEF, Stage.BUSINESS_CASE})


def test_pitch_risk_check_states_the_threat_thresholds():
    # Project rules: grounded if it traces to a negative axis statement or a
    # threat with score >= 3; a severe omission is a threat with score 5 or a
    # negative axis statement with importance >= 8. The fixed catalog puts all
    # 21 threats in every Swot, so "a threat" alone would mean nothing.
    text = _judge("pitch_risk_analysis_grounded_in_swot").instruction
    assert "a threat with score >= 3" in text
    assert "a threat with score 5" in text
    assert "negative axis_statement with importance >= 8" in text
    assert "fixed catalog" in text
    assert "Minor omissions are expected" in text
    assert "or a threat in the Swot" not in text


def _judge(id: str) -> JudgeCheck:
    return next(c for c in JUDGE_CHECKS if c.id == id)


class TestDiscoveryOfOptionalInputRules:
    def test_every_rule_and_check_is_discoverable_once_all_stages_completed(self):
        # Regression: two judge checks used to list team_info/business_case/
        # environment_scan as required inputs. Discovery must find every
        # rule and check once everything is completed.
        everything = set(Stage)
        for item in [*CONSISTENCY_RULES, *JUDGE_CHECKS]:
            assert item.is_checkable(everything), item.id

    def test_check_found_when_only_one_of_its_optional_stages_exists(self):
        # A project that did no business case, but did an environment scan.
        completed = {Stage.BRIEF, Stage.ENVIRONMENT_SCAN}
        found = {c.id for c in JUDGE_CHECKS if c.is_checkable(completed)}
        assert "business_case_environment_scan_relevant_to_brief" in found

    def test_optional_flag_defaults_to_false(self):
        assert RuleInput(artifact=ArtifactType.BRIEF, arity=Arity.ONE).optional is False

    def test_optional_inputs_are_exactly_the_optional_stages(self):
        from bizstruct_domain.schemas.chain import STAGE_REGISTRY

        optional_stages = {s for s, d in STAGE_REGISTRY.stages.items() if d.is_optional}
        for item in [*CONSISTENCY_RULES, *JUDGE_CHECKS]:
            for inp in item.inputs:
                if inp.optional:
                    assert inp.stage in optional_stages, (item.id, inp.stage)


# --------------------------------------------------------------------------- registry integrity


class TestRegistryIntegrity:
    def test_ids_are_unique(self):
        ids = [i.id for i in [*CONSISTENCY_RULES, *JUDGE_CHECKS]]
        assert len(ids) == len(set(ids)), sorted(i for i in ids if ids.count(i) > 1)

    def test_no_duplicate_artifact_type_within_one_item(self):
        for item in [*CONSISTENCY_RULES, *JUDGE_CHECKS]:
            types = [i.artifact for i in item.inputs]
            assert len(types) == len(set(types)), item.id

    @pytest.mark.parametrize("rule", CONSISTENCY_RULES, ids=lambda r: r.id)
    def test_input_count_matches_check_parameters(self, rule):
        params = inspect.signature(rule.check).parameters
        assert len(rule.inputs) == len(params), rule.id

    @pytest.mark.parametrize("rule", CONSISTENCY_RULES, ids=lambda r: r.id)
    def test_many_arity_is_exactly_a_list_parameter(self, rule):
        hints = typing.get_type_hints(rule.check)
        names = list(inspect.signature(rule.check).parameters)
        for name, inp in zip(names, rule.inputs, strict=True):
            is_list = typing.get_origin(hints[name]) is list
            assert is_list == (inp.arity is Arity.MANY), (rule.id, name)

    @pytest.mark.parametrize("rule", CONSISTENCY_RULES, ids=lambda r: r.id)
    def test_rule_returns_annotated_violation_list(self, rule):
        ret = typing.get_type_hints(rule.check)["return"]
        assert typing.get_origin(ret) is list

    @pytest.mark.parametrize("check", JUDGE_CHECKS, ids=lambda c: c.id)
    def test_judge_checks_have_an_instruction(self, check):
        assert check.instruction.strip()
        assert check.inputs
