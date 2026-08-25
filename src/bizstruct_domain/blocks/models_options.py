"""Output model for the `models_options` generation stage.

This block had the worst field drift of any of the eight: bizstruct-ml
generated `name`/`monetization`/`target_segment`/`score`, bizstruct-be's
`/validate` side-channel expected `title`/`audience`/`value_proposition`/
`description`, and bizstruct-fe read yet a third shape (`title`/`audience`/
`valueProposition`/`description`, silently dropping `monetization`,
`key_metric`, `time_to_value`, and `score` entirely — they were generated
but never shown). This model is the single canonical shape all three now
share.

Unlike architecture/empathy_map/scenario/pitch/hypotheses, this block is
NOT bilingual — it's generated in whichever single language the project's
`translation_key` implies, matching how it already worked before this
model existed.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bizstruct_domain.enums import MonetizationType


class BusinessModelOption(BaseModel):
    """One candidate business model for the idea."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str = Field(min_length=3, max_length=120)
    audience: str = Field(min_length=3, max_length=200, description="Target customer segment for this option.")
    value_proposition: str = Field(min_length=10, max_length=200)
    description: str = Field(
        min_length=20,
        max_length=600,
        description="What the model is and why it fits the idea's audience.",
    )
    monetization: MonetizationType
    key_metric: str = Field(
        min_length=2,
        max_length=100,
        description="The primary success metric for this monetization type, e.g. MRR/NRR for subscription, GMV/take rate for a marketplace, ACV for retainer_plus_saas.",
    )
    time_to_value: str = Field(
        min_length=2,
        max_length=100,
        description="How long before the customer sees the first result, e.g. '30 minutes', '2 weeks'.",
    )
    score: int = Field(ge=0, le=100, description="Viability score for this option.")
    score_rationale: str = Field(
        min_length=15,
        max_length=400,
        description="Why this score — what specifically makes the model strong or weak, not just a restatement of the number.",
    )


class ModelsOptions(BaseModel):
    """Output of the `models_options` stage: exactly 3 candidate business
    models, with at most one selected."""

    model_config = ConfigDict(extra="forbid")

    options: list[BusinessModelOption] = Field(min_length=3, max_length=3)
    selected_id: UUID | None = None

    @model_validator(mode="after")
    def _validate_selected_id(self) -> "ModelsOptions":
        if self.selected_id is not None:
            option_ids = {o.id for o in self.options}
            if self.selected_id not in option_ids:
                raise ValueError(
                    f"selected_id {self.selected_id} does not match any option id in {sorted(str(i) for i in option_ids)}"
                )
        return self
