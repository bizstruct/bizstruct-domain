import pytest
from pydantic import ValidationError

from bizstruct_domain.validate_model import FieldFeedback, ValidateModelResult


def _feedback(**overrides) -> dict:
    feedback = dict(
        field="title",
        status="ok",
        comment="Clear and specific, names the product and its core value.",
        suggestion=None,
    )
    feedback.update(overrides)
    return feedback


def test_valid_result_passes():
    result = ValidateModelResult(
        status="valid",
        score=88,
        summary="Strong, specific model with a clear audience and pricing logic.",
        fields=[_feedback()],
    )
    assert result.status == "valid"
    assert len(result.fields) == 1


def test_invalid_field_name_rejected():
    with pytest.raises(ValidationError):
        FieldFeedback(**_feedback(field="tagline"))


def test_invalid_status_rejected():
    with pytest.raises(ValidationError):
        ValidateModelResult(
            status="pending",
            score=50,
            summary="A summary long enough to pass validation.",
            fields=[_feedback()],
        )


def test_score_out_of_range_rejected():
    with pytest.raises(ValidationError):
        ValidateModelResult(
            status="valid",
            score=150,
            summary="A summary long enough to pass validation.",
            fields=[_feedback()],
        )


def test_empty_fields_list_rejected():
    with pytest.raises(ValidationError):
        ValidateModelResult(
            status="valid",
            score=80,
            summary="A summary long enough to pass validation.",
            fields=[],
        )


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        ValidateModelResult(
            status="valid",
            score=80,
            summary="A summary long enough to pass validation.",
            fields=[_feedback()],
            unexpected_field="nope",
        )
