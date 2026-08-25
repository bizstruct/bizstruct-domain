"""Output model for the `scenario` generation stage.

A before/after user-journey scenario for a concrete persona. Bilingual per
field (`_uk`/`_en` suffixes), not a `{uk: {...}, en: {...}}` wrapper.

`highlight` (which timeline steps get visually emphasized) is deliberately
NOT part of this model — it's presentation logic, not domain data. The
frontend derives it from `step_type` (highlight `action` and `result`).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

StepType = Literal["context", "goal", "action", "result", "impact"]
IconKey = Literal["calendar", "target", "zap", "check-circle", "trending-up"]

# Fixed order and icon per step — enforced by the validator below, so the
# frontend can render the timeline in this order without re-sorting.
_STEP_ORDER: tuple[StepType, ...] = ("context", "goal", "action", "result", "impact")
_STEP_ICON: dict[StepType, IconKey] = {
    "context": "calendar",
    "goal": "target",
    "action": "zap",
    "result": "check-circle",
    "impact": "trending-up",
}


class Persona(BaseModel):
    """The protagonist of the scenario — should be the same persona as the
    project's `empathy_map`, not a newly invented one."""

    model_config = ConfigDict(extra="forbid")

    name_uk: str = Field(min_length=1, max_length=100)
    name_en: str = Field(min_length=1, max_length=100)
    role_uk: str = Field(min_length=1, max_length=150)
    role_en: str = Field(min_length=1, max_length=150)
    pain_point_uk: str = Field(min_length=10, max_length=300)
    pain_point_en: str = Field(min_length=10, max_length=300)


class TimelineStep(BaseModel):
    """One step of the persona's journey.

    `icon_key` must match `step_type` per `_STEP_ICON` — validated on the
    parent `Scenario`, since that's where the full ordered list is known.
    """

    model_config = ConfigDict(extra="forbid")

    step_type: StepType
    icon_key: IconKey
    text_uk: str = Field(min_length=10, max_length=300)
    text_en: str = Field(min_length=10, max_length=300)


class MetricValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value_uk: str = Field(min_length=1, max_length=100)
    value_en: str = Field(min_length=1, max_length=100)
    label_uk: str = Field(min_length=1, max_length=150)
    label_en: str = Field(min_length=1, max_length=150)


class ScenarioMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    before: MetricValue
    after: MetricValue


class Scenario(BaseModel):
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
        for step in self.timeline:
            expected_icon = _STEP_ICON[step.step_type]
            if step.icon_key != expected_icon:
                raise ValueError(
                    f"step_type '{step.step_type}' requires icon_key "
                    f"'{expected_icon}', got '{step.icon_key}'"
                )
        return self
