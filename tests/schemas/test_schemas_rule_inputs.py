"""ADR-0012: rule inputs address an artifact type with ONE / MANY / EACH / FINAL.

Covers the migration table of every check, `bind_inputs` (how the kinds treat the instances a caller
gathered), `is_checkable` / `applies_to` for the cycle, and the registry's integrity."""
import inspect
import typing

import pytest
from pydantic import ValidationError

import schema_builders as b
from bizstruct_domain.schemas import (
    ARTIFACT_HOLDERS,
    ARTIFACT_MODELS,
    ARTIFACT_STAGE,
    CONSISTENCY_RULES,
    JUDGE_CHECKS,
    Arity,
    ArtifactType,
    ConsistencyRule,
    InputBindingError,
    JudgeCheck,
    RuleInput,
    Stage,
    bind_inputs,
)
from test_schemas_cycle import cycle

A = ArtifactType
ONE, MANY, EACH, FINAL = Arity.ONE, Arity.MANY, Arity.EACH, Arity.FINAL
ALL_ITEMS = {i.id: i for i in [*CONSISTENCY_RULES, *JUDGE_CHECKS]}

# The migration table of ADR-0012: id -> inputs as (artifact, arity, optional).
MIGRATION = {
    "multi_sided_requires_signal": [(A.CUSTOMER_SCENARIO, MANY, False), (A.PATTERNS, ONE, False)],
    "canvas_group_id_is_known": [(A.PATTERNS, ONE, False), (A.CANVAS, EACH, False)],
    "future_scenario_references_nonempty_sections": [(A.CANVAS, FINAL, False), (A.FUTURE_SCENARIO, ONE, False)],
    "errc_move_targets_correct_canvas_version": [(A.CANVAS, MANY, False), (A.ERRC, EACH, False)],
    "swot_environment_scan_reference_is_known": [(A.SWOT, EACH, False), (A.ENVIRONMENT_SCAN, ONE, False)],
    "storytelling_references_nonempty_sections": [(A.CANVAS, FINAL, False), (A.STORYTELLING, ONE, False)],
    "empathy_map_customer_scenario_persona_consistency": [(A.EMPATHY_MAP, ONE, False), (A.CUSTOMER_SCENARIO, ONE, False)],
    "canvas_grounded_in_customer_insights": [(A.EMPATHY_MAP, MANY, False), (A.CUSTOMER_SCENARIO, MANY, False), (A.CANVAS, ONE, False)],
    "pitch_risk_analysis_grounded_in_swot": [(A.SWOT, FINAL, False), (A.PITCH, ONE, False)],
    "ideation_grounds_pattern_tags": [(A.IDEATION, MANY, False), (A.PATTERNS, ONE, False)],
    "pitch_optional_sections_grounded_in_sources": [(A.PITCH, ONE, False), (A.TEAM_INFO, ONE, True), (A.BUSINESS_CASE, ONE, True)],
    "business_case_environment_scan_relevant_to_brief": [(A.BRIEF, ONE, False), (A.BUSINESS_CASE, ONE, True), (A.ENVIRONMENT_SCAN, ONE, True)],
}


def test_the_table_covers_all_twelve_checks():
    assert len(MIGRATION) == 12 and set(MIGRATION) == set(ALL_ITEMS)


@pytest.mark.parametrize("check_id", MIGRATION)
def test_every_check_has_the_inputs_the_table_says(check_id):
    assert [(i.artifact, i.arity, i.optional) for i in ALL_ITEMS[check_id].inputs] == MIGRATION[check_id]


# --------------------------------------------------------------------------- RuleInput


def test_the_stage_is_derived_from_the_artifact():
    assert RuleInput(artifact=A.SWOT, arity=ONE).stage == Stage.SWOT_ERRC_CYCLE
    assert RuleInput(artifact=A.ERRC, arity=EACH).stage == Stage.SWOT_ERRC_CYCLE
    assert RuleInput(artifact=A.CANVAS, arity=ONE).stage == Stage.CANVAS


def test_the_old_stage_keyword_is_gone():
    with pytest.raises(ValidationError):
        RuleInput(stage=Stage.CANVAS, arity=ONE)  # type: ignore[call-arg]


@pytest.mark.parametrize("artifact", [a for a in A if a not in (A.CANVAS, A.SWOT)])
def test_final_is_only_for_canvas_and_swot(artifact):
    with pytest.raises(ValidationError, match="FINAL applies to canvas and swot only"):
        RuleInput(artifact=artifact, arity=FINAL)


@pytest.mark.parametrize("artifact", [A.CANVAS, A.SWOT])
def test_final_is_allowed_for_canvas_and_swot(artifact):
    assert RuleInput(artifact=artifact, arity=FINAL).arity is FINAL


