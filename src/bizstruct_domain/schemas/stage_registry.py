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
    def no_unknown_or_cyclic_dependencies(self) -> "StageRegistry":
        """
            Validates that there are no unknown or cyclic dependencies among the stages.
        """
        visited, in_progress = set(), set()
        
        def visit(stage_id: Stage) -> None:
            if stage_id in visited:
                return
            if stage_id in in_progress:
                raise ValueError(f"Cyclic dependency detected at stage: {stage_id}")
            in_progress.add(stage_id)
            for dep in self.stages[stage_id].depends_on:
                visit(dep)
            in_progress.discard(stage_id)
            visited.add(stage_id)
            
        for stage_id in self.stages:
            visit(stage_id)
        return self
    
    def topological_order(self) -> list[Stage]:
        """
            Returns the topological order of the stages in the registry.
        """
        order: list[Stage] = []
        visited: set[Stage] = set()

        def visit(stage_id: Stage) -> None:
            if stage_id in visited:
                return
            for dep in self.stages[stage_id].depends_on:
                visit(dep)
            visited.add(stage_id)
            order.append(stage_id)

        for stage_id in self.stages:
            visit(stage_id)
        return order
    
    def next_available(self, completed: set[Stage]) -> list[Stage]:
        """
            Returns a list of stages that are available to be processed next, given a set of completed stages.
        """
        return [
            stage_id
            for stage_id, definition in self.stages.items()
            if stage_id not in completed
            and set(definition.depends_on) <= completed
        ]

