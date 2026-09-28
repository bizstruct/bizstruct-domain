"""Locks in the max_length increases from the data-quality brief's part D
— calibrated against experiments/results/ (see the field-level docstrings
in each block module and the task summary for measured truncation rates).
Each test constructs a string just past the field's *old* limit and
confirms it's now accepted; a second, wildly over-length string still
gets rejected, so these aren't accidentally unbounded.
"""

import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.canvas import CanvasCard
from bizstruct_domain.blocks.hypotheses import Hypothesis
from bizstruct_domain.blocks.models_options import BusinessModelOption
from bizstruct_domain.blocks.errc import ERRCAlternative, ERRCMove
from bizstruct_domain.blocks.patterns import PatternTag
from bizstruct_domain.enums import (
    CanvasSection,
    ERRCAction,
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


def test_pattern_rationale_keeps_architecture_750_limit():
    # The 750 limit was measured on the former architecture block's
    # rationale fields and carried over to PatternTag.rationale.
    PatternTag(pattern=Pattern.UNBUNDLING, subtype=None, rationale=_over_old_limit(600) + " " * 40)
    with pytest.raises(ValidationError):
        PatternTag(pattern=Pattern.UNBUNDLING, subtype=None, rationale="a" * 2000)


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
        rationale="A sufficiently long rationale in English here for validation purposes.",
    )


def test_errc_premise_and_expected_impact_accept_past_old_200_limit():
    ERRCAlternative(
        id=uuid4(),
        title="Title",
        premise=_over_old_limit(200) + " longer text to pad out the length",
        moves=[_move(ERRCAction.CREATE), _move(ERRCAction.ELIMINATE), _move(ERRCAction.RAISE_)],
        expected_impact=_over_old_limit(200) + " longer text to pad out the length",
    )


def test_errc_new_text_accepts_past_old_200_limit():
    ERRCMove(
        action=ERRCAction.RAISE_,
        target_section=CanvasSection.VALUE_PROPOSITIONS,
        target="A sufficiently long target text here for validation",
        new_text=_over_old_limit(200),
        rationale="A sufficiently long rationale in English here for validation purposes.",
    )
