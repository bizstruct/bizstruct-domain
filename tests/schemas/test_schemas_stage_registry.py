import pytest
from pydantic import ValidationError

from bizstruct_domain.schemas.chain import STAGE_REGISTRY
from bizstruct_domain.schemas.enums import Stage
from bizstruct_domain.schemas.stage_registry import StageRegistry

CANVAS_DEPS = [
    Stage.BRIEF,
    Stage.EMPATHY_MAP,
    Stage.CUSTOMER_SCENARIO,
    Stage.IDEATION,
    Stage.PATTERNS,
]
THROUGH_CANVAS = set(CANVAS_DEPS) | {Stage.CANVAS}


def _definitions() -> dict:
    """Mutable deep copy of the real registry's definitions."""
    return {k: v.model_copy(deep=True) for k, v in STAGE_REGISTRY.stages.items()}


class TestRegistryContent:
    def test_has_exactly_13_stages(self):
        assert len(STAGE_REGISTRY.stages) == 13
        assert set(STAGE_REGISTRY.stages) == set(Stage)

    def test_only_brief_is_available_at_start(self):
        assert STAGE_REGISTRY.next_available(set()) == [Stage.BRIEF]

    def test_topological_order_covers_every_stage_once(self):
        order = STAGE_REGISTRY.topological_order()
        assert sorted(order) == sorted(Stage)

    def test_topological_order_puts_enrichment_before_consumer(self):
        order = STAGE_REGISTRY.topological_order()
        assert order.index(Stage.ENVIRONMENT_SCAN) < order.index(Stage.SWOT_ERRC_CYCLE)
        assert order.index(Stage.TEAM_INFO) < order.index(Stage.PITCH)
        assert order.index(Stage.BUSINESS_CASE) < order.index(Stage.PITCH)

    def test_topological_order_respects_every_edge(self):
        order = STAGE_REGISTRY.topological_order()
        for stage, definition in STAGE_REGISTRY.stages.items():
            for dep in [*definition.depends_on, *definition.optional_depends_on]:
                assert order.index(dep) < order.index(stage)

    def test_canvas_depends_on_the_five_direct_deps(self):
        assert set(STAGE_REGISTRY.stages[Stage.CANVAS].depends_on) == set(CANVAS_DEPS)

    @pytest.mark.parametrize("stage", [Stage.BUSINESS_CASE, Stage.ENVIRONMENT_SCAN])
    def test_enrichment_stages_depend_on_brief(self, stage):
        assert STAGE_REGISTRY.stages[stage].depends_on == [Stage.BRIEF]


MULTI_INSTANCE = {
    Stage.EMPATHY_MAP,
    Stage.CUSTOMER_SCENARIO,
    Stage.IDEATION,
    Stage.CANVAS,
    Stage.SWOT_ERRC_CYCLE,
    Stage.STORYTELLING,
    Stage.FUTURE_SCENARIO,
    Stage.PITCH,
}


class TestMultiplicityFlags:
    def test_exact_set_of_multi_instance_stages(self):
        flagged = {s for s, d in STAGE_REGISTRY.stages.items() if d.allows_multiple_instances}
        assert flagged == MULTI_INSTANCE

    @pytest.mark.parametrize(
        "stage",
        [Stage.BRIEF, Stage.PATTERNS, Stage.TEAM_INFO, Stage.BUSINESS_CASE, Stage.ENVIRONMENT_SCAN],
    )
    def test_single_instance_stages(self, stage):
        assert STAGE_REGISTRY.stages[stage].allows_multiple_instances is False

    def test_the_flag_is_a_declaration_the_graph_logic_does_not_read(self):
        # Flipping every flag must not change topological order, next_available
        # or the stage machine's ready_stages / dependents_of.
        from bizstruct_domain.stage_machine import dependents_of, ready_stages

        flipped = _definitions()
        for definition in flipped.values():
            definition.allows_multiple_instances = not definition.allows_multiple_instances
        other = StageRegistry(stages=flipped)
        assert other.topological_order() == STAGE_REGISTRY.topological_order()
        orders = STAGE_REGISTRY.topological_order()
        for i in range(len(orders) + 1):
            completed = set(orders[:i])
            for enabled in (set(), {Stage.ENVIRONMENT_SCAN}, {Stage.TEAM_INFO, Stage.BUSINESS_CASE}):
                assert other.next_available(completed, enabled) == STAGE_REGISTRY.next_available(completed, enabled)
        # stage_machine reads STAGE_REGISTRY only for dependencies, never the flag
        import bizstruct_domain.stage_machine as machine
        import inspect

        assert "allows_multiple_instances" not in inspect.getsource(machine)
        assert dependents_of("canvas")
        assert ready_stages([]) == ()


