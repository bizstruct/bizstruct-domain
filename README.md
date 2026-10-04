# bizstruct-domain

Single source of truth for the BizStruct domain model: Pydantic models for
each generated artifact, the shared enums they use, the 13-stage generation
graph (order and dependencies), the stage state machine, and the
cross-artifact consistency rules.

`bizstruct-ml` and `bizstruct-be` depend on this package directly and use
its models as the Azure OpenAI `response_format` / API schema. `bizstruct-fe`
does not depend on it at runtime — it generates TypeScript types from the
JSON Schemas committed under [`schemas/`](schemas/).

The package describes the shape of one generation pass. Multiplicity (how
many instances of a stage a project has), the iteration count and stop rule
of the Canvas -> SWOT -> ERRC loop, product tiers, stage titles and user
gates are the consumers' concern — see
[ADR-0009](docs/adr/0009-stage-graph-and-schemas.md).

## Layout

```
src/bizstruct_domain/
  __init__.py        re-exports schemas + the stage machine API; __version__
  stage_machine.py   StageStatus transitions, ready_stages, dependents_of
  schemas/
    enums.py         every enum (Stage, CanvasSection, StageStatus, ...)
    fields.py        SanitizedModel: base of every model (strips control chars)
    stage_definition.py, stage_registry.py, chain.py
                     StageDefinition, StageRegistry, STAGE_REGISTRY (13 stages)
    brief.py, empathy_map.py, customer_scenario.py, ideation.py, pattern.py,
    canvas.py, swot.py, errc.py, storytelling.py, future_scenario.py,
    pitch.py, optional_inputs.py (TeamInfo, BusinessCase, EnvironmentScan)
                     artifact models, one module per stage
    consistency.py   cross-artifact rules and judge-check declarations
    generation.py    GENERATION_CONTRACTS: what the LLM writes, per stage (ADR-0010)
    wire.py          be <-> ml wire contract: rows, messages, results, row logic (ADR-0011)
    validate_model.py  side-channel result contract (not a stage)
scripts/export_schemas.py   regenerates schemas/*.json
schemas/                    generated JSON Schemas (committed)
```

Import everything from `bizstruct_domain` (or `bizstruct_domain.schemas`); the
module layout above is not a public contract.

## Why Pydantic, not JSON Schema, as the source of truth

Two of the three consumers are Python, and the models are passed directly
into `beta.chat.completions.parse` as `response_format`. They also carry
cross-field validators (e.g. a pattern's `subtype` must match its `pattern`)
that JSON Schema alone can't express. Such validator-only constraints are
invisible to the generator; they are listed in
[ADR-0009](docs/adr/0009-stage-graph-and-schemas.md). JSON Schema is exported *from* the Pydantic
models for the frontend, not authored separately.

## Usage

### Python (bizstruct-ml, bizstruct-be)

```bash
pip install "bizstruct-domain @ git+https://github.com/bizstruct/bizstruct-domain@v0.1.0"
```

```python
from bizstruct_domain import Patterns, STAGE_REGISTRY

order = STAGE_REGISTRY.topological_order()
```

### TypeScript (bizstruct-fe)

Generate types from the committed schemas with
[`json-schema-to-typescript`](https://github.com/bcherny/json-schema-to-typescript):

```bash
npx json-schema-to-typescript schemas/patterns.json > src/types/patterns.ts
```

`schemas/stages.json` is the serialized `STAGE_REGISTRY` (topological order, with
`depends_on` / `optional_depends_on`), for building stage navigation from the
same source instead of a hand-maintained list.

## Wire contract (bizstruct-be <-> bizstruct-ml)

[ADR-0011](docs/adr/0011-wire-contract.md). The unit of work is a **stage row**: be
creates rows, assigns row ids, and records in `refs` which rows each row draws from.
ml receives a `QueueMessage`, reads the `ProjectSnapshot`, generates, checks
consistency and answers with a `StageResult`; **ml never writes statuses**, be applies
the stage-machine transitions. All wire models are snake_case, ids are `str`, and
every model inherits `SanitizedModel`. JSON Schemas: `queue_message.json`,
`stage_result.json`, `project_snapshot.json`, `stage_event.json`.

| Model | Purpose |
|---|---|
| `ArtifactType` (14), `ARTIFACT_STAGE`, `ARTIFACT_MODELS` | the persisted artifacts, their stage and model |
| `ArtifactRecord` | `id`, `type`, `data` of one artifact on the wire |
| `StageRow` | row state: `id`, `stage`, `instance_index`, `status`, `attempt_id`, `refs`, `artifacts`, `consistency`, `retry_count`, `error_code`, `error`, timestamps |
| `ProjectSnapshot` | `project_id`, `idea`, `language`, `enabled_optional`, `rows` (be -> ml) |
| `RowTarget`, `QueueMessage` | `project_id`, `language`, `targets` (>= 1; the pipeline sends one) |
| `StageFailure`, `StageResult` | ml -> be: `success` needs artifacts, `failed` needs an error; carries the final `ConsistencyReport` |
| `StageEvent` | be -> fe pubsub after a transition |
| `CanvasRowSpec` | one canvas row to create, from a `Patterns` group |

| Function (pure, no I/O) | Purpose |
|---|---|
| `derive_artifact_id(stage_row_id, artifact_type, index=0)` | deterministic uuid5 artifact id, so regeneration keeps foreign keys valid; `index` is the canvas version for `canvas`/`swot_errc_cycle` |
| `validate_row_refs(stage, refs)` | keys must be dependencies; every hard dependency non-empty |
| `ready_rows(rows, enabled_optional)` | rows that can start now (per row, not per type); an enabled optional dependency that is not `DONE` blocks its consumer; a `PENDING` row of a stage without a generation contract (`team_info`) is never ready |
| `dependent_rows(row_id, rows)` | transitive dependents through `refs`, to mark stale rows |
| `project_status(rows, enabled_optional)` | `completed` / `failed` / `running` |
| `canvas_rows_for(patterns)` | one `CanvasRowSpec` per group |
| `row_of_artifact(rows, artifact_id)` | the row holding an artifact |
| `parse_artifact(record)` | validate `record.data` with the persisted model |

`team_info` is user input: be creates its row directly in `DONE` when the user submits.

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
[0009: stage graph, schemas and consistency](docs/adr/0009-stage-graph-and-schemas.md)
for the current stage graph (it supersedes
[0008](docs/adr/0008-bmg-domain-rewrite.md)).

## Changing the domain model

Any change to enums, artifact models, or the stage graph goes through a PR
against this repository, followed by a new version tag. Consumers pin to a
tag; there's no "latest" floating dependency.
