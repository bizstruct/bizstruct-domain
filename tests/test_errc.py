import uuid

import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.errc import ERRC, ERRCAlternative, ERRCGenerated, ERRCMove
from bizstruct_domain.enums import CanvasSection, ERRCAction, ERRCStatus


def _move(action: ERRCAction = ERRCAction.ELIMINATE, **overrides) -> dict:
    move = dict(
        action=action,
        target_section=CanvasSection.KEY_PARTNERS,
        target="Third-party logistics partner",
        rationale="Reduces dependency on an external partner.",
    )
    if action in (ERRCAction.REDUCE, ERRCAction.RAISE_):
        move["new_text"] = "Regional logistics partner, smaller contract"
    move.update(overrides)
    return move


def _diverse_moves() -> list[dict]:
    return [
        _move(ERRCAction.ELIMINATE),
        _move(ERRCAction.REDUCE),
        _move(ERRCAction.RAISE_),
    ]


def _alternative(**overrides) -> dict:
    alt = dict(
        id=uuid.uuid4(),
        title="Direct delivery",
        premise="Remove logistics intermediaries.",
        moves=_diverse_moves(),
        expected_impact="Lower delivery cost.",
    )
    alt.update(overrides)
    return alt


def _three_alternatives(status_overrides: dict[int, ERRCStatus] | None = None) -> list[dict]:
    alts = [_alternative() for _ in range(3)]
    for i, status in (status_overrides or {}).items():
        alts[i]["status"] = status
    return alts


def test_alternative_with_diverse_actions_passes():
    alt = ERRCAlternative(**_alternative())
    assert len(alt.moves) == 3
    assert alt.status is ERRCStatus.DRAFT


def test_alternative_all_create_rejected():
    kwargs = _alternative(moves=[_move(ERRCAction.CREATE) for _ in range(3)])
    with pytest.raises(ValidationError):
        ERRCAlternative(**kwargs)


def test_alternative_two_distinct_actions_rejected():
    kwargs = _alternative(moves=[_move(ERRCAction.ELIMINATE), _move(ERRCAction.ELIMINATE), _move(ERRCAction.REDUCE)])
    with pytest.raises(ValidationError):
        ERRCAlternative(**kwargs)


def test_alternative_too_few_moves_rejected():
    kwargs = _alternative(moves=_diverse_moves()[:2])
    with pytest.raises(ValidationError):
        ERRCAlternative(**kwargs)


def test_alternative_too_many_moves_rejected():
    kwargs = _alternative(moves=_diverse_moves() + [_move(ERRCAction.CREATE)] * 4)
    with pytest.raises(ValidationError):
        ERRCAlternative(**kwargs)


def test_move_requires_target_section():
    kwargs = _move()
    del kwargs["target_section"]
    with pytest.raises(ValidationError):
        ERRCMove(**kwargs)


def test_move_extra_field_rejected():
    with pytest.raises(ValidationError):
        ERRCMove(**_move(color="indigo"))


def test_errc_exactly_three_alternatives_required():
    with pytest.raises(ValidationError):
        ERRC(alternatives=[_alternative(), _alternative()])


def test_errc_zero_applied_is_valid():
    model = ERRC(alternatives=_three_alternatives())
    assert all(a.status is ERRCStatus.DRAFT for a in model.alternatives)


def test_errc_one_applied_is_valid():
    model = ERRC(alternatives=_three_alternatives({0: ERRCStatus.APPLIED}))
    applied = [a for a in model.alternatives if a.status is ERRCStatus.APPLIED]
    assert len(applied) == 1


def test_errc_two_applied_rejected():
    with pytest.raises(ValidationError):
        ERRC(alternatives=_three_alternatives({0: ERRCStatus.APPLIED, 1: ERRCStatus.APPLIED}))


def test_generated_all_draft_passes():
    model = ERRCGenerated(alternatives=_three_alternatives())
    assert all(a.status is ERRCStatus.DRAFT for a in model.alternatives)


def test_generated_applied_rejected():
    """The generation-stage output must never claim an alternative is
    already applied — that's a decision made after generation, by the user."""
    with pytest.raises(ValidationError):
        ERRCGenerated(alternatives=_three_alternatives({0: ERRCStatus.APPLIED}))


def test_no_presentation_fields_on_move():
    with pytest.raises(ValidationError):
        ERRCMove(**_move(icon="coins"))


def test_move_reduce_requires_new_text():
    kwargs = _move(ERRCAction.REDUCE)
    del kwargs["new_text"]
    with pytest.raises(ValidationError):
        ERRCMove(**kwargs)


def test_move_raise_requires_new_text():
    kwargs = _move(ERRCAction.RAISE_)
    del kwargs["new_text"]
    with pytest.raises(ValidationError):
        ERRCMove(**kwargs)


def test_move_eliminate_rejects_new_text():
    kwargs = _move(ERRCAction.ELIMINATE, new_text="Should not be here")
    with pytest.raises(ValidationError):
        ERRCMove(**kwargs)


def test_move_create_rejects_new_text():
    kwargs = _move(ERRCAction.CREATE, target="A brand new card", new_text="Should not be here")
    with pytest.raises(ValidationError):
        ERRCMove(**kwargs)


def test_move_reduce_with_new_text_passes():
    move = ERRCMove(**_move(ERRCAction.REDUCE))
    assert move.new_text == "Regional logistics partner, smaller contract"
