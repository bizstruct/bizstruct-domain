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
"""

from uuid import UUID

from pydantic import ConfigDict, Field

from bizstruct_domain.sanitize import SanitizedModel

# Measured against experiments/results/ (4 models x 5 ideas): at
# max_length=200, revenue_streams and value_propositions cards were
# truncated mid-word 10-13% of the time (other sections' cards run
# naturally shorter and weren't affected) — raised with modest headroom
# rather than per-section, since all nine sections share this constant.
# See the data-quality brief's part D and the task summary.
_CARD_TEXT_KWARGS = dict(min_length=5, max_length=260)


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
    """Output of the `canvas` generation stage: every section must have
    2-4 cards. See module docstring for why this is a subclass of `Canvas`
    rather than a separate unrelated model."""

    key_partners: list[CanvasCard] = Field(min_length=2, max_length=4)
    key_activities: list[CanvasCard] = Field(min_length=2, max_length=4)
    key_resources: list[CanvasCard] = Field(min_length=2, max_length=4)
    value_propositions: list[CanvasCard] = Field(min_length=2, max_length=4)
    customer_relationships: list[CanvasCard] = Field(min_length=2, max_length=4)
    channels: list[CanvasCard] = Field(min_length=2, max_length=4)
    customer_segments: list[CanvasCard] = Field(min_length=2, max_length=4)
    cost_structure: list[CanvasCard] = Field(min_length=2, max_length=4)
    revenue_streams: list[CanvasCard] = Field(min_length=2, max_length=4)
