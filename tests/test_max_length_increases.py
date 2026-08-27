"""Locks in the max_length increases from the data-quality brief's part D
— calibrated against experiments/results/ (see the field-level docstrings
in each block module and the task summary for measured truncation rates).
Each test constructs a string just past the field's *old* limit and
confirms it's now accepted; a second, wildly over-length string still
gets rejected, so these aren't accidentally unbounded.
"""

import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.architecture import Architecture
from bizstruct_domain.blocks.canvas import CanvasCard
from bizstruct_domain.blocks.hypotheses import Hypothesis
from bizstruct_domain.blocks.models_options import BusinessModelOption
from bizstruct_domain.blocks.what_if import ERRCMove, WhatIfAlternative
from bizstruct_domain.enums import (
    CanvasSection,
    ERRCAction,
    Epicenter,
    HypothesisCategory,
    MonetizationType,
    Pattern,
    Quadrant,
)
from uuid import uuid4


def _over_old_limit(old_limit: int, over_by: int = 30) -> str:
    return "a" * (old_limit + over_by)


def test_canvas_card_text_accepts_past_old_200_limit():
    CanvasCard(id=uuid4(), text=_over_old_limit(200))
    with pytest.raises(ValidationError):
        CanvasCard(id=uuid4(), text="a" * 1000)


def test_architecture_rationale_fields_accept_past_old_600_limit():
    Architecture(
        epicenter=Epicenter.CUSTOMER_DRIVEN,
        epicenter_rationale_uk=_over_old_limit(600) + " " * 40,
        epicenter_rationale_en=_over_old_limit(600) + " " * 40,
        pattern=Pattern.UNBUNDLING,
        pattern_subtype=None,
        pattern_rationale_uk=_over_old_limit(600) + " " * 40,
        pattern_rationale_en=_over_old_limit(600) + " " * 40,
    )
    with pytest.raises(ValidationError):
        Architecture(
            epicenter=Epicenter.CUSTOMER_DRIVEN,
            epicenter_rationale_uk="a" * 2000,
            epicenter_rationale_en="a" * 40,
            pattern=Pattern.UNBUNDLING,
            pattern_subtype=None,
            pattern_rationale_uk="a" * 40,
            pattern_rationale_en="a" * 40,
        )


def test_models_options_time_to_value_accepts_past_old_100_limit():
    BusinessModelOption(
        id=uuid4(),
        title="A sufficiently long title",
        audience="A sufficiently long audience description",
        value_proposition="A sufficiently long value proposition here",
        description="A" * 30,
        monetization=MonetizationType.SUBSCRIPTION,
        key_metric="MRR",
        time_to_value=_over_old_limit(100),
        score=50,
        score_rationale="A" * 20,
    )
    with pytest.raises(ValidationError):
        BusinessModelOption(
            id=uuid4(),
            title="A sufficiently long title",
            audience="A sufficiently long audience description",
            value_proposition="A sufficiently long value proposition here",
            description="A" * 30,
            monetization=MonetizationType.SUBSCRIPTION,
            key_metric="MRR",
            time_to_value="a" * 1000,
            score=50,
            score_rationale="A" * 20,
        )


def test_hypotheses_text_accepts_past_old_300_limit():
    Hypothesis(
        id="H1.1",
        text=_over_old_limit(300, over_by=10) + " must include a 42% metric",
        category=HypothesisCategory.DESIRABILITY,
        quadrant=Quadrant.Q1,
    )
    with pytest.raises(ValidationError):
        Hypothesis(id="H1.1", text="a" * 1000, category=HypothesisCategory.DESIRABILITY, quadrant=Quadrant.Q1)


def _move(action: ERRCAction) -> ERRCMove:
    return ERRCMove(
        action=action,
        target_section=CanvasSection.VALUE_PROPOSITIONS,
        target="A sufficiently long target text here for validation",
        new_text="A replacement card text" if action in (ERRCAction.REDUCE, ERRCAction.RAISE_) else None,
        rationale_uk="Достатньо довге обґрунтування українською мовою тут для перевірки.",
        rationale_en="A sufficiently long rationale in English here for validation purposes.",
    )


def test_what_if_premise_and_expected_impact_accept_past_old_200_limit():
    WhatIfAlternative(
        id=uuid4(),
        title_uk="Заголовок",
        title_en="Title",
        premise_uk=_over_old_limit(200) + " довший текст щоб набрати довжину",
        premise_en=_over_old_limit(200) + " longer text to pad out the length",
        moves=[_move(ERRCAction.CREATE), _move(ERRCAction.ELIMINATE), _move(ERRCAction.RAISE_)],
        expected_impact_uk=_over_old_limit(200) + " довший текст щоб набрати довжину",
        expected_impact_en=_over_old_limit(200) + " longer text to pad out the length",
    )


def test_what_if_new_text_accepts_past_old_200_limit():
    ERRCMove(
        action=ERRCAction.RAISE_,
        target_section=CanvasSection.VALUE_PROPOSITIONS,
        target="A sufficiently long target text here for validation",
        new_text=_over_old_limit(200),
        rationale_uk="Достатньо довге обґрунтування українською мовою тут для перевірки.",
        rationale_en="A sufficiently long rationale in English here for validation purposes.",
    )
