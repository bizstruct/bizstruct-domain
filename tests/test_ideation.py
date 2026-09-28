import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.ideation import Ideation
from bizstruct_domain.enums import Epicenter

_QUESTION = "What if customers never had to own the tool at all?"


def test_single_epicenter_passes():
    model = Ideation(epicenters=[Epicenter.CUSTOMER_DRIVEN], what_if_questions=[_QUESTION])
    assert model.epicenters == [Epicenter.CUSTOMER_DRIVEN]


def test_multiple_epicenters_pass():
    model = Ideation(
        epicenters=[Epicenter.OFFER_DRIVEN, Epicenter.FINANCE_DRIVEN],
        what_if_questions=[_QUESTION],
    )
    assert len(model.epicenters) == 2


def test_no_epicenter_rejected():
    with pytest.raises(ValidationError):
        Ideation(epicenters=[], what_if_questions=[_QUESTION])


def test_repeated_epicenter_rejected():
    with pytest.raises(ValidationError):
        Ideation(epicenters=[Epicenter.OFFER_DRIVEN, Epicenter.OFFER_DRIVEN], what_if_questions=[_QUESTION])


def test_multiple_epicenter_is_not_a_value():
    with pytest.raises(ValidationError):
        Ideation(epicenters=["multiple_epicenter"], what_if_questions=[_QUESTION])


def test_no_what_if_questions_rejected():
    with pytest.raises(ValidationError):
        Ideation(epicenters=[Epicenter.CUSTOMER_DRIVEN], what_if_questions=[])
