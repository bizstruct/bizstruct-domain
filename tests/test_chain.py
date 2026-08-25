from bizstruct_domain.chain import STAGES, StageMode, stages_for_mode, topological_order, validate_dag


def test_dag_has_no_cycles_and_validates():
    validate_dag()  # should not raise


def test_topological_order_is_deterministic():
    first = topological_order(pro=True)
    second = topological_order(pro=True)
    assert first == second
    assert set(first) == {s.id for s in STAGES}


def test_topological_order_basic_mode_is_deterministic():
    first = topological_order(pro=False)
    second = topological_order(pro=False)
    assert first == second


def test_no_both_stage_depends_on_pro_stage():
    by_id = {s.id: s for s in STAGES}
    for stage in STAGES:
        if stage.mode is not StageMode.BOTH:
            continue
        for dep in stage.depends_on:
            assert by_id[dep].mode is not StageMode.PRO_ONLY, (
                f"{stage.id} (both) depends on {dep} (pro-only)"
            )


def test_stages_for_mode_basic_excludes_pro_only_stages():
    basic_ids = {s.id for s in stages_for_mode(pro=False)}
    assert "environment_scan" not in basic_ids
    assert "assessment" not in basic_ids


def test_stages_for_mode_pro_includes_everything():
    pro_ids = {s.id for s in stages_for_mode(pro=True)}
    assert pro_ids == {s.id for s in STAGES}
