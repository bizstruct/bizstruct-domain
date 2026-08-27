"""Shared base class for every domain block model — strips NUL bytes and
other non-printable control characters out of string input *before*
Pydantic's own field constraints (`min_length`, `max_length`, ...) run.

Why this lives here rather than in bizstruct-ml or bizstruct-be: the LLM
occasionally emits a `\\x00` in a text field. Pydantic validation doesn't
reject it (it's a valid Python string), but PostgreSQL's `text` columns do
(`asyncpg.exceptions.UntranslatableCharacterError`), which bizstruct-ml's
hook client and bizstruct-be's queue worker both then have to treat as a
transient `5xx` — masking a permanent generation defect as a retryable
one. Sanitizing at the domain-model boundary fixes it in both directions
at once: bizstruct-ml's generation output (`ModelsOptions.model_validate`
etc. in `generators/base.py`) and bizstruct-be's hook validation
(`CanvasGenerated`/`WhatIfGenerated`/... in `app/routers/internal.py`)
both construct these same domain models, so both get the same protection
for free — no separate fix needed in either consuming repo.

Every block model in `bizstruct_domain.blocks` inherits `SanitizedModel`
instead of `pydantic.BaseModel`. New block models get this automatically
by doing the same — nothing else to opt in.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, field_validator

# Control characters to strip: C0 controls (0x00-0x1F) and DEL (0x7F),
# except \t (0x09), \n (0x0A), \r (0x0D) — legitimate whitespace that
# shows up in real multi-line rationale/description text. C1 controls
# (0x80-0x9F) are included too since they're just as invalid in Postgres
# text columns and just as clearly not intentional LLM output.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def strip_control_chars(text: str) -> str:
    """Removes NUL bytes and other non-printable control characters from a
    string, leaving \\t/\\n/\\r untouched. Idempotent."""
    return _CONTROL_CHARS_RE.sub("", text)


def _sanitize_value(value: Any) -> Any:
    """Recurses into list/tuple/dict so a field typed as e.g. list[str] or
    dict[str, str] is covered directly by this model's own validator, not
    just by a nested model's. Nested BaseModel instances are NOT recursed
    into here — pydantic constructs those from the (already-recursed) raw
    dict/list this returns, and if the nested model is itself a
    SanitizedModel subclass (the expectation for every block model), its
    own field_validator runs on its own fields when pydantic builds it."""
    if isinstance(value, str):
        return strip_control_chars(value)
    if isinstance(value, list):
        return [_sanitize_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_value(v) for v in value)
    if isinstance(value, dict):
        return {_sanitize_value(k): _sanitize_value(v) for k, v in value.items()}
    return value


class SanitizedModel(BaseModel):
    """Base class for every bizstruct_domain block model. Strips control
    characters from string input before any other field validation
    (min_length included) runs — see module docstring."""

    @field_validator("*", mode="before")
    @classmethod
    def _strip_control_characters(cls, value: Any) -> Any:
        return _sanitize_value(value)
