import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.pitch import Pitch

_INVESTOR_TYPES = ["hook", "problem", "solution", "traction", "ask"]
_CUSTOMER_TYPES = ["opening", "empathy", "transformation", "social_proof", "invitation"]


def _slide(slide_type: str) -> dict:
    return {
        "type": slide_type,
        "headline": f"Headline {slide_type}",
        "content": f"Sufficiently long slide content for {slide_type} in English",
    }


def _deck(types: list[str]) -> list[dict]:
    return [_slide(t) for t in types]


def _valid_kwargs(**overrides) -> dict:
    kwargs = {"investor": _deck(_INVESTOR_TYPES), "customer": _deck(_CUSTOMER_TYPES)}
    kwargs.update(overrides)
    return kwargs


def test_valid_model_passes():
    model = Pitch(**_valid_kwargs())
    assert len(model.investor) == 5
    assert len(model.customer) == 5
    assert model.investor[0].type == "hook"
    assert model.customer[0].type == "opening"


def test_wrong_investor_order_rejected():
    with pytest.raises(ValidationError):
        Pitch(**_valid_kwargs(investor=_deck(list(reversed(_INVESTOR_TYPES)))))


def test_wrong_customer_order_rejected():
    with pytest.raises(ValidationError):
        Pitch(**_valid_kwargs(customer=_deck(list(reversed(_CUSTOMER_TYPES)))))


def test_too_few_investor_slides_rejected():
    with pytest.raises(ValidationError):
        Pitch(**_valid_kwargs(investor=_deck(_INVESTOR_TYPES[:4])))


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        Pitch(**_valid_kwargs(unexpected_field="nope"))


def test_no_client_field_exists():
    """The audience is `customer`, not `client` — closes the naming drift
    between bizstruct-be (used `client`) and bizstruct-fe (used `customer`)."""
    model = Pitch(**_valid_kwargs())
    assert hasattr(model, "customer")
    assert not hasattr(model, "client")