class TestNextAvailable:
    @pytest.mark.parametrize("missing", CANVAS_DEPS)
    def test_canvas_blocked_until_all_five_deps_completed(self, missing):
        completed = set(CANVAS_DEPS) - {missing}
        assert Stage.CANVAS not in STAGE_REGISTRY.next_available(completed)

    def test_canvas_available_once_all_five_deps_completed(self):
        assert Stage.CANVAS in STAGE_REGISTRY.next_available(set(CANVAS_DEPS))

    def test_optional_stage_hidden_unless_enabled(self):
        completed = {Stage.BRIEF}
        assert Stage.ENVIRONMENT_SCAN not in STAGE_REGISTRY.next_available(completed)
        assert Stage.ENVIRONMENT_SCAN in STAGE_REGISTRY.next_available(
            completed, {Stage.ENVIRONMENT_SCAN}
        )

    def test_enabled_optional_stage_still_needs_its_own_deps(self):
        assert Stage.ENVIRONMENT_SCAN not in STAGE_REGISTRY.next_available(
            set(), {Stage.ENVIRONMENT_SCAN}
        )

    def test_optional_stage_without_deps_available_when_enabled(self):
        assert Stage.TEAM_INFO in STAGE_REGISTRY.next_available(set(), {Stage.TEAM_INFO})
        assert Stage.TEAM_INFO not in STAGE_REGISTRY.next_available(set())

    def test_completed_stage_is_not_offered_again(self):
        assert Stage.BRIEF not in STAGE_REGISTRY.next_available({Stage.BRIEF})

    def test_enabled_incomplete_optional_dep_blocks_consumer(self):
        completed = THROUGH_CANVAS | {Stage.BRIEF}
        assert Stage.SWOT_ERRC_CYCLE in STAGE_REGISTRY.next_available(completed)
        assert Stage.SWOT_ERRC_CYCLE not in STAGE_REGISTRY.next_available(
            completed, {Stage.ENVIRONMENT_SCAN}
        )

    def test_completed_optional_dep_unblocks_consumer(self):
        completed = THROUGH_CANVAS | {Stage.ENVIRONMENT_SCAN}
        assert Stage.SWOT_ERRC_CYCLE in STAGE_REGISTRY.next_available(
            completed, {Stage.ENVIRONMENT_SCAN}
        )

    def test_disabled_optional_dep_does_not_block_consumer(self):
        # ENVIRONMENT_SCAN enabled, TEAM_INFO/BUSINESS_CASE not: pitch ignores them.
        completed = THROUGH_CANVAS | {
            Stage.ENVIRONMENT_SCAN,
            Stage.SWOT_ERRC_CYCLE,
            Stage.STORYTELLING,
        }
        assert Stage.PITCH in STAGE_REGISTRY.next_available(
            completed, {Stage.ENVIRONMENT_SCAN}
        )

    @pytest.mark.parametrize("pending", [Stage.TEAM_INFO, Stage.BUSINESS_CASE])
    def test_enabled_pending_pitch_input_blocks_pitch(self, pending):
        completed = THROUGH_CANVAS | {
            Stage.SWOT_ERRC_CYCLE,
            Stage.STORYTELLING,
            Stage.TEAM_INFO,
            Stage.BUSINESS_CASE,
        } - {pending}
        assert Stage.PITCH not in STAGE_REGISTRY.next_available(completed, {pending})

    @pytest.mark.parametrize(
        "bad", [Stage.BRIEF, Stage.CANVAS, Stage.PITCH]
    )
    def test_enabling_a_non_optional_stage_raises(self, bad):
        with pytest.raises(ValueError, match="non-optional"):
            STAGE_REGISTRY.next_available(set(), {bad})

    def test_enabling_non_optional_alongside_optional_raises(self):
        with pytest.raises(ValueError, match="non-optional"):
            STAGE_REGISTRY.next_available(set(), {Stage.TEAM_INFO, Stage.CANVAS})


class TestRegistryValidation:
    def test_real_definitions_are_accepted(self):
        StageRegistry(stages=_definitions())

    def test_rejects_missing_stage(self):
        defs = _definitions()
        del defs[Stage.PITCH]
        with pytest.raises(ValidationError, match="Missing stage definitions"):
            StageRegistry(stages=defs)

    def test_rejects_key_id_mismatch(self):
        defs = _definitions()
        defs[Stage.IDEATION] = defs[Stage.CUSTOMER_SCENARIO]
        with pytest.raises(ValidationError, match="do not match"):
            StageRegistry(stages=defs)

    def test_rejects_required_dep_on_optional_stage(self):
        defs = _definitions()
        defs[Stage.STORYTELLING].depends_on.append(Stage.TEAM_INFO)
        with pytest.raises(ValidationError, match="requires optional stage"):
            StageRegistry(stages=defs)

    def test_rejects_optional_dep_on_non_optional_stage(self):
        defs = _definitions()
        defs[Stage.STORYTELLING].optional_depends_on.append(Stage.BRIEF)
        with pytest.raises(ValidationError, match="not marked is_optional"):
            StageRegistry(stages=defs)

    def test_rejects_cycle_through_hard_edges(self):
        defs = _definitions()
        defs[Stage.BRIEF].depends_on = [Stage.EMPATHY_MAP]
        with pytest.raises(ValidationError, match="Cyclic dependency"):
            StageRegistry(stages=defs)

    def test_rejects_cycle_through_an_optional_edge(self):
        # BRIEF -(optional)-> TEAM_INFO -(hard)-> BRIEF. Every per-edge rule
        # is satisfied; only the cycle check can catch it.
        defs = _definitions()
        defs[Stage.BRIEF].optional_depends_on = [Stage.TEAM_INFO]
        defs[Stage.TEAM_INFO].depends_on = [Stage.BRIEF]
        with pytest.raises(ValidationError, match="Cyclic dependency"):
            StageRegistry(stages=defs)
