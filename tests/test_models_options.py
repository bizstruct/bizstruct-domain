import uuid

import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.models_options import BusinessModelOption, ModelsOptions


def _option(**overrides) -> dict:
    option = dict(
        id=uuid.uuid4(),
        title="B2B SaaS · EcoSync",
        audience="Mid-market sustainability teams",
        value_proposition="Automates ESG reporting in minutes",
        description="Monthly subscription giving mid-market companies automated ESG reporting, cutting compliance costs.",
        monetization="subscription",
        key_metric="MRR / NRR",
        time_to_value="30 minutes to first report",
        score=85,
        score_rationale="Strong fit: addresses a specific, recurring pain with a metric-backed value proposition.",
    )
    option.update(overrides)
    return option


def _valid_kwargs(**overrides) -> dict:
    kwargs = {
        "options": [
            _option(monetization="subscription"),
            _option(monetization="transaction_fee"),
            _option(monetization="retainer_plus_saas"),
        ],
    }
    kwargs.update(overrides)
    return kwargs


def test_valid_model_passes():
    model = ModelsOptions(**_valid_kwargs())
    assert len(model.options) == 3
    assert model.selected_id is None


def test_exactly_three_options_enforced_too_few():
    with pytest.raises(ValidationError):
        ModelsOptions(options=[_option(), _option()])


def test_exactly_three_options_enforced_too_many():
    with pytest.raises(ValidationError):
        ModelsOptions(options=[_option(), _option(), _option(), _option()])


def test_selected_id_matching_an_option_passes():
    opts = [_option(), _option(), _option()]
    model = ModelsOptions(options=opts, selected_id=opts[0]["id"])
    assert model.selected_id == opts[0]["id"]


def test_selected_id_not_matching_any_option_rejected():
    opts = [_option(), _option(), _option()]
    with pytest.raises(ValidationError, match="does not match any option id"):
        ModelsOptions(options=opts, selected_id=uuid.uuid4())


def test_invalid_monetization_rejected():
    with pytest.raises(ValidationError):
        BusinessModelOption(**_option(monetization="crowdfunding"))


def test_short_score_rationale_rejected():
    with pytest.raises(ValidationError):
        BusinessModelOption(**_option(score_rationale="too short"))


def test_score_out_of_range_rejected():
    with pytest.raises(ValidationError):
        BusinessModelOption(**_option(score=101))


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        ModelsOptions(**_valid_kwargs(unexpected_field="nope"))
