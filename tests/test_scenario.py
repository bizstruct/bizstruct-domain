import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.scenario import Scenario, TimelineStep

_STEPS = ["context", "goal", "action", "result", "impact"]


def _persona(**overrides) -> dict:
    persona = dict(
        name="Dmytro Petrenko",
        role="EHS Director",
        pain_point="The annual audit costs €52k and takes 3 weeks to prepare",
    )
    persona.update(overrides)
    return persona


def _timeline(steps=_STEPS) -> list[dict]:
    return [
        {
            "step_type": step_type,
            "text": f"A sufficiently long step text for {step_type} in English",
        }
        for step_type in steps
    ]


def _metrics() -> dict:
    return {
        "before": {"value": "€52k", "label": "Audit cost"},
        "after": {"value": "€6k", "label": "Monitoring cost"},
    }


def _valid_kwargs(**overrides) -> dict:
    kwargs = {"persona": _persona(), "timeline": _timeline(), "metrics": _metrics()}
    kwargs.update(overrides)
    return kwargs


def test_valid_model_passes():
    model = Scenario(**_valid_kwargs())
    assert len(model.timeline) == 5
    assert model.timeline[0].step_type == "context"


def test_wrong_step_order_rejected():
    shuffled = list(reversed(_STEPS))
    with pytest.raises(ValidationError):
        Scenario(**_valid_kwargs(timeline=_timeline(shuffled)))


def test_too_few_timeline_steps_rejected():
    with pytest.raises(ValidationError):
        Scenario(**_valid_kwargs(timeline=_timeline(_STEPS[:4])))


def test_too_many_timeline_steps_rejected():
    extra = _STEPS + ["impact"]
    with pytest.raises(ValidationError):
        Scenario(**_valid_kwargs(timeline=_timeline(extra)))


def test_short_step_text_rejected():
    with pytest.raises(ValidationError):
        TimelineStep(step_type="context", text="ok")


def test_extra_field_on_scenario_rejected():
    with pytest.raises(ValidationError):
        Scenario(**_valid_kwargs(unexpected_field="nope"))


def test_highlight_field_does_not_exist():
    """Presentation logic — the frontend derives highlighting from step_type,
    it isn't stored as domain data."""
    model = Scenario(**_valid_kwargs())
    assert not hasattr(model.timeline[0], "highlight")
    with pytest.raises(ValidationError):
        Scenario(**_valid_kwargs(timeline=[{**step, "highlight": True} for step in _timeline()]))


def test_icon_key_field_does_not_exist():
    """icon_key was 100% derivable from step_type — presentation data, not
    domain data. Consumers pick their own icon per step_type client-side."""
    model = Scenario(**_valid_kwargs())
    assert not hasattr(model.timeline[0], "icon_key")
    with pytest.raises(ValidationError):
        TimelineStep(
            step_type="context",
            icon_key="calendar",
            text="A sufficiently long step text for context in English",
        )
