"""Output model for the `errc` generation stage (ERRC alternatives).

Renamed from `what_if` (ADR-0008): the id collided with the Ideation
"What if...?" technique, which is a different, upstream step (see
`blocks/ideation.py`). This stage is the Blue Ocean ERRC edit step.

Blue Ocean Strategy's ERRC grid (Eliminate-Reduce-Raise-Create), applied to
the project's own Business Model Canvas (BMG, Strategy -> Business Model
Perspective on Blue Ocean Strategy, pp. 226-231): each alternative is a set
of moves against the canvas the project already has, not an abstract "what
if we tried X" idea disconnected from it.

Project extensions, not methodology quotes: three alternatives per run,
3-6 moves per alternative, and at least three distinct ERRC actions per
alternative. The book describes the four actions; these counts are this
project's quality bar on generated output.

Applying an alternative produces the next canvas version. Storing versions
and running the Canvas -> SWOT -> ERRC loop is bizstruct-be's job, not
this package's (ADR-0008).

Colors and icons are deliberately absent (see
tests/test_no_presentation_fields.py's docstring); the frontend derives
styling from `ERRCAction` itself, a fixed, finite enum.
"""

from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from bizstruct_domain.enums import CanvasSection, ERRCAction, ERRCStatus
from bizstruct_domain.sanitize import SanitizedModel

# `target` matches an existing canvas card's exact text (see ERRCMove's
# docstring) — kept aligned with CanvasCard.text's own max_length.
_TEXT = dict(min_length=5, max_length=200)
# premise/expected_impact are short prose (a few sentences), not a text
# match. Measured against experiments/results/ (4 models x 5 ideas, when
# these were still _uk/_en pairs): at max_length=200 these were truncated
# mid-word 93-97% (premise) and 53-57% (expected_impact) of the time — not
# an occasional overflow but the field's normal case. Raised with
# headroom; see the data-quality brief's part D and the task summary for
# the measured rates this was calibrated against. `rationale` (ERRCMove,
# 400 already) showed no truncation at all, which is the reference point
# for how much room prose actually needs here.
_TEXT_LONG = dict(min_length=5, max_length=320)
_RATIONALE = dict(min_length=10, max_length=400)
_MIN_MOVES = 3
_MAX_MOVES = 6
_MIN_ACTIONS_COVERED = 3


class ERRCMove(SanitizedModel):
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
        # Kept aligned with CanvasCard.text's own max_length (this becomes
        # a card's text) — raised alongside it; see canvas.py's
        # _CARD_TEXT_KWARGS for the same measured-truncation rationale.
        max_length=260,
        description="Required for reduce/raise (the card's text after the "
        "move); must be omitted for eliminate/create.",
    )
    rationale: str = Field(**_RATIONALE)

    @model_validator(mode="after")
    def _validate_new_text_by_action(self) -> "ERRCMove":
        needs_new_text = self.action in (ERRCAction.REDUCE, ERRCAction.RAISE_)
        if needs_new_text and not self.new_text:
            raise ValueError(f"action={self.action.value} requires new_text (the card's replacement text)")
        if not needs_new_text and self.new_text is not None:
            raise ValueError(f"action={self.action.value} must not set new_text (only reduce/raise do)")
        return self


class ERRCAlternative(SanitizedModel):
    """One ERRC-grid alternative business model built from the project's canvas."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str = Field(min_length=1, max_length=150)
    premise: str = Field(**_TEXT_LONG)
    moves: list[ERRCMove] = Field(min_length=_MIN_MOVES, max_length=_MAX_MOVES)
    expected_impact: str = Field(**_TEXT_LONG)
    status: ERRCStatus = ERRCStatus.DRAFT

    @model_validator(mode="after")
    def _validate_action_coverage(self) -> "ERRCAlternative":
        distinct_actions = {move.action for move in self.moves}
        if len(distinct_actions) < _MIN_ACTIONS_COVERED:
            raise ValueError(
                f"alternative must cover at least {_MIN_ACTIONS_COVERED} distinct "
                f"ERRC actions across its moves (got {len(distinct_actions)}: "
                f"{sorted(a.value for a in distinct_actions)}) — a set of moves that "
                "is all `create` (or otherwise under-diverse) is a wishlist, not ERRC"
            )
        return self


class ERRC(SanitizedModel):
    """The persisted/CRUD shape: exactly three ERRC alternatives, at most one
    `applied` (the user's own choice)."""

    model_config = ConfigDict(extra="forbid")

    alternatives: list[ERRCAlternative] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def _validate_at_most_one_applied(self) -> "ERRC":
        applied = [a for a in self.alternatives if a.status is ERRCStatus.APPLIED]
        if len(applied) > 1:
            raise ValueError(
                f"at most one alternative may be status=applied, got {len(applied)} "
                f"({[str(a.id) for a in applied]}) — applying an alternative is a "
                "decision the user makes, and only one can be in effect on the canvas "
                "at a time"
            )
        return self


class ERRCGenerated(ERRC):
    """Output of the `errc` generation stage. Same shape as `ERRC`, plus:
    every alternative must be `status=draft` — the LLM proposes, it never
    decides which alternative is in effect."""

    @model_validator(mode="after")
    def _validate_all_draft(self) -> "ERRCGenerated":
        applied = [a for a in self.alternatives if a.status is not ERRCStatus.DRAFT]
        if applied:
            raise ValueError(
                f"freshly generated alternatives must all be status=draft, got "
                f"non-draft: {[str(a.id) for a in applied]} — applying is a "
                "user decision made after generation, not something generation does"
            )
        return self
