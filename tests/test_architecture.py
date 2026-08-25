import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.architecture import Architecture
from bizstruct_domain.enums import Epicenter, Pattern, PatternSubtype

VALID_RATIONALE_UK = "Це обґрунтування достатньо довге, щоб пройти перевірку мінімальної довжини поля."
VALID_RATIONALE_EN = "This rationale is long enough to satisfy the minimum length validation for the field."


def _base_kwargs(**overrides):
    kwargs = dict(
        epicenter=Epicenter.CUSTOMER_DRIVEN,
        epicenter_rationale_uk=VALID_RATIONALE_UK,
        epicenter_rationale_en=VALID_RATIONALE_EN,
        pattern=Pattern.FREE,
        pattern_subtype=PatternSubtype.FREEMIUM,
        pattern_rationale_uk=VALID_RATIONALE_UK,
        pattern_rationale_en=VALID_RATIONALE_EN,
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


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        Architecture(**_base_kwargs(unexpected_field="nope"))


def test_short_rationale_rejected():
    with pytest.raises(ValidationError):
        Architecture(**_base_kwargs(epicenter_rationale_uk="закоротко"))
