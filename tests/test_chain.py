import pytest

import bizstruct_domain.chain as chain
from bizstruct_domain.chain import STAGES, Stage, topological_order, validate_dag


def _stage(stage_id: str, depends_on: tuple[str, ...] = (), optional: tuple[str, ...] = ()) -> Stage:
    return Stage(
        id=stage_id,
        title_uk=stage_id,
        depends_on=depends_on,
        optional_depends_on=optional,
        requires_user_gate=False,
        source="-",
    )


def test_dag_has_no_cycles_and_validates():
    validate_dag()  # should not raise


def test_topological_order_is_deterministic_and_complete():
    first = topological_order()
    second = topological_order()
    assert first == second
    assert set(first) == {s.id for s in STAGES}


def test_topological_order_respects_hard_dependencies():
    position = {stage_id: i for i, stage_id in enumerate(topological_order())}
    for stage in STAGES:
        for dep in stage.depends_on:
            assert position[dep] < position[stage.id], f"{dep} must come before {stage.id}"


def test_stages_tuple_itself_lists_every_dependency_first():
    # STAGES order is the tie-breaker for topological_order. Keeping even
    # optional inputs ahead of their consumers means the default order
    # produces them first when they're run at all.
    position = {s.id: i for i, s in enumerate(STAGES)}
    for stage in STAGES:
        for dep in (*stage.depends_on, *stage.optional_depends_on):
            assert position[dep] < position[stage.id], f"{dep} is listed after {stage.id}"


def test_no_stage_lists_a_dependency_as_both_hard_and_optional():
    for stage in STAGES:
        assert not set(stage.depends_on) & set(stage.optional_depends_on), stage.id


def test_patterns_precedes_canvas():
    by_id = {s.id: s for s in STAGES}
    assert "patterns" in by_id["canvas"].depends_on
    assert "canvas" not in by_id["patterns"].depends_on


def test_errc_depends_on_assessment_only_optionally():
    by_id = {s.id: s for s in STAGES}
    assert "assessment" in by_id["errc"].optional_depends_on
    assert "assessment" not in by_id["errc"].depends_on


def test_assessment_depends_on_environment_scan_only_optionally():
    by_id = {s.id: s for s in STAGES}
    assert "environment_scan" in by_id["assessment"].optional_depends_on
    assert "environment_scan" not in by_id["assessment"].depends_on


def test_pitch_team_info_and_business_case_are_optional_inputs():
    by_id = {s.id: s for s in STAGES}
    assert set(by_id["pitch"].optional_depends_on) == {"team_info", "business_case"}


def test_every_stage_has_a_source():
    for stage in STAGES:
        assert stage.source.strip(), stage.id


def test_stage_has_no_mode_field():
    # Product tiers (Basic/Pro) are bizstruct-be's decision — ADR-0008.
    assert "mode" not in Stage.model_fields


def _validate_with(monkeypatch: pytest.MonkeyPatch, stages: tuple[Stage, ...]) -> None:
    monkeypatch.setattr(chain, "STAGES", stages)
    validate_dag()


def test_validate_dag_rejects_unknown_hard_dependency(monkeypatch):
    with pytest.raises(ValueError, match="unknown"):
        _validate_with(monkeypatch, (_stage("a", depends_on=("ghost",)),))


def test_validate_dag_rejects_unknown_optional_dependency(monkeypatch):
    with pytest.raises(ValueError, match="unknown"):
        _validate_with(monkeypatch, (_stage("a", optional=("ghost",)),))


def test_validate_dag_rejects_dependency_in_both_lists(monkeypatch):
    with pytest.raises(ValueError, match="both"):
        _validate_with(monkeypatch, (_stage("a"), _stage("b", depends_on=("a",), optional=("a",))))


def test_validate_dag_rejects_hard_cycle(monkeypatch):
    with pytest.raises(ValueError, match="cycle"):
        _validate_with(monkeypatch, (_stage("a", depends_on=("b",)), _stage("b", depends_on=("a",))))


def test_validate_dag_rejects_cycle_through_optional_edge(monkeypatch):
    with pytest.raises(ValueError, match="cycle"):
        _validate_with(monkeypatch, (_stage("a", optional=("b",)), _stage("b", depends_on=("a",))))


def test_validate_dag_rejects_duplicate_ids(monkeypatch):
    with pytest.raises(ValueError, match="duplicate"):
        _validate_with(monkeypatch, (_stage("a"), _stage("a")))