def test_only_canvas_has_two_holders_and_the_home_stage_is_always_one_of_them():
    assert ARTIFACT_HOLDERS[A.CANVAS] == (Stage.CANVAS, Stage.SWOT_ERRC_CYCLE)
    assert {t for t, h in ARTIFACT_HOLDERS.items() if len(h) > 1} == {A.CANVAS}
    for artifact, holders in ARTIFACT_HOLDERS.items():
        assert ARTIFACT_STAGE[artifact] in holders and set(holders) <= set(Stage)


def test_two_each_inputs_are_refused():
    two = (RuleInput(artifact=A.SWOT, arity=EACH), RuleInput(artifact=A.ERRC, arity=EACH))
    with pytest.raises(ValueError, match="At most one input may be EACH"):
        ConsistencyRule("x", two, lambda *a: [])
    with pytest.raises(ValidationError, match="At most one input may be EACH"):
        JudgeCheck(id="x", inputs=two, instruction="i")


# --------------------------------------------------------------------------- is_checkable / applies_to


def test_final_requires_the_cycle_stage_to_be_done():
    rule = ALL_ITEMS["storytelling_references_nonempty_sections"]
    assert not rule.is_checkable({Stage.CANVAS, Stage.STORYTELLING})
    assert not rule.is_checkable({Stage.SWOT_ERRC_CYCLE})
    assert rule.is_checkable({Stage.SWOT_ERRC_CYCLE, Stage.STORYTELLING})
    risk = ALL_ITEMS["pitch_risk_analysis_grounded_in_swot"]
    assert not risk.is_checkable({Stage.PITCH}) and risk.is_checkable({Stage.PITCH, Stage.SWOT_ERRC_CYCLE})


def test_a_one_canvas_input_needs_only_the_canvas_stage():
    rule = ALL_ITEMS["canvas_group_id_is_known"]  # canvas EACH: home stage only
    assert rule.is_checkable({Stage.PATTERNS, Stage.CANVAS})
    assert not rule.is_checkable({Stage.PATTERNS})


@pytest.mark.parametrize(
    ("check_id", "applies_to"),
    [
        ("canvas_group_id_is_known", [Stage.PATTERNS, Stage.CANVAS, Stage.SWOT_ERRC_CYCLE]),   # EACH canvas
        ("future_scenario_references_nonempty_sections", [Stage.CANVAS, Stage.SWOT_ERRC_CYCLE, Stage.FUTURE_SCENARIO]),
        ("errc_move_targets_correct_canvas_version", [Stage.CANVAS, Stage.SWOT_ERRC_CYCLE]),    # MANY canvas + EACH errc
        ("storytelling_references_nonempty_sections", [Stage.CANVAS, Stage.SWOT_ERRC_CYCLE, Stage.STORYTELLING]),
        ("canvas_grounded_in_customer_insights", [Stage.EMPATHY_MAP, Stage.CUSTOMER_SCENARIO, Stage.CANVAS]),  # canvas ONE: no cycle
        ("pitch_risk_analysis_grounded_in_swot", [Stage.SWOT_ERRC_CYCLE, Stage.PITCH]),
        ("multi_sided_requires_signal", [Stage.CUSTOMER_SCENARIO, Stage.PATTERNS]),
    ],
)
def test_applies_to_includes_the_cycle_for_versioned_canvases(check_id, applies_to):
    assert list(ALL_ITEMS[check_id].applies_to) == applies_to


def test_every_item_is_still_discoverable_once_everything_is_done():
    for item in ALL_ITEMS.values():
        assert item.is_checkable(set(Stage)), item.id


# --------------------------------------------------------------------------- bind_inputs


def inputs(*specs):
    return tuple(RuleInput(artifact=a, arity=ar, optional=o) for a, ar, o in specs)


def test_one_binds_a_single_candidate():
    ((patterns, canvas),) = bind_inputs(inputs((A.PATTERNS, ONE, False), (A.CANVAS, ONE, False)), {A.PATTERNS: [b.patterns()], A.CANVAS: [b.canvas()]})
    assert patterns.id == "patterns_001" and canvas.id == "canvas_001"


def test_one_with_several_candidates_is_an_error():
    canvases = [b.canvas(id="c1"), b.canvas(id="c2", version=2)]
    with pytest.raises(InputBindingError, match="ambiguous input: 2 canvas instances"):
        bind_inputs(inputs((A.CANVAS, ONE, False)), {A.CANVAS: canvases})


def test_one_with_no_candidate_is_an_error_unless_optional():
    with pytest.raises(InputBindingError, match="no team_info"):
        bind_inputs(inputs((A.TEAM_INFO, ONE, False)), {})
    assert bind_inputs(inputs((A.TEAM_INFO, ONE, True)), {}) == [(None,)]


