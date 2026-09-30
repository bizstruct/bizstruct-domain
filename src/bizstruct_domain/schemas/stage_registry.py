from pydantic import BaseModel, Field, model_validator

from .enums import (
    Stage,
)

from .stage_definition import StageDefinition


class StageRegistry(BaseModel):
    """
        A registry of stages in the application.
    """
    stages: dict[Stage, StageDefinition] = Field(
        ...,
        description="A dictionary mapping stages to their definitions.",
        examples=[
            {
                Stage.BRIEF: StageDefinition(
                    id=Stage.BRIEF,
                    depends_on=[],
                    allows_multiple_instances=False,
                    is_optional=False,
                ),
            }
        ]
    )

    def _all_dependencies(self, stage_id: Stage) -> list[Stage]:
        """Hard + optional dependencies of a stage, for graph-shape checks
        (cycles, topological order) where both kinds of edges matter."""
        definition = self.stages[stage_id]
        return [*definition.depends_on, *definition.optional_depends_on]

    @model_validator(mode="after")
    def all_stages_covered_exactly_once(self) -> "StageRegistry":
        """
            Validates that all stages are covered exactly once in the registry.
        """
        missing = set(Stage) - set(self.stages.keys())
        if missing:
            raise ValueError(f"Missing stage definitions for: {missing}")
        return self

    @model_validator(mode="after")
    def key_matches_definition_id(self) -> "StageRegistry":
        """
            Validates that the keys in the stages dictionary match their corresponding definition IDs.
        """
        mismatched = [k for k, d in self.stages.items() if k != d.id]
        if mismatched:
            raise ValueError(f"Stage keys do not match their definition IDs: {mismatched}")
        return self

    @model_validator(mode="after")
    def required_deps_never_optional(self) -> "StageRegistry":
        """
            Validates that a hard dependency never points at a stage marked
            is_optional=True (it might never run, so nothing may require it).
        """
        for stage_id, definition in self.stages.items():
            for dep_id in definition.depends_on:
                if self.stages[dep_id].is_optional:
                    raise ValueError(
                        f"Stage {stage_id} requires optional stage {dep_id}; "
                        f"use optional_depends_on instead"
                    )
        return self

    @model_validator(mode="after")
    def optional_deps_target_optional_stages(self) -> "StageRegistry":
        """
            Validates that optional_depends_on only ever points at stages
            marked is_optional=True. Together with required_deps_never_optional
            this also guarantees a dependency cannot appear in both lists.
        """
        for stage_id, definition in self.stages.items():
            for dep_id in definition.optional_depends_on:
                if not self.stages[dep_id].is_optional:
                    raise ValueError(
                        f"Stage {stage_id} lists {dep_id} in optional_depends_on, "
                        f"but {dep_id} is not marked is_optional"
                    )
        return self

    @model_validator(mode="after")
    def no_unknown_or_cyclic_dependencies(self) -> "StageRegistry":
        """
            Validates that there are no cyclic dependencies among the stages,
            counting both hard and optional edges (an optional input that
            transitively depends on its own consumer could never be
            available to it).
        """
        visited, in_progress = set(), set()

        def visit(stage_id: Stage) -> None:
            if stage_id in visited:
                return
            if stage_id in in_progress:
                raise ValueError(f"Cyclic dependency detected at stage: {stage_id}")
            in_progress.add(stage_id)
            for dep in self._all_dependencies(stage_id):
                visit(dep)
            in_progress.discard(stage_id)
            visited.add(stage_id)

        for stage_id in self.stages:
            visit(stage_id)
        return self

    def topological_order(self) -> list[Stage]:
        """
            Returns the topological order of the stages in the registry.
            Both hard and optional dependencies are respected, so a stage
            that only enriches another (never blocks it) still comes before
            its consumer.
        """
        order: list[Stage] = []
        visited: set[Stage] = set()

        def visit(stage_id: Stage) -> None:
            if stage_id in visited:
                return
            for dep in self._all_dependencies(stage_id):
                visit(dep)
            visited.add(stage_id)
            order.append(stage_id)

        for stage_id in self.stages:
            visit(stage_id)
        return order

    def next_available(
        self,
        completed: set[Stage],
        enabled_optional: set[Stage] | None = None,
    ) -> list[Stage]:
        """
            Returns the stages ready to run next, given a set of completed
            stages and which optional stages are enabled for this project.

            An optional stage only appears here if it is in enabled_optional.
            An optional dependency only blocks its consumer while it is both
            enabled and not yet completed; a disabled optional dependency is
            ignored entirely.
        """
        enabled = enabled_optional or set()
        not_optional = {s for s in enabled if not self.stages[s].is_optional}
        if not_optional:
            raise ValueError(f"enabled_optional contains non-optional stages: {not_optional}")

        available: list[Stage] = []
        for stage_id, definition in self.stages.items():
            if stage_id in completed:
                continue
            if definition.is_optional and stage_id not in enabled:
                continue
            if not set(definition.depends_on) <= completed:
                continue
            if (set(definition.optional_depends_on) & enabled) - completed:
                continue
            available.append(stage_id)
        return available
