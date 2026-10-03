"""Generic guards run over every model in `bizstruct_domain.schemas`.

They exist to catch the mistakes review kept finding by hand: flat-list
examples on list fields, examples naming enum members that don't exist or
that break their own constraints, and models whose JSON Schema can't be built.
"""

import importlib
import inspect
import pkgutil
from typing import Annotated, Any

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

import bizstruct_domain.schemas as schemas_pkg


def _all_models() -> list[type[BaseModel]]:
    models: dict[str, type[BaseModel]] = {}
    for info in pkgutil.iter_modules(schemas_pkg.__path__):
        module = importlib.import_module(f"{schemas_pkg.__name__}.{info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseModel) and obj.__module__.startswith(schemas_pkg.__name__):
                models[f"{obj.__module__}.{obj.__qualname__}"] = obj
    return sorted(models.values(), key=lambda m: (m.__module__, m.__qualname__))


MODELS = _all_models()


def _model_ids(model: type[BaseModel]) -> str:
    return f"{model.__module__.rsplit('.', 1)[-1]}.{model.__name__}"


def _field_cases() -> list[Any]:
    cases = []
    for model in MODELS:
        for name, info in model.model_fields.items():
            for index, example in enumerate(info.examples or []):
                cases.append(
                    pytest.param(model, name, example, id=f"{_model_ids(model)}.{name}[{index}]")
                )
    return cases


def _model_instances(value: Any) -> list[BaseModel]:
    """Model instances found in an example, however deeply lists/dicts nest."""
    if isinstance(value, BaseModel):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [m for v in value for m in _model_instances(v)]
    if isinstance(value, dict):
        return [m for v in value.values() for m in _model_instances(v)]
    return []


def test_discovery_finds_the_schema_models():
    names = {m.__name__ for m in MODELS}
    # Spot checks across every module, including the generation-time models.
    assert {
        "Brief", "EmpathyMap", "CustomerScenario", "Ideation", "Patterns", "Canvas",
        "CanvasGenerated", "Swot", "Errc", "Storytelling", "FutureScenario", "Pitch",
        "TeamInfo", "BusinessCase", "EnvironmentScan", "StageDefinition", "StageRegistry",
        "ConsistencyViolation", "ConsistencyReport", "RuleInput", "JudgeCheck",
    } <= names
    assert len(MODELS) >= 40


@pytest.mark.parametrize(("model", "field_name", "example"), _field_cases())
def test_field_example_validates_against_its_own_field(model, field_name, example):
    """Each example must satisfy the field's annotation and constraints.

    A flat list on a `list[...]` field fails here (the example "a" is not a
    list), as does an example outside ge/le/min_length/max_length.
    """
    info = model.model_fields[field_name]
    annotation = Annotated[(info.annotation, *info.metadata)] if info.metadata else info.annotation
    try:
        TypeAdapter(annotation).validate_python(example)
    except ValidationError as exc:
        pytest.fail(f"{_model_ids(model)}.{field_name} example {example!r} is invalid:\n{exc}")


@pytest.mark.parametrize(("model", "field_name", "example"), _field_cases())
def test_model_instances_in_examples_pass_their_own_validators(model, field_name, example):
    """Instances built at import already ran validators once; re-validating
    their dumped data also catches examples that only pass because an
    instance was constructed with validation bypassed."""
    for instance in _model_instances(example):
        type(instance).model_validate(instance.model_dump(mode="python"))


@pytest.mark.parametrize("model", MODELS, ids=_model_ids)
def test_json_schema_can_be_generated(model):
    schema = model.model_json_schema()
    assert schema["type"] == "object"
    assert schema["properties"]
