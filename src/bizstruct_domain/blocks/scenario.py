"""Output model for the `scenario` generation stage.

A before/after user-journey scenario for a concrete persona.

Single language per project (see data-quality brief part E / ADR-0006) —
each text field is one field, not a `_uk`/`_en` pair. Language is a
property of the project; this model doesn't carry it.

`highlight` (which timeline steps get visually emphasized) is deliberately
NOT part of this model — it's presentation logic, not domain data. The
frontend derives it from `step_type` (highlight `action` and `result`).

Likewise, this model does NOT carry an icon field for timeline steps.
icon_key used to be stored here, but it was 100% derivable from step_type
(a fixed step_type -> icon mapping, enforced by a validator so the LLM
couldn't drift the two apart) — pure presentation data that added nothing
domain-specific. Consumers pick their own icon per step_type client-side.
"""

from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from bizstruct_domain.sanitize import SanitizedModel

StepType = Literal["context", "goal", "action", "result", "impact"]

# Fixed order — enforced by the validator below, so the frontend can render
# the timeline in this order without re-sorting.
_STEP_ORDER: tuple[StepType, ...] = ("context", "goal", "action", "result", "impact")


class Persona(SanitizedModel):
    """The protagonist of the scenario — should be the same persona as the
    project's `empathy_map`, not a newly invented one."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=150)
    pain_point: str = Field(min_length=10, max_length=300)


class TimelineStep(SanitizedModel):
    """One step of the persona's journey."""

    model_config = ConfigDict(extra="forbid")

    step_type: StepType
    text: str = Field(min_length=10, max_length=300)


class MetricValue(SanitizedModel):
    model_config = ConfigDict(extra="forbid")

    value: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=150)


class ScenarioMetrics(SanitizedModel):
    model_config = ConfigDict(extra="forbid")

    before: MetricValue
    after: MetricValue


class Scenario(SanitizedModel):
    """Output of the `scenario` stage: a before/after user journey."""

    model_config = ConfigDict(extra="forbid")

    persona: Persona
    timeline: list[TimelineStep] = Field(min_length=5, max_length=5)
    metrics: ScenarioMetrics

    @model_validator(mode="after")
    def _validate_timeline(self) -> "Scenario":
        actual = tuple(s.step_type for s in self.timeline)
        if actual != _STEP_ORDER:
            raise ValueError(
                f"timeline steps must be in order {_STEP_ORDER}, got {actual}"
            )
        return self
