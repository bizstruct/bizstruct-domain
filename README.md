# bizstruct-domain

Single source of truth for the BizStruct domain model: Pydantic models for
each generated block, the shared enums they use, and the definition of the
generation-stage chain (order, dependencies, Basic vs. Pro availability).

`bizstruct-ml` and `bizstruct-be` depend on this package directly and use
its models as the Azure OpenAI `response_format` / API schema. `bizstruct-fe`
does not depend on it at runtime — it generates TypeScript types from the
JSON Schemas committed under [`schemas/`](schemas/).

**Pilot scope:** this initial cut implements only the `architecture` block,
as a template for the rest. Other blocks (`empathy_map`, `canvas`, `pitch`,
etc.) will be added the same way in follow-up PRs.

## Why Pydantic, not JSON Schema, as the source of truth

Two of the three consumers are Python, and the models are passed directly
into `beta.chat.completions.parse` as `response_format`. They also carry
cross-field validators (e.g. `pattern_subtype` must match `pattern`) that
JSON Schema alone can't express. JSON Schema is exported *from* the Pydantic
models for the frontend, not authored separately.

## Usage

### Python (bizstruct-ml, bizstruct-be)

```bash
pip install "bizstruct-domain @ git+https://github.com/bizstruct/bizstruct-domain@v0.1.0"
```

```python
from bizstruct_domain.blocks.architecture import Architecture
from bizstruct_domain.chain import topological_order

order = topological_order(pro=False)
```

### TypeScript (bizstruct-fe)

Generate types from the committed schemas with
[`json-schema-to-typescript`](https://github.com/bcherny/json-schema-to-typescript):

```bash
npx json-schema-to-typescript schemas/architecture.json > src/types/architecture.ts
```

`schemas/chain.json` is the serialized `STAGES` tuple, for building stage
navigation from the same source instead of a hand-maintained list.

## Development

```bash
pip install -e ".[dev]"
pytest
python scripts/export_schemas.py   # regenerate schemas/*.json; must be a no-op if code didn't change
```

CI fails if `scripts/export_schemas.py` produces a diff against the
committed `schemas/` — i.e. if the schemas fell out of sync with the models.

## Architecture decisions

See [`docs/adr/`](docs/adr/), starting with
[0001: generation stages](docs/adr/0001-generation-stages.md).

## Changing the domain model

Any change to enums, block models, or the stage chain goes through a PR
against this repository, followed by a new version tag. Consumers pin to a
tag; there's no "latest" floating dependency.
