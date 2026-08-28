"""Output model for the `empathy_map` generation stage.

Six-section empathy map (says / thinks / does / feels / pains / gains) for
the primary customer persona.

Single language per project, not bilingual (`_uk`/`_en` pairs removed —
see ADR-0006 / the data-quality brief's part E): language is a property of
the project, not the artifact. bizstruct-ml is told which language to
generate in via the queue message; this model doesn't know or care which
one `text` ended up in.
"""

from pydantic import ConfigDict, Field

from bizstruct_domain.sanitize import SanitizedModel


class EmpathyItem(SanitizedModel):
    """One observation within an empathy map section."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(description="1-based position within its section.")
    text: str = Field(min_length=10, max_length=200)


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
