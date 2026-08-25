"""Guards against presentation/UI concerns leaking into domain models.

Three times running, an ML generator produced a UI-presentation attribute
alongside domain data: colors/icons in what_if (still unfixed), `highlight`
in scenario, `initials` in scenario. Each was caught by hand, after the
fact, once someone noticed the frontend had to derive the same thing anyway.
This test makes that class of defect fail automatically instead: it walks
every field of every block model (recursing into nested domain models) and
fails if it finds a field name that's presentation logic, not domain data
— a color, an icon, a UI variant, a layout position.

If a field on this blacklist is ever legitimately domain data, that's a
decision made explicitly by editing BLACKLIST in a PR — not by silently
adding the field and letting this test rot.

Matching is per-word, not a raw substring test on the whole field name: a
field name is split on underscores and camelCase boundaries (`icon_key` ->
["icon", "key"], `mainIcon` -> ["main", "icon"]) and each word is checked
against BLACKLIST exactly. This is deliberate on both sides — a compound
name like `icon_key` needs to be caught by the `icon` entry without every
possible compound spelled out (icon_key itself was missed once already, in
scenario.TimelineStep, because a naive exact-match on the *whole* field
name wouldn't have caught it), but a raw substring test on the whole name
is too blunt: `value_proposition` contains "position" as a literal
substring and would false-positive against the `position` entry despite
being legitimate domain data.
"""

import re
import typing

import pytest
from pydantic import BaseModel

from bizstruct_domain.blocks.architecture import Architecture
from bizstruct_domain.blocks.empathy_map import EmpathyMap
from bizstruct_domain.blocks.scenario import Scenario
from bizstruct_domain.blocks.pitch import Pitch
from bizstruct_domain.blocks.hypotheses import Hypotheses
from bizstruct_domain.blocks.models_options import ModelsOptions
from bizstruct_domain.blocks.canvas import CanvasGenerated

BLACKLIST = {
    "color", "colour", "icon", "highlight", "initials", "variant",
    "class", "css", "style", "theme", "badge", "emoji", "avatar",
    "order", "position",
}

BLOCK_MODELS: dict[str, type[BaseModel]] = {
    "architecture": Architecture,
    "empathy_map": EmpathyMap,
    "scenario": Scenario,
    "pitch": Pitch,
    "hypotheses": Hypotheses,
    "models_options": ModelsOptions,
    # CanvasGenerated, not Canvas — same fields, checking the stricter
    # subclass covers the base class's fields too.
    "canvas": CanvasGenerated,
}


def _words(field_name: str) -> set[str]:
    """Split a field name into lowercase words on underscores and camelCase
    boundaries, e.g. 'icon_key' / 'iconKey' -> {'icon', 'key'}."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", field_name)
    return {w.lower() for w in spaced.split("_") if w}


def _nested_models(annotation: object) -> list[type[BaseModel]]:
    """Extract any BaseModel subclasses reachable from a field annotation
    (directly, through Optional/Union, or through list/dict containers)."""
    found: list[type[BaseModel]] = []
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        found.append(annotation)
        return found
    for arg in typing.get_args(annotation):
        found.extend(_nested_models(arg))
    return found


def _walk(model: type[BaseModel], path: str, seen: set[type[BaseModel]], violations: list[str]) -> None:
    if model in seen:
        return
    seen.add(model)
    for field_name, field_info in model.model_fields.items():
        field_path = f"{path}.{field_name}"
        if _words(field_name) & BLACKLIST:
            violations.append(
                f"{field_path} (on {model.__name__}) — '{field_name}' looks like presentation "
                f"logic (matches blacklist), not domain data. If this is a legitimate exception, "
                f"add it explicitly to BLACKLIST's allowed exceptions in this test, don't just "
                f"leave it — see the module docstring for why."
            )
        for nested in _nested_models(field_info.annotation):
            _walk(nested, field_path, seen, violations)


@pytest.mark.parametrize("name,model", BLOCK_MODELS.items())
def test_no_presentation_fields_in_block_model(name: str, model: type[BaseModel]) -> None:
    violations: list[str] = []
    _walk(model, name, set(), violations)
    assert not violations, "Presentation fields found in domain model(s):\n" + "\n".join(violations)
