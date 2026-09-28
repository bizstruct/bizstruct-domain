import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.scenario import FutureScenario, FutureScenarioCase
from bizstruct_domain.enums import ScenarioAdaptationArea


def _case(**overrides) -> dict:
    case = dict(
        title="My.medicine",
        narrative="Personalized medicine becomes mainstream and patients expect treatment tailored to their genome.",
        adaptation_questions=[
            dict(area=ScenarioAdaptationArea.VALUE_PROPOSITION, question="What does our offer look like per patient?"),
            dict(area=ScenarioAdaptationArea.REVENUE_STREAMS, question="How will revenues be generated per treatment?"),
        ],
    )
    case.update(overrides)
    return case


def _scenario(**overrides) -> dict:
    scenario = dict(
        uncertainty_drivers=[
            "Emergence of personalized medicine",
            "Shift from treatment to prevention",
        ],
        scenario_matrix=[_case(), _case(title="Business as Usual")],
    )
    scenario.update(overrides)
    return scenario


def test_valid_future_scenario_passes():
    model = FutureScenario(**_scenario())
    assert len(model.scenario_matrix) == 2


def test_single_driver_rejected():
    with pytest.raises(ValidationError):
        FutureScenario(**_scenario(uncertainty_drivers=["Only one driver here"]))


def test_single_scenario_rejected():
    with pytest.raises(ValidationError):
        FutureScenario(**_scenario(scenario_matrix=[_case()]))


def test_more_than_four_scenarios_rejected():
    with pytest.raises(ValidationError):
        FutureScenario(**_scenario(scenario_matrix=[_case() for _ in range(5)]))


def test_repeated_adaptation_area_rejected():
    question = dict(area=ScenarioAdaptationArea.COST_STRUCTURE, question="How will the cost structure change?")
    with pytest.raises(ValidationError):
        FutureScenarioCase(**_case(adaptation_questions=[question, question]))


def test_case_without_adaptation_questions_rejected():
    with pytest.raises(ValidationError):
        FutureScenarioCase(**_case(adaptation_questions=[]))
