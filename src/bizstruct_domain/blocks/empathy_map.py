"""Output model for the `empathy_map` generation stage.

Six-section empathy map (says / thinks / does / feels / pains / gains) for
the primary customer persona. Bilingual per item (`text_uk`/`text_en`), not
a `{uk: {...}, en: {...}}` wrapper — see `blocks.architecture` for the same
convention and its rationale.
"""

from pydantic import ConfigDict, Field

from bizstruct_domain.sanitize import SanitizedModel


class EmpathyItem(SanitizedModel):
    """One observation within an empathy map section."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(description="1-based position within its section.")
    text_uk: str = Field(min_length=10, max_length=200)
    text_en: str = Field(min_length=10, max_length=200)


class EmpathyMap(SanitizedModel):
    """Output of the `empathy_map` stage: the first block generated, with no
    prior context — see bizstruct_domain.chain.STAGES.
    """

    model_config = ConfigDict(extra="forbid")

    says: list[EmpathyItem] = Field(min_length=3, max_length=6)
    thinks: list[EmpathyItem] = Field(min_length=3, max_length=6)
    does: list[EmpathyItem] = Field(min_length=3, max_length=6)
    feels: list[EmpathyItem] = Field(min_length=3, max_length=6)
    pains: list[EmpathyItem] = Field(min_length=3, max_length=6)
    gains: list[EmpathyItem] = Field(min_length=3, max_length=6)
