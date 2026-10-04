"""Shared base class for every model in this package.

`SanitizedModel` strips NUL bytes and other non-printable control characters
from string input *before* Pydantic's own field constraints (`min_length`,
...) run.

Why this lives in the domain package rather than in bizstruct-ml or
bizstruct-be: the LLM occasionally emits `\\x00` in a text field. Pydantic
accepts it (it is a valid Python string), but PostgreSQL `text` columns
reject it (`asyncpg.exceptions.UntranslatableCharacterError`), which the
hook client and the queue worker then treat as a transient 5xx, masking a
permanent generation defect as a retryable one. Both consumers build these
same models, so sanitizing at the domain boundary protects both at once.

Every model in `bizstruct_domain.schemas` inherits `SanitizedModel`
(a guard test enforces it); new models get the protection by using it.

Identity is preserved: a value that needs no change is returned as the very
same object. That matters for enum members (a `StrEnum` member must stay the
member, not become a plain `str`, or `strict=True` validation rejects it) and
for enum-keyed dicts.
"""

import re
from typing import Any, TypeVar

from pydantic import BaseModel, field_validator

# C0 controls (0x00-0x1F) and DEL (0x7F), except \t (0x09), \n (0x0A) and
# \r (0x0D): legitimate whitespace in multi-line text. C1 controls
# (0x80-0x9F) are included: just as invalid in Postgres text columns and
# just as clearly not intentional LLM output.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def strip_control_chars(text: str) -> str:
    """Remove NUL and other control characters, keeping \\t, \\n and \\r.

    Idempotent. Returns `text` itself (same object) when there is nothing to
    strip, so str subclasses such as StrEnum members are left untouched.
    """
    if _CONTROL_CHARS_RE.search(text) is None:
        return text
    return _CONTROL_CHARS_RE.sub("", text)


def _sanitize_value(value: Any) -> Any:
    """Recurse into str / list / tuple / dict; rebuild a container only if at
    least one element (or dict key) actually changed."""
    if isinstance(value, str):
        return strip_control_chars(value)
    if isinstance(value, (list, tuple)):
        cleaned = [_sanitize_value(v) for v in value]
        if all(new is old for new, old in zip(cleaned, value)):
            return value
        return type(value)(cleaned) if isinstance(value, list) else tuple(cleaned)
    if isinstance(value, dict):
        cleaned_items = [(_sanitize_value(k), _sanitize_value(v)) for k, v in value.items()]
        if all(nk is ok and nv is ov for (nk, nv), (ok, ov) in zip(cleaned_items, value.items())):
            return value
        return dict(cleaned_items)
    return value


class SanitizedModel(BaseModel):
    """Base class for every model in `bizstruct_domain.schemas`. Nested
    models are covered by their own validators when pydantic builds them."""

    @field_validator("*", mode="before")
    @classmethod
    def _strip_control_characters(cls, value: Any) -> Any:
        return _sanitize_value(value)


_M = TypeVar("_M", bound=BaseModel)


class FromGeneratedMixin:
    """Adds `from_generated` to a persisted model that extends its generation model.

    Pure conversion, no I/O: the caller passes the system fields (ids, foreign
    keys, versions, sources). The result is built with `model_validate`, so
    every validator of the persisted model runs; a `ValidationError` is the
    signal that the generated content does not fit the system fields (e.g. a
    Pitch section without the matching input id).
    """

    @classmethod
    def from_generated(cls: type[_M], generated: BaseModel, **system_fields: Any) -> _M:
        return cls.model_validate({**generated.model_dump(), **system_fields})
