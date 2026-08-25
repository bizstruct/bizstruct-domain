import uuid

import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.canvas import Canvas, CanvasCard, CanvasGenerated

_SECTIONS = (
    "key_partners", "key_activities", "key_resources", "value_propositions",
    "customer_relationships", "channels", "customer_segments",
    "cost_structure", "revenue_streams",
)


def _card(**overrides) -> dict:
    card = dict(id=uuid.uuid4(), text="Cloud infrastructure providers", is_ai_generated=True)
    card.update(overrides)
    return card


def _generated_kwargs(cards_per_section: int = 2) -> dict:
    return {section: [_card() for _ in range(cards_per_section)] for section in _SECTIONS}


def test_generated_valid_passes():
    model = CanvasGenerated(**_generated_kwargs())
    assert len(model.key_partners) == 2
    assert all(card.is_ai_generated for card in model.key_partners)


def test_generated_too_few_cards_rejected():
    kwargs = _generated_kwargs()
    kwargs["key_partners"] = [_card()]
    with pytest.raises(ValidationError):
        CanvasGenerated(**kwargs)


def test_generated_too_many_cards_rejected():
    kwargs = _generated_kwargs()
    kwargs["revenue_streams"] = [_card(), _card(), _card(), _card(), _card()]
    with pytest.raises(ValidationError):
        CanvasGenerated(**kwargs)


def test_generated_zero_cards_in_one_section_rejected():
    kwargs = _generated_kwargs()
    kwargs["channels"] = []
    with pytest.raises(ValidationError):
        CanvasGenerated(**kwargs)


def test_canvas_crud_shape_allows_more_than_four_cards():
    """Unlike CanvasGenerated, the persisted/CRUD Canvas has no per-section
    cardinality constraint — a user is entitled to add a 5th card."""
    kwargs = {section: [_card() for _ in range(5)] for section in _SECTIONS}
    model = Canvas(**kwargs)
    assert len(model.key_partners) == 5


def test_canvas_crud_shape_allows_zero_cards():
    model = Canvas()
    assert model.key_partners == []


def test_canvas_crud_shape_allows_one_card():
    model = Canvas(key_partners=[_card()])
    assert len(model.key_partners) == 1


def test_card_short_text_rejected():
    with pytest.raises(ValidationError):
        CanvasCard(**_card(text="Ads"))


def test_card_is_ai_generated_defaults_true():
    card = CanvasCard(id=uuid.uuid4(), text="Cloud infrastructure providers")
    assert card.is_ai_generated is True


def test_card_is_ai_generated_can_be_false_for_user_added_cards():
    card = CanvasCard(**_card(is_ai_generated=False))
    assert card.is_ai_generated is False


def test_card_extra_field_rejected():
    with pytest.raises(ValidationError):
        CanvasCard(**_card(color="teal"))


def test_canvas_extra_field_rejected():
    with pytest.raises(ValidationError):
        Canvas(**{**_generated_kwargs(), "unexpected_field": "nope"})


def test_no_order_field_on_card():
    """Card order is list order — there's no separate order/position field
    (see bizstruct-domain's presentation-field safeguard test)."""
    card = CanvasCard(**_card())
    assert not hasattr(card, "order")
    assert not hasattr(card, "position")
    with pytest.raises(ValidationError):
        CanvasCard(**_card(order=1))
