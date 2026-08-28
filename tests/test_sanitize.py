import pytest
from pydantic import Field, ValidationError

from bizstruct_domain.blocks.empathy_map import EmpathyItem, EmpathyMap
from bizstruct_domain.sanitize import SanitizedModel, strip_control_chars


# ── strip_control_chars ──────────────────────────────────────────────────


def test_strip_control_chars_removes_nul_byte():
    assert strip_control_chars("before\x00after") == "beforeafter"


def test_strip_control_chars_removes_other_c0_controls():
    assert strip_control_chars("a\x01b\x08c\x0bd\x0ce\x1ff") == "abcdef"


def test_strip_control_chars_removes_c1_controls():
    assert strip_control_chars("a\x7fb\x9fc") == "abc"


def test_strip_control_chars_preserves_whitespace():
    text = "line one\nline two\ttabbed\rreturn"
    assert strip_control_chars(text) == text


def test_strip_control_chars_is_idempotent():
    text = "a\x00b\nc"
    once = strip_control_chars(text)
    twice = strip_control_chars(once)
    assert once == twice == "ab\nc"


def test_strip_control_chars_noop_on_clean_text():
    text = "Цілком нормальний текст українською and in English too."
    assert strip_control_chars(text) == text


# ── SanitizedModel: direct string field ──────────────────────────────────


def test_nul_byte_stripped_from_direct_field():
    item = EmpathyItem(id=1, text="Sufficiently long text\x00 with a nul")
    assert "\x00" not in item.text
    assert item.text == "Sufficiently long text with a nul"


def test_newline_not_stripped_from_direct_field():
    text = "A two-line description\nsecond line here for length"
    item = EmpathyItem(id=1, text=text)
    assert item.text == text


# ── SanitizedModel: nested models and lists of models ────────────────────


def _item(i: int, *, nul: bool = False) -> dict:
    text = f"A sufficiently long item in English number {i}"
    if nul:
        text = text[:5] + "\x00" + text[5:]
    return {"id": i, "text": text}


def test_nul_byte_stripped_inside_nested_list_of_models():
    kwargs = {
        section: [_item(1, nul=True), _item(2, nul=True), _item(3)]
        for section in ("says", "thinks", "does", "feels", "pains", "gains")
    }
    model = EmpathyMap(**kwargs)
    assert "\x00" not in model.says[0].text
    assert "\x00" not in model.says[1].text
    # untouched item still intact
    assert model.says[2].text == _item(3)["text"]


# ── Sanitization happens before min_length is checked ────────────────────


def test_sanitize_runs_before_min_length_check():
    # 10 chars of raw input, but 9 of them are NUL bytes — after
    # sanitization only 1 real character remains, well under min_length=10.
    # If min_length were checked against the *raw* (unsanitized) length,
    # this would incorrectly pass.
    raw = "a" + "\x00" * 9
    assert len(raw) == 10
    with pytest.raises(ValidationError):
        EmpathyItem(id=1, text=raw)


def test_sanitize_then_min_length_pass_when_cleaned_text_is_long_enough():
    # Raw length is inflated by NUL bytes but the real content alone
    # already clears min_length=10 once they're stripped.
    raw = "Sufficiently long\x00\x00\x00 text"
    cleaned = strip_control_chars(raw)
    assert len(cleaned) >= 10
    item = EmpathyItem(id=1, text=raw)
    assert item.text == cleaned


# ── General mechanism: list[str] / dict[str, str] fields (no existing
# block currently has these shapes, but new ones might) ──────────────────


class _SyntheticModel(SanitizedModel):
    tags: list[str] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)


def test_list_of_plain_strings_sanitized():
    model = _SyntheticModel(tags=["clean", "dirty\x00tag"], labels={})
    assert model.tags == ["clean", "dirtytag"]


def test_dict_of_plain_strings_sanitized():
    model = _SyntheticModel(tags=[], labels={"key\x00": "va\x00lue"})
    assert model.labels == {"key": "value"}