def test_many_binds_the_whole_list_and_an_absent_optional_one_is_empty():
    scenarios = [b.customer_scenario("a"), b.customer_scenario("b")]
    ((bound,),) = bind_inputs(inputs((A.CUSTOMER_SCENARIO, MANY, False)), {A.CUSTOMER_SCENARIO: scenarios})
    assert [s.id for s in bound] == ["a", "b"]
    assert bind_inputs(inputs((A.TEAM_INFO, MANY, True)), {}) == [([],)]
    with pytest.raises(InputBindingError):
        bind_inputs(inputs((A.CUSTOMER_SCENARIO, MANY, False)), {})


@pytest.mark.parametrize("n_errc", [1, 2, 3, 4])
def test_each_runs_once_per_instance_up_to_four_errc(n_errc):
    canvases = [b.canvas(id=f"canvas_{v}", version=v) for v in range(1, n_errc + 2)]
    errcs = [b.errc(id=f"errc_{v}", canvas_id=f"canvas_{v}", from_version=v, to_version=v + 1) for v in range(1, n_errc + 1)]
    rows = bind_inputs(MIGRATED["errc_move_targets_correct_canvas_version"], {A.CANVAS: canvases, A.ERRC: errcs})
    assert [e.id for _, e in rows] == [e.id for e in errcs]
    assert all(c == canvases for c, _ in rows)  # the MANY input is bound once, whole, for every run


@pytest.mark.parametrize("n_swot", [1, 2, 3, 4, 5])
def test_each_runs_once_per_instance_up_to_five_swot(n_swot):
    _, swots = cycle(*range(90, 90 - 5 * n_swot, -5))
    rows = bind_inputs(MIGRATED["swot_environment_scan_reference_is_known"], {A.SWOT: swots, A.ENVIRONMENT_SCAN: [b.environment_scan()]})
    assert [s.id for s, _ in rows] == [s.id for s in swots]
    assert all(scan.id == "environment_scan_001" for _, scan in rows)


def test_each_with_no_instance_runs_nothing_when_optional_and_is_an_error_when_required():
    assert bind_inputs(inputs((A.ERRC, EACH, True), (A.CANVAS, MANY, False)), {A.CANVAS: [b.canvas()]}) == []
    with pytest.raises(InputBindingError):
        bind_inputs(inputs((A.ERRC, EACH, False)), {})


MIGRATED = {i: ALL_ITEMS[i].inputs for i in MIGRATION}


@pytest.mark.parametrize(
    ("totals", "final"),
    [
        ((60,), 1),
        ((60, 70), 1),                           # no improvement: v1 is the final canvas
        ((90, 80, 70, 60, 50), 5),               # steady improvement to v5
        ((90, 80, 70, 75), 3),                   # stop at k = 3
        ((90, 80, 80), 2),                       # equal scores
    ],
)
def test_final_binds_the_selected_swot_and_canvas(totals, final):
    canvases, swots = cycle(*totals)
    story = object()
    ((canvas, bound_story),) = bind_inputs(
        MIGRATED["storytelling_references_nonempty_sections"], {A.CANVAS: canvases, A.SWOT: swots, A.STORYTELLING: [story]}
    )
    assert canvas.version == final and bound_story is story
    ((swot, pitch),) = bind_inputs(MIGRATED["pitch_risk_analysis_grounded_in_swot"], {A.SWOT: swots, A.PITCH: [b.pitch()]})
    assert swot.canvas_version == final


def test_final_without_swots_is_an_error():
    with pytest.raises(InputBindingError, match="final version is undefined"):
        bind_inputs(MIGRATED["future_scenario_references_nonempty_sections"], {A.CANVAS: [b.canvas()], A.FUTURE_SCENARIO: [object()]})


def test_final_with_a_missing_final_canvas_is_an_error():
    canvases, swots = cycle(90, 80, 85)
    with pytest.raises(InputBindingError, match="not provided"):
        bind_inputs(MIGRATED["future_scenario_references_nonempty_sections"], {A.CANVAS: [canvases[0]], A.SWOT: swots, A.FUTURE_SCENARIO: [object()]})


# --------------------------------------------------------------------------- the rules through bind_inputs


def run(rule, candidates):
    return [v for args in bind_inputs(rule.inputs, candidates) for v in rule.check(*args)]


def test_canvas_group_check_runs_for_every_canvas_version():
    rule = ALL_ITEMS["canvas_group_id_is_known"]
    canvases = [b.canvas(id="c1"), b.canvas(id="c2", version=2, group_id="dangling"), b.canvas(id="c3", version=3)]
    violations = run(rule, {A.PATTERNS: [b.patterns()], A.CANVAS: canvases})
    assert [v.artifact_ids[0] for v in violations] == ["c2"]


