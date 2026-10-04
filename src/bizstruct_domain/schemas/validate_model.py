"""Result schema for the `validate_model` side-channel task.

`validate_model` is NOT a stage of the graph (it is not in `STAGE_REGISTRY`).
It evaluates one business model option a user is looking at (already
generated, possibly hand-edited), independent of the stage graph, and
returns a score plus per-field critique.

The feature currently has no subject model in this package: the
`BusinessModelOption` / `models_options` stage it was written for is gone
from the stage graph (ADR-0009). The contract is kept as is, with
`FieldFeedback.field` an open `str`, until a product decision says what
`validate_model` should validate.
"""

from typing import Literal

from pydantic import ConfigDict, Field

from .fields import SanitizedModel

FieldStatus = Literal["ok", "weak", "invalid"]
ValidationStatus = Literal["valid", "needs_revision", "invalid"]


class FieldFeedback(SanitizedModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(
        ...,
        min_length=1,
        description="Name of the field of the evaluated option this feedback is about.",
        examples=["value_proposition"],
    )
    status: FieldStatus = Field(
        ...,
        description="Verdict for this field.",
        examples=["weak"],
    )
    comment: str = Field(
        ...,
        min_length=5,
        max_length=400,
        description="What is good or wrong with this field.",
        examples=["The value proposition does not name a concrete customer pain."],
    )
    suggestion: str | None = Field(
        default=None,
        max_length=400,
        description="A concrete rewrite or fix, if one is useful.",
        examples=["State which pain is removed and for whom."],
    )


class ValidateModelResult(SanitizedModel):
    """Output of the `validate_model` side-channel task."""

    model_config = ConfigDict(extra="forbid")

    status: ValidationStatus = Field(
        ...,
        description="Overall verdict.",
        examples=["needs_revision"],
    )
    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Overall quality score, 0 (unusable) to 100 (excellent).",
        examples=[62],
    )
    summary: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Short overall assessment.",
        examples=["Clear audience, but the value proposition is generic."],
    )
    fields: list[FieldFeedback] = Field(
        ...,
        min_length=1,
        description="Per-field feedback, at least one entry.",
        examples=[[FieldFeedback(field="value_proposition", status="weak", comment="Too generic to evaluate.")]],
    )
