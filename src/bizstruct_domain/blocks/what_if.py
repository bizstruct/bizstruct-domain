"""Output model for the `what_if` generation stage (ERRC alternatives).

Blue Ocean Strategy's ERRC grid (Eliminate-Reduce-Raise-Create), applied to
the project's own Business Model Canvas: each alternative is a set of moves
against the canvas the project already has, not an abstract "what if we
tried X" idea disconnected from it. This replaces an earlier, unfounded
Financial/Technical/Emotional-vector design that had no basis in any
business-modeling methodology and gave no structured way to actually change
the model.

Colors and icons were previously hardcoded per-vector in bizstruct-ml
(indigo/coins, teal/cpu, slate/heartHandshake) — the last known case of
presentation leaking into this domain (see
tests/test_no_presentation_fields.py's docstring). Deliberately absent
here; the frontend derives styling from `ERRCAction` itself, a fixed,
finite enum.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bizstruct_domain.enums import CanvasSection, ERRCAction, WhatIfStatus

_TEXT = dict(min_length=5, max_length=200)
_RATIONALE = dict(min_length=10, max_length=400)
_MIN_MOVES = 3
_MAX_MOVES = 6
_MIN_ACTIONS_COVERED = 3


class ERRCMove(BaseModel):
    """A single ERRC action against one canvas section.

    `target` always identifies what the move is about, but what it means
    depends on `action`:
    - eliminate: the exact `text` of the existing card in `target_section`
      to remove. `new_text` must be absent.
    - reduce / raise: the exact `text` of the existing card in
      `target_section` being scaled back/up. `new_text` is required — the
      card's replacement text after the move (there is no way to
      "reduce"/"raise" a card without saying what it now reads).
    - create: the proposed new card's text. `new_text` must be absent.

    This is deliberately a text match on `target`, not a UUID reference —
    see bizstruct-be's application endpoint for how an unresolved match is
    handled (never a silent best-effort guess).
    """

    model_config = ConfigDict(extra="forbid")

    action: ERRCAction
    target_section: CanvasSection = Field(
        description="Which canvas section this move acts on. Required for "
        "all four actions — this is what makes a move concrete instead of "
        "a vague statement of intent.",
    )
    target: str = Field(**_TEXT)
    new_text: str | None = Field(
        default=None,
        max_length=200,
        description="Required for reduce/raise (the card's text after the "
        "move); must be omitted for eliminate/create.",
    )
    rationale_uk: str = Field(**_RATIONALE)
    rationale_en: str = Field(**_RATIONALE)

    @model_validator(mode="after")
    def _validate_new_text_by_action(self) -> "ERRCMove":
        needs_new_text = self.action in (ERRCAction.REDUCE, ERRCAction.RAISE_)
        if needs_new_text and not self.new_text:
            raise ValueError(f"action={self.action.value} requires new_text (the card's replacement text)")
        if not needs_new_text and self.new_text is not None:
            raise ValueError(f"action={self.action.value} must not set new_text (only reduce/raise do)")
        return self


class WhatIfAlternative(BaseModel):
    """One ERRC-grid alternative business model built from the project's canvas."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    title_uk: str = Field(min_length=1, max_length=150)
    title_en: str = Field(min_length=1, max_length=150)
    premise_uk: str = Field(**_TEXT)
    premise_en: str = Field(**_TEXT)
    moves: list[ERRCMove] = Field(min_length=_MIN_MOVES, max_length=_MAX_MOVES)
    expected_impact_uk: str = Field(**_TEXT)
    expected_impact_en: str = Field(**_TEXT)
    status: WhatIfStatus = WhatIfStatus.DRAFT

    @model_validator(mode="after")
    def _validate_action_coverage(self) -> "WhatIfAlternative":
        distinct_actions = {move.action for move in self.moves}
        if len(distinct_actions) < _MIN_ACTIONS_COVERED:
            raise ValueError(
                f"alternative must cover at least {_MIN_ACTIONS_COVERED} distinct "
                f"ERRC actions across its moves (got {len(distinct_actions)}: "
                f"{sorted(a.value for a in distinct_actions)}) — a set of moves that "
                "is all `create` (or otherwise under-diverse) is a wishlist, not ERRC"
            )
        return self


class WhatIf(BaseModel):
    """The persisted/CRUD shape: exactly three ERRC alternatives, at most one
    `applied` (the user's own choice — see module docstring)."""

    model_config = ConfigDict(extra="forbid")

    alternatives: list[WhatIfAlternative] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def _validate_at_most_one_applied(self) -> "WhatIf":
        applied = [a for a in self.alternatives if a.status is WhatIfStatus.APPLIED]
        if len(applied) > 1:
            raise ValueError(
                f"at most one alternative may be status=applied, got {len(applied)} "
                f"({[str(a.id) for a in applied]}) — applying an alternative is a "
                "decision the user makes, and only one can be in effect on the canvas "
                "at a time"
            )
        return self


class WhatIfGenerated(WhatIf):
    """Output of the `what_if` generation stage. Same shape as `WhatIf`, plus:
    every alternative must be `status=draft` — the LLM proposes, it never
    decides which alternative is in effect (see module docstring, B1)."""

    @model_validator(mode="after")
    def _validate_all_draft(self) -> "WhatIfGenerated":
        applied = [a for a in self.alternatives if a.status is not WhatIfStatus.DRAFT]
        if applied:
            raise ValueError(
                f"freshly generated alternatives must all be status=draft, got "
                f"non-draft: {[str(a.id) for a in applied]} — applying is a "
                "user decision made after generation, not something generation does"
            )
        return self
