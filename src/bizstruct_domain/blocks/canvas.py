"""Output model for the `canvas` generation stage (Business Model Canvas).

The nine sections are separate fields (not `dict[CanvasSection, ...]`) —
this keeps the shape compatible with structured output (`beta.chat.
completions.parse` needs a fixed set of named fields, not an open dict) and
with straightforward TS codegen on the frontend. CRUD operations map a
`CanvasSection` value to the matching field name instead.

Card order within a section IS its list order — there's deliberately no
`order`/`position` field (see bizstruct-domain's presentation-field
safeguard test); the list is already ordered, and adding a redundant
ordinal would just be one more thing that can drift out of sync with it.

Two models, not one, because generation and CRUD have different
cardinality rules:
- `CanvasGenerated` is what the `canvas` stage must produce: each section
  gets 2-4 cards. This is what bizstruct-ml's structured output is typed
  against and what bizstruct-be's hook validates the ml payload with.
- `Canvas` is the persisted/CRUD shape: no per-section count constraint.
  Once a user is editing their own canvas they're entitled to add a 5th
  card to a section or delete down to zero — the 2-4 rule is a quality bar
  on what the LLM generates, not a permanent shape restriction on the data.
  `CanvasGenerated` IS-A `Canvas` (same fields, tighter bounds only at
  generation time), so a freshly generated canvas satisfies both.

`detail_level` (BMG, Design -> Prototyping, p. 165) sets which sections the
generation-time 2-4 rule applies to: a napkin sketch only needs Value
Propositions and Revenue Streams; elaborated and business-case canvases
need all nine.

This is the shape of one canvas. Which variant (shared, or per segment
after the Patterns A/B decision) and which ERRC iteration a canvas belongs
to is stored by bizstruct-be, not modeled here (ADR-0008).
"""

from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from bizstruct_domain.enums import CanvasDetailLevel, CanvasSection
from bizstruct_domain.sanitize import SanitizedModel

# Measured against experiments/results/ (4 models x 5 ideas): at
# max_length=200, revenue_streams and value_propositions cards were
# truncated mid-word 10-13% of the time (other sections' cards run
# naturally shorter and weren't affected) — raised with modest headroom
# rather than per-section, since all nine sections share this constant.
# See the data-quality brief's part D and the task summary.
_CARD_TEXT_KWARGS = dict(min_length=5, max_length=260)

_MIN_GENERATED_CARDS = 2
_MAX_GENERATED_CARDS = 4

# Sections the generation-time 2-4 rule applies to, per detail level. Other
# sections may be empty (up to the same maximum).
REQUIRED_SECTIONS: dict[CanvasDetailLevel, frozenset[CanvasSection]] = {
    CanvasDetailLevel.NAPKIN: frozenset({CanvasSection.VALUE_PROPOSITIONS, CanvasSection.REVENUE_STREAMS}),
    CanvasDetailLevel.ELABORATED: frozenset(CanvasSection),
    CanvasDetailLevel.BUSINESS_CASE: frozenset(CanvasSection),
}


class CanvasCard(SanitizedModel):
    """A single card within one Business Model Canvas section."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    text: str = Field(**_CARD_TEXT_KWARGS)
    is_ai_generated: bool = Field(
        default=True,
        description="True if the LLM generated this card. Must be set to "
        "False whenever a user adds a card or edits an existing one's text.",
    )


class Canvas(SanitizedModel):
    """The nine Business Model Canvas sections, as persisted and edited via
    CRUD. No per-section cardinality constraint — see module docstring."""

    model_config = ConfigDict(extra="forbid")

    detail_level: CanvasDetailLevel = CanvasDetailLevel.ELABORATED
    key_partners: list[CanvasCard] = Field(default_factory=list)
    key_activities: list[CanvasCard] = Field(default_factory=list)
    key_resources: list[CanvasCard] = Field(default_factory=list)
    value_propositions: list[CanvasCard] = Field(default_factory=list)
    customer_relationships: list[CanvasCard] = Field(default_factory=list)
    channels: list[CanvasCard] = Field(default_factory=list)
    customer_segments: list[CanvasCard] = Field(default_factory=list)
    cost_structure: list[CanvasCard] = Field(default_factory=list)
    revenue_streams: list[CanvasCard] = Field(default_factory=list)


class CanvasGenerated(Canvas):
    """Output of the `canvas` generation stage: each section required by
    `detail_level` (see `REQUIRED_SECTIONS`) must have 2-4 cards, the rest
    at most 4. See module docstring for why this is a subclass of `Canvas`
    rather than a separate unrelated model."""

    key_partners: list[CanvasCard] = Field(max_length=_MAX_GENERATED_CARDS)
    key_activities: list[CanvasCard] = Field(max_length=_MAX_GENERATED_CARDS)
    key_resources: list[CanvasCard] = Field(max_length=_MAX_GENERATED_CARDS)
    value_propositions: list[CanvasCard] = Field(max_length=_MAX_GENERATED_CARDS)
    customer_relationships: list[CanvasCard] = Field(max_length=_MAX_GENERATED_CARDS)
    channels: list[CanvasCard] = Field(max_length=_MAX_GENERATED_CARDS)
    customer_segments: list[CanvasCard] = Field(max_length=_MAX_GENERATED_CARDS)
    cost_structure: list[CanvasCard] = Field(max_length=_MAX_GENERATED_CARDS)
    revenue_streams: list[CanvasCard] = Field(max_length=_MAX_GENERATED_CARDS)

    @model_validator(mode="after")
    def _validate_required_sections(self) -> "CanvasGenerated":
        short = sorted(
            section.value
            for section in REQUIRED_SECTIONS[self.detail_level]
            if len(getattr(self, section.value)) < _MIN_GENERATED_CARDS
        )
        if short:
            raise ValueError(
                f"detail_level={self.detail_level.value} requires at least "
                f"{_MIN_GENERATED_CARDS} cards in: {', '.join(short)}"
            )
        return self
