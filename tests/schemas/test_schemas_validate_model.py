import pytest
from pydantic import ValidationError

from bizstruct_domain.schemas import FieldFeedback, ValidateModelResult


def _feedback(**overrides) -> dict:
    feedback = dict(
        field="title",
        status="ok",
        comment="Clear and specific, names the product and its core value.",
        suggestion=None,
    )
    feedback.update(overrides)
    return feedback


def _result(**overrides) -> dict:
    data = dict(
        status="valid",
        score=80,
        summary="A summary long enough to pass validation.",
        fields=[_feedback()],
    )
    data.update(overrides)
    return data


def test_valid_result_passes():
    result = ValidateModelResult(**_result(score=88))
    assert result.status == "valid"
    assert len(result.fields) == 1


@pytest.mark.parametrize("name", ["title", "value_proposition", "tagline", "anything_else"])
def test_field_is_an_open_string(name):
    # Typed against no model: the feature has no subject model (ADR-0009).
    assert FieldFeedback(**_feedback(field=name)).field == name


def test_empty_field_name_rejected():
    with pytest.raises(ValidationError):
        FieldFeedback(**_feedback(field=""))


def test_invalid_status_rejected():
    with pytest.raises(ValidationError):
        ValidateModelResult(**_result(status="pending"))


@pytest.mark.parametrize("score", [-1, 101, 150])
def test_score_out_of_range_rejected(score):
    with pytest.raises(ValidationError):
        ValidateModelResult(**_result(score=score))


@pytest.mark.parametrize("score", [0, 100])
def test_score_bounds_accepted(score):
    assert ValidateModelResult(**_result(score=score)).score == score


def test_empty_fields_list_rejected():
    with pytest.raises(ValidationError):
        ValidateModelResult(**_result(fields=[]))


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        ValidateModelResult(**_result(unexpected_field="nope"))
    with pytest.raises(ValidationError):
        FieldFeedback(**_feedback(unexpected_field="nope"))


def test_nul_byte_is_stripped_from_feedback():
    assert FieldFeedback(**_feedback(comment="Clear\x00 and specific")).comment == "Clear and specific"
