"""Guards against presentation/UI concerns leaking into domain models.

Three times running, an ML generator produced a UI-presentation attribute
alongside domain data (colors/icons, `highlight`, `initials`), each caught
by hand after the fact. This makes that class of defect fail automatically:
it walks every field of every model in `schemas/` and fails on a field name
that is presentation logic, not domain data (a color, an icon, a UI variant,
a layout position).

If a blacklisted word is ever legitimately domain data, make that decision
explicitly by editing BLACKLIST/ALLOWED_FIELDS in a PR.

Matching is per word: a name is split on underscores and camelCase
boundaries (`icon_key` -> {icon, key}) and each word is compared exactly.
A raw substring test is too blunt: `value_proposition` contains "position".
"""

import re

import pytest
from pydantic import BaseModel

from test_schemas_guards import MODELS

BLACKLIST = {
    "color", "colour", "icon", "highlight", "initials", "variant",
    "class", "css", "style", "theme", "badge", "emoji", "avatar",
    "order", "position",
}

# (model name, field name) pairs that are legitimate domain data.
ALLOWED_FIELDS: set[tuple[str, str]] = set()


def _words(field_name: str) -> set[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", field_name)
    return {w.lower() for w in spaced.split("_") if w}


def test_words_splits_snake_and_camel_case():
    assert _words("icon_key") == {"icon", "key"}
    assert _words("mainIcon") == {"main", "icon"}
    assert "position" not in _words("value_proposition")


@pytest.mark.parametrize("model", MODELS, ids=lambda m: m.__name__)
def test_no_presentation_fields(model: type[BaseModel]):
    violations = [
        name
        for name in model.model_fields
        if _words(name) & BLACKLIST and (model.__name__, name) not in ALLOWED_FIELDS
    ]
    assert not violations, (
        f"{model.__name__}: {violations} look like presentation logic, not domain data. "
        "If legitimate, add the pair to ALLOWED_FIELDS."
    )
