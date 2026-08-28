import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.architecture import Architecture
from bizstruct_domain.enums import Epicenter, Pattern, PatternSubtype

VALID_RATIONALE = "This rationale is long enough to satisfy the minimum length validation for the field."


def _base_kwargs(**overrides):
    kwargs = dict(
        epicenter=Epicenter.CUSTOMER_DRIVEN,
        epicenter_rationale=VALID_RATIONALE,
        pattern=Pattern.FREE,
        pattern_subtype=PatternSubtype.FREEMIUM,
        pattern_rationale=VALID_RATIONALE,
    )
    kwargs.update(overrides)
    return kwargs


def test_valid_model_passes():
    model = Architecture(**_base_kwargs())
    assert model.pattern_subtype is PatternSubtype.FREEMIUM


def test_long_tail_with_any_subtype_fails():
    with pytest.raises(ValidationError):
        Architecture(**_base_kwargs(pattern=Pattern.LONG_TAIL, pattern_subtype=PatternSubtype.FREEMIUM))


def test_free_with_mismatched_subtype_fails():
    with pytest.raises(ValidationError):
        Architecture(**_base_kwargs(pattern=Pattern.FREE, pattern_subtype=PatternSubtype.OUTSIDE_IN))


def test_free_with_freemium_passes():
    model = Architecture(**_base_kwargs(pattern=Pattern.FREE, pattern_subtype=PatternSubtype.FREEMIUM))
    assert model.pattern is Pattern.FREE


def test_free_without_subtype_fails():
    with pytest.raises(ValidationError):
        Architecture(**_base_kwargs(pattern=Pattern.FREE, pattern_subtype=None))


def test_open_business_model_without_subtype_fails():
    with pytest.raises(ValidationError):
        Architecture(
            **_base_kwargs(
                pattern=Pattern.OPEN_BUSINESS_MODEL,
                pattern_subtype=None,
            )
        )


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        Architecture(**_base_kwargs(unexpected_field="nope"))


def test_short_rationale_rejected():
    with pytest.raises(ValidationError):
        Architecture(**_base_kwargs(epicenter_rationale="too short"))