def test_errc_rule_checks_each_errc_against_its_own_canvas():
    rule = ALL_ITEMS["errc_move_targets_correct_canvas_version"]
    v1 = b.canvas(id="canvas_1", sections=b.sections(0, channels=[b.CanvasCard(id="a", text="Direct sales")]))
    v2 = b.canvas(id="canvas_2", version=2, sections=b.sections(0, channels=[b.CanvasCard(id="b", text="Partners")]))
    good = b.errc([b.move(b.ERRCActionType.ELIMINATE, target_card_text="Direct sales")], id="errc_1", canvas_id="canvas_1")
    bad = b.errc([b.move(b.ERRCActionType.ELIMINATE, target_card_text="Direct sales")], id="errc_2", canvas_id="canvas_2", from_version=2, to_version=3)
    violations = run(rule, {A.CANVAS: [v1, v2], A.ERRC: [good, bad]})
    assert [v.artifact_ids[0] for v in violations] == ["errc_2"]


def test_swot_scan_rule_checks_every_swot_version():
    rule = ALL_ITEMS["swot_environment_scan_reference_is_known"]
    _, swots = cycle(90, 80, 70)
    swots[1] = swots[1].model_copy(update={"environment_scan_id": "stale"})
    violations = run(rule, {A.SWOT: swots, A.ENVIRONMENT_SCAN: [b.environment_scan()]})
    assert [v.artifact_ids[0] for v in violations] == ["swot_2"]


def test_storytelling_rule_reads_the_final_canvas_not_the_last_one():
    from bizstruct_domain.schemas import CanvasReference, CanvasSection, Storytelling, StorytellingFormat, StorytellingGoal, StorytellingPerspective

    rule = ALL_ITEMS["storytelling_references_nonempty_sections"]
    canvases, swots = cycle(90, 80, 85)  # v2 is final; v3 is worse
    canvases[1] = b.canvas(id="canvas_2", version=2, sections=b.sections(0, channels=[b.CanvasCard(id="x", text="t")]))
    canvases[2] = b.canvas(id="canvas_3", version=3, sections=b.sections(0))  # empty channels, would be a violation
    story = Storytelling(
        id="st", canvas_id="canvas_2", perspective=StorytellingPerspective.COMPANY, goal=StorytellingGoal.PITCHING_INVESTORS,
        format=StorytellingFormat.VIDEO_CLIP, narrative_text="t", canvas_references=[CanvasReference(section=CanvasSection.CHANNELS, note="n")],
    )
    assert run(rule, {A.CANVAS: canvases, A.SWOT: swots, A.STORYTELLING: [story]}) == []


# --------------------------------------------------------------------------- registry integrity


@pytest.mark.parametrize("rule", CONSISTENCY_RULES, ids=lambda r: r.id)
def test_each_parameter_is_the_model_of_its_input_artifact(rule):
    hints = typing.get_type_hints(rule.check)
    names = list(inspect.signature(rule.check).parameters)
    assert len(names) == len(rule.inputs)
    for name, spec in zip(names, rule.inputs, strict=True):
        model = ARTIFACT_MODELS[spec.artifact]
        expected = list[model] if spec.arity is MANY else model
        assert hints[name] == expected, (rule.id, name, spec.artifact.value, spec.arity.value)


@pytest.mark.parametrize("item", [*CONSISTENCY_RULES, *JUDGE_CHECKS], ids=lambda i: i.id)
def test_at_most_one_each_and_optional_only_on_optional_stages(item):
    assert sum(i.arity is EACH for i in item.inputs) <= 1
    from bizstruct_domain.schemas import STAGE_REGISTRY

    for spec in item.inputs:
        if spec.optional:
            assert STAGE_REGISTRY.stages[spec.stage].is_optional, (item.id, spec.artifact)


@pytest.mark.parametrize(
    ("arity", "stages"),
    [
        (ONE, (Stage.CANVAS,)),
        (MANY, (Stage.CANVAS, Stage.SWOT_ERRC_CYCLE)),
        (EACH, (Stage.CANVAS, Stage.SWOT_ERRC_CYCLE)),
        (FINAL, (Stage.CANVAS, Stage.SWOT_ERRC_CYCLE)),
    ],
)
def test_read_stages_of_a_canvas_input_by_arity(arity, stages):
    assert RuleInput(artifact=A.CANVAS, arity=arity).read_stages == stages


def test_single_holder_types_read_only_their_own_stage():
    assert RuleInput(artifact=A.PITCH, arity=MANY).read_stages == (Stage.PITCH,)
