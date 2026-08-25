# 0001. Generation stages and their order

## Status

Accepted

## Context

The business-model generation pipeline is a sequence of stages, each an LLM
call that (for most stages) receives already-generated blocks as context.
Because generated content is fed forward into later prompts, the *order* of
stages is not just a UX/navigation concern — it changes the substance of what
gets generated, not merely the sequence in which it's displayed.

Before this repository existed, the order was duplicated and had drifted:

- **bizstruct-be** (backend): `models → canvas → empathy → hypotheses →
  pitch → scenario → what_if → architecture`
- **bizstruct-fe** (frontend): `empathy → scenario → what_if → architecture →
  canvas → pitch → hypotheses`

These two orders are close to mirror images of each other, and neither
matches the methodology described in Osterwalder & Pigneur, *Business Model
Generation*, or the referenced companion works (*Value Proposition Design*,
*Testing Business Ideas*, *Blue Ocean Strategy*).

## Decision

Fix the stage order to:

`brief → empathy_map → value_map → models_options → canvas → architecture →
what_if → hypotheses → scenario → pitch`

(with `environment_scan` and `assessment` as Pro-only side branches off
`empathy_map`/`canvas` respectively — see the dependency table in
`chain.py`).

Rationale for the non-obvious dependencies:

- **`empathy_map` before `canvas`** — the value proposition must be grounded
  in customer pains/gains (Value Proposition Canvas methodology). Generating
  it earlier is a deliberate methodological inversion relative to a
  "canvas-first" reading of BMG.
- **`models_options` before `canvas`** — the Revenue Streams and Cost
  Structure blocks of the canvas depend on which monetization model was
  chosen; generating the canvas first would make those two building blocks
  ungrounded guesses.
- **`architecture` after `canvas`** — the epicenter, by definition, names
  which canvas building block is the driver of change. Classifying it
  without a canvas to point at is not meaningful. (The current frontend
  generates `architecture` *before* `canvas`, which is methodologically
  incorrect.)
- **`hypotheses` after `what_if`** — the set of risky assumptions changes
  once an ERRC alternative has been applied to the model; generating
  hypotheses before that point risks testing assumptions that no longer
  apply.
- **`scenario` depends only on `empathy_map`, `value_map`, `models_options`**
  — it is the one stage that can run in parallel with `architecture`/
  `what_if`, since it doesn't need the canvas or its downstream blocks.
- **`environment_scan` and `assessment` are Pro-only** — both require
  external data lookups and/or feedback loops (returning to a prior stage
  to revise it based on new findings), which the linear Basic pipeline
  doesn't support.

## Consequences

- The ML worker must read stage order from `chain.py` (via
  `topological_order()`), not from a local constant.
- The frontend builds its stage navigation from `schemas/chain.json`,
  generated from the same `STAGES` tuple.
- Adding, removing, or reordering a stage is a PR against this repository,
  tagged with a new version, not a change made independently in any
  consumer.

## Alternatives considered

- **Keep the current backend order.** Rejected — it contradicts the
  methodology (see `architecture`/`canvas` and `models_options`/`canvas`
  arguments above).
- **Make the order configurable per project/deployment.** Rejected — it
  would make it impossible to compare Basic vs. Pro generation runs in an
  experiment, since they'd no longer share a common causal structure.
