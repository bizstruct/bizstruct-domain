import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.empathy_map import EmpathyItem, EmpathyMap


def _item(i: int) -> dict:
    return {
        "id": i,
        "text_uk": f"Достатньо довгий пункт українською номер {i}",
        "text_en": f"A sufficiently long item in English number {i}",
    }


def _valid_kwargs(**overrides) -> dict:
    kwargs = {
        section: [_item(1), _item(2), _item(3)]
        for section in ("says", "thinks", "does", "feels", "pains", "gains")
    }
    kwargs.update(overrides)
    return kwargs


def test_valid_model_passes():
    model = EmpathyMap(**_valid_kwargs())
    assert len(model.says) == 3


def test_minimum_three_items_enforced():
    with pytest.raises(ValidationError):
        EmpathyMap(**_valid_kwargs(pains=[_item(1), _item(2)]))


def test_maximum_six_items_enforced():
    with pytest.raises(ValidationError):
        EmpathyMap(**_valid_kwargs(gains=[_item(i) for i in range(1, 8)]))


def test_six_items_is_allowed():
    model = EmpathyMap(**_valid_kwargs(gains=[_item(i) for i in range(1, 7)]))
    assert len(model.gains) == 6


def test_short_item_text_rejected():
    with pytest.raises(ValidationError):
        EmpathyItem(id=1, text_uk="ok", text_en="A sufficiently long item in English.")


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        EmpathyMap(**_valid_kwargs(unexpected_field="nope"))


def test_missing_section_rejected():
    kwargs = _valid_kwargs()
    del kwargs["says"]
    with pytest.raises(ValidationError):
        EmpathyMap(**kwargs)
