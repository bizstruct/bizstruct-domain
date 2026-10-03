import enum
import importlib
import inspect
import pkgutil

import pytest
from pydantic import BaseModel

import bizstruct_domain.schemas as schemas_pkg


def _defined_public_types() -> dict[str, type]:
    found: dict[str, type] = {}
    for info in pkgutil.iter_modules(schemas_pkg.__path__):
        module = importlib.import_module(f"{schemas_pkg.__name__}.{info.name}")
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module.__name__ or name.startswith("_"):
                continue
            if issubclass(obj, (BaseModel, enum.Enum)) or name == "ConsistencyRule":
                found[name] = obj
    return found


def test_all_names_resolve():
    for name in schemas_pkg.__all__:
        assert hasattr(schemas_pkg, name), name


def test_all_has_no_duplicates():
    assert len(schemas_pkg.__all__) == len(set(schemas_pkg.__all__))


def test_every_public_model_and_enum_is_exported():
    missing = sorted(set(_defined_public_types()) - set(schemas_pkg.__all__))
    assert not missing, f"defined in schemas/ but not exported: {missing}"


@pytest.mark.parametrize("name", sorted(_defined_public_types()))
def test_export_is_the_defining_object(name):
    assert getattr(schemas_pkg, name) is _defined_public_types()[name]


def test_registries_and_generation_contract_are_exported():
    from bizstruct_domain.schemas import (
        CONSISTENCY_RULES,
        JUDGE_CHECKS,
        STAGE_REGISTRY,
        CanvasGenerated,
        StageRegistry,
    )

    assert isinstance(STAGE_REGISTRY, StageRegistry)
    assert CONSISTENCY_RULES and JUDGE_CHECKS
    assert CanvasGenerated.__name__ == "CanvasGenerated"
