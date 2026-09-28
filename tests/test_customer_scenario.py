import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.customer_scenario import CustomerScenario
from bizstruct_domain.enums import CanvasSection


def _question(section: CanvasSection) -> dict:
    return dict(section=section, question="Which option fits this situation best?")


def _scenario(**overrides) -> dict:
    data = dict(
        persona="Tourists visiting Paris for a weekend",
        situation="A couple lands at Charles de Gaulle, rents a GPS device at the airport and uses it to plan the day.",
        open_questions=[
            _question(CanvasSection.CHANNELS),
            _question(CanvasSection.CUSTOMER_RELATIONSHIPS),
            _question(CanvasSection.REVENUE_STREAMS),
        ],
    )
    data.update(overrides)
    return data


def test_valid_customer_scenario_passes():
    CustomerScenario(**_scenario())


def test_missing_block_rejected():
    questions = [_question(CanvasSection.CHANNELS)] * 2 + [_question(CanvasSection.REVENUE_STREAMS)]
    with pytest.raises(ValidationError, match="customer_relationships"):
        CustomerScenario(**_scenario(open_questions=questions))


def test_question_on_other_block_rejected():
    questions = _scenario()["open_questions"] + [_question(CanvasSection.KEY_PARTNERS)]
    with pytest.raises(ValidationError, match="key_partners"):
        CustomerScenario(**_scenario(open_questions=questions))
