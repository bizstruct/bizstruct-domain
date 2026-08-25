import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.hypotheses import Hypothesis, Hypotheses


def _hyp(id_: str, category: str, quadrant: str, text: str | None = None) -> dict:
    return {
        "id": id_,
        "text": text or f"At least 60% of target users report this pain point in surveys",
        "category": category,
        "quadrant": quadrant,
    }


def _valid_hypotheses() -> list[dict]:
    return [
        _hyp("H1.1", "desirability", "q1"),
        _hyp("H1.2", "desirability", "q1"),
        _hyp("H2.1", "viability", "q2"),
        _hyp("H3.1", "feasibility", "q3"),
        _hyp("H4.1", "feasibility", "q4"),
    ]


def test_valid_model_passes():
    model = Hypotheses(hypotheses=_valid_hypotheses())
    assert len(model.hypotheses) == 5


def test_minimum_five_hypotheses_enforced():
    with pytest.raises(ValidationError):
        Hypotheses(hypotheses=_valid_hypotheses()[:4])


def test_missing_category_rejected():
    only_desirability = [
        _hyp("H1.1", "desirability", "q1"),
        _hyp("H1.2", "desirability", "q1"),
        _hyp("H1.3", "desirability", "q1"),
        _hyp("H1.4", "desirability", "q1"),
        _hyp("H1.5", "desirability", "q1"),
    ]
    with pytest.raises(ValidationError, match="must cover all three categories"):
        Hypotheses(hypotheses=only_desirability)


def test_all_three_categories_present_passes():
    model = Hypotheses(hypotheses=_valid_hypotheses())
    categories = {h.category for h in model.hypotheses}
    assert categories == {"desirability", "viability", "feasibility"}


def test_invalid_id_pattern_rejected():
    with pytest.raises(ValidationError):
        Hypothesis(id="H1", text="A statement long enough to pass the minimum length check", category="desirability", quadrant="q1")


def test_short_text_rejected():
    with pytest.raises(ValidationError):
        Hypothesis(id="H1.1", text="Too short", category="desirability", quadrant="q1")


def test_invalid_category_rejected():
    with pytest.raises(ValidationError):
        Hypothesis(id="H1.1", text="A statement long enough to pass the minimum length check", category="Desirability", quadrant="q1")


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        Hypotheses(hypotheses=_valid_hypotheses(), unexpected_field="nope")
