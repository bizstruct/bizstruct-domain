"""Result schema for the `validate_model` side-channel task.

`validate_model` is NOT a generation-chain stage — it isn't in
`bizstruct_domain.chain.STAGES`. It evaluates a single business model
option a user is looking at (already generated, possibly hand-edited),
independent of the chain, and returns a score plus per-field critique.

The fields it can comment on are `BusinessModelOption`'s user-facing
fields (see `blocks/models_options.py`): `title`, `audience`,
`value_proposition`, `description`.

Known limitation, not fixed here: this task validates the model payload in
isolation — it doesn't read the project's idea or empathy_map from the
backend, so its critique has no context beyond the four fields it's given.
"""

from typing import Literal

from pydantic import ConfigDict, Field

from bizstruct_domain.sanitize import SanitizedModel

ValidatedField = Literal["title", "audience", "value_proposition", "description"]
FieldStatus = Literal["ok", "weak", "invalid"]
ValidationStatus = Literal["valid", "needs_revision", "invalid"]


class FieldFeedback(SanitizedModel):
    model_config = ConfigDict(extra="forbid")

    field: ValidatedField
    status: FieldStatus
    comment: str = Field(min_length=5, max_length=400)
    suggestion: str | None = Field(default=None, max_length=400)


class ValidateModelResult(SanitizedModel):
    """Output of the `validate_model` side-channel task."""

    model_config = ConfigDict(extra="forbid")

    status: ValidationStatus
    score: int = Field(ge=0, le=100)
    summary: str = Field(min_length=10, max_length=500)
    fields: list[FieldFeedback] = Field(min_length=1)
