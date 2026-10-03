import pytest
from pydantic import Field, ValidationError

from bizstruct_domain.schemas import (
    JUDGE_CHECKS,
    STAGE_REGISTRY,
    CanvasCardDraft,
    SanitizedModel,
    Stage,
    StageRegistry,
    strip_control_chars,
)
from bizstruct_domain.schemas.fields import _sanitize_value
from test_schemas_guards import MODELS  # noqa: E402  (shared model discovery)

# Static config models are NOT exempt: the allowlist is deliberately empty.
NOT_SANITIZED: set[type] = set()


class Holder(SanitizedModel):
    stage: Stage
    by_stage: dict[Stage, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)
    pair: tuple[str, str] | None = None


# ------------------------------------------------------------ strip_control_chars


def test_removes_nul_byte():
    assert strip_control_chars("before\x00after") == "beforeafter"


def test_removes_other_c0_controls():
    assert strip_control_chars("a\x01b\x08c\x0bd\x0ce\x1ff") == "abcdef"


def test_removes_del_and_c1_controls():
    assert strip_control_chars("a\x7fb\x9fc") == "abc"


def test_preserves_tab_newline_carriage_return():
    text = "line one\nline two\ttabbed\rreturn"
    assert strip_control_chars(text) == text
    assert strip_control_chars(text) is text


def test_is_idempotent():
    once = strip_control_chars("a\x00b\nc")
    assert strip_control_chars(once) == once == "ab\nc"


def test_clean_text_is_returned_as_the_same_object():
    text = "Цілком нормальний текст українською and in English too."
    assert strip_control_chars(text) is text


def test_str_enum_member_is_returned_unchanged():
    assert strip_control_chars(Stage.BRIEF) is Stage.BRIEF


# ------------------------------------------------------------ identity (strict mode)


def test_enum_field_and_enum_keyed_dict_survive_strict_validation_with_identity():
    model = Holder.model_validate(
        {"stage": Stage.CANVAS, "by_stage": {Stage.BRIEF: "a", Stage.PITCH: "b"}}, strict=True
    )
    assert model.stage is Stage.CANVAS
    keys = list(model.by_stage)
    assert keys[0] is Stage.BRIEF and keys[1] is Stage.PITCH


def test_enum_identity_survives_lax_validation_too():
    model = Holder(stage=Stage.CANVAS, by_stage={Stage.BRIEF: "a"})
    assert model.stage is Stage.CANVAS
    assert next(iter(model.by_stage)) is Stage.BRIEF


def test_clean_containers_are_returned_as_the_same_objects():
    tags = ["a", "b"]
    labels = {"k": "v"}
    pair = ("x", "y")
    assert _sanitize_value(tags) is tags
    assert _sanitize_value(labels) is labels
    assert _sanitize_value(pair) is pair
    assert _sanitize_value(5) == 5


def test_container_is_rebuilt_only_when_something_changed():
    tags = ["a", "b\x00"]
    assert _sanitize_value(tags) == ["a", "b"]
    assert _sanitize_value(tags) is not tags
    assert tags == ["a", "b\x00"]  # input not mutated
    assert _sanitize_value(("x", "y\x00")) == ("x", "y")
    assert _sanitize_value({"k\x00": "v"}) == {"k": "v"}


def test_dirty_dict_with_enum_keys_keeps_clean_keys_as_enum_members():
    cleaned = _sanitize_value({Stage.BRIEF: "a\x00b"})
    assert cleaned == {Stage.BRIEF: "ab"}
    assert next(iter(cleaned)) is Stage.BRIEF


# ------------------------------------------------------------ behaviour on models


def test_nul_byte_stripped_from_direct_field():
    assert CanvasCardDraft(text="Weekly box\x00 of produce").text == "Weekly box of produce"


def test_whitespace_survives_on_a_model_field():
    text = "line one\n\tline two\r\n"
    assert CanvasCardDraft(text=text).text == text


def test_nul_stripped_inside_nested_list_of_models():
    from bizstruct_domain.schemas import CanvasGenerated

    payload = {
        "sections": {
            name: [{"text": "ok\x00 one"}, {"text": "fine two"}]
            for name in ("value_propositions", "customer_segments", "channels", "customer_relationships",
                         "revenue_streams", "key_resources", "key_activities", "key_partnerships",
                         "cost_structure")
        }
    }
    generated = CanvasGenerated.model_validate(payload)
    assert generated.sections.channels[0].text == "ok one"
    assert generated.sections.channels[1].text == "fine two"


def test_sanitizing_runs_before_min_length():
    # CanvasCardDraft.text has min_length=1: a lone NUL is empty once stripped.
    with pytest.raises(ValidationError):
        CanvasCardDraft(text="\x00")


def test_list_and_dict_of_plain_strings_sanitized():
    model = Holder(stage=Stage.BRIEF, tags=["clean", "dirty\x00tag"], labels={"key\x00": "va\x00lue"})
    assert model.tags == ["clean", "dirtytag"]
    assert model.labels == {"key": "value"}


# ------------------------------------------------------------ real config models


@pytest.mark.parametrize("check", JUDGE_CHECKS, ids=lambda c: c.id)
def test_judge_check_instructions_are_fixed_points(check):
    assert strip_control_chars(check.instruction) == check.instruction
    assert strip_control_chars(check.instruction) is check.instruction


def test_stage_registry_survives_a_model_dump_round_trip():
    rebuilt = StageRegistry.model_validate(STAGE_REGISTRY.model_dump())
    assert rebuilt == STAGE_REGISTRY


def test_stage_registry_survives_a_strict_round_trip_with_identity():
    rebuilt = StageRegistry.model_validate(STAGE_REGISTRY.model_dump(), strict=True)
    assert rebuilt == STAGE_REGISTRY
    assert all(key is definition.id for key, definition in rebuilt.stages.items())


# ------------------------------------------------------------ guard


@pytest.mark.parametrize("model", MODELS, ids=lambda m: m.__name__)
def test_every_model_in_schemas_inherits_sanitized_model(model):
    if model in NOT_SANITIZED:
        pytest.skip("explicitly allowlisted")
    assert issubclass(model, SanitizedModel), f"{model.__name__} must inherit SanitizedModel"


def test_allowlist_is_empty():
    assert NOT_SANITIZED == set()
