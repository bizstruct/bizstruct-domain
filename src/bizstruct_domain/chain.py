"""Generation-chain definition: stage order, dependencies, and DAG validation.

This is the formalization of docs/adr/0001-generation-stages.md. Consumers
(bizstruct-ml, bizstruct-be, bizstruct-fe via schemas/chain.json) must read
the stage order from here rather than hardcoding it locally.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict


class StageMode(str, Enum):
    """Which generation mode a stage is available in."""

    BOTH = "both"  # available in both Basic and Pro (agentic) modes
    PRO_ONLY = "pro"  # only in the agentic Pro mode


class Stage(BaseModel):
    """A single step of the business-model generation pipeline."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    title_uk: str
    depends_on: tuple[str, ...]
    mode: StageMode
    requires_user_gate: bool
    source: str


_BOTH_STAGES_BEFORE_PITCH = (
    "brief",
    "empathy_map",
    "value_map",
    "models_options",
    "canvas",
    "architecture",
    "what_if",
    "hypotheses",
    "scenario",
)

STAGES: tuple[Stage, ...] = (
    Stage(
        id="brief",
        title_uk="Нормалізація ідеї",
        depends_on=(),
        mode=StageMode.BOTH,
        requires_user_gate=False,
        source="-",
    ),
    Stage(
        id="empathy_map",
        title_uk="Карта емпатії",
        depends_on=("brief",),
        mode=StageMode.BOTH,
        requires_user_gate=False,
        source="BMG, Customer Insights",
    ),
    Stage(
        id="environment_scan",
        title_uk="Аналіз середовища (4 сили)",
        depends_on=("brief", "empathy_map"),
        mode=StageMode.PRO_ONLY,
        requires_user_gate=False,
        source="BMG, Business Model Environment",
    ),
    Stage(
        id="value_map",
        title_uk="Ціннісна пропозиція",
        depends_on=("empathy_map",),
        mode=StageMode.BOTH,
        requires_user_gate=False,
        source="Value Proposition Design",
    ),
    Stage(
        id="models_options",
        title_uk="Варіанти монетизації",
        depends_on=("empathy_map", "value_map"),
        mode=StageMode.BOTH,
        requires_user_gate=True,
        source="BMG, Ideation",
    ),
    Stage(
        id="canvas",
        title_uk="Business Model Canvas",
        depends_on=("empathy_map", "value_map", "models_options"),
        mode=StageMode.BOTH,
        requires_user_gate=False,
        source="BMG, ядро",
    ),
    Stage(
        id="architecture",
        title_uk="Епіцентр і патерн",
        depends_on=("canvas",),
        mode=StageMode.BOTH,
        requires_user_gate=False,
        source="BMG, Patterns",
    ),
    Stage(
        id="assessment",
        title_uk="SWOT-оцінка блоків",
        depends_on=("canvas", "architecture"),
        mode=StageMode.PRO_ONLY,
        requires_user_gate=False,
        source="BMG, Evaluating Business Models",
    ),
    Stage(
        id="what_if",
        title_uk="ERRC-альтернативи",
        depends_on=("canvas", "architecture"),
        mode=StageMode.BOTH,
        requires_user_gate=True,
        source="Blue Ocean Strategy",
    ),
    Stage(
        id="hypotheses",
        title_uk="Гіпотези D/V/F",
        depends_on=("canvas", "what_if"),
        mode=StageMode.BOTH,
        requires_user_gate=False,
        source="Testing Business Ideas",
    ),
    Stage(
        id="scenario",
        title_uk="Сценарій до/після",
        depends_on=("empathy_map", "value_map", "models_options"),
        mode=StageMode.BOTH,
        requires_user_gate=False,
        source="BMG, Scenarios",
    ),
    Stage(
        id="pitch",
        title_uk="Пітч-презентації",
        depends_on=_BOTH_STAGES_BEFORE_PITCH,
        mode=StageMode.BOTH,
        requires_user_gate=False,
        source="BMG, Storytelling",
    ),
)


def stages_for_mode(pro: bool) -> tuple[Stage, ...]:
    """Return stages available in the given mode, preserving STAGES order."""
    if pro:
        return STAGES
    return tuple(s for s in STAGES if s.mode is StageMode.BOTH)


def topological_order(pro: bool) -> tuple[str, ...]:
    """Deterministic topological order of stage ids for the given mode.

    Ties are broken by position in STAGES, so the result is reproducible
    across runs and independent of dict/set iteration order.
    """
    stages = stages_for_mode(pro)
    available_ids = {s.id for s in stages}
    index = {s.id: i for i, s in enumerate(stages)}

    remaining = list(stages)
    resolved: set[str] = set()
    order: list[str] = []

    while remaining:
        ready = [
            s
            for s in remaining
            if all(dep in resolved for dep in s.depends_on if dep in available_ids)
        ]
        if not ready:
            raise ValueError("cycle detected among remaining stages: " + ", ".join(s.id for s in remaining))
        ready.sort(key=lambda s: index[s.id])
        next_stage = ready[0]
        order.append(next_stage.id)
        resolved.add(next_stage.id)
        remaining.remove(next_stage)

    return tuple(order)


def validate_dag() -> None:
    """Validate STAGES: all depends_on references exist, no cycles.

    Also enforces that no BOTH-mode stage depends on a PRO_ONLY stage,
    which would break Basic mode.
    """
    ids = {s.id for s in STAGES}
    by_id = {s.id: s for s in STAGES}

    for stage in STAGES:
        for dep in stage.depends_on:
            if dep not in ids:
                raise ValueError(f"stage '{stage.id}' depends_on unknown stage '{dep}'")

    # cycle check via full topological sort over all stages
    resolved: set[str] = set()
    remaining = list(STAGES)
    while remaining:
        ready = [s for s in remaining if all(dep in resolved for dep in s.depends_on)]
        if not ready:
            raise ValueError("cycle detected in STAGES: " + ", ".join(s.id for s in remaining))
        for s in ready:
            resolved.add(s.id)
            remaining.remove(s)

    for stage in STAGES:
        if stage.mode is not StageMode.BOTH:
            continue
        for dep in stage.depends_on:
            dep_stage = by_id[dep]
            if dep_stage.mode is StageMode.PRO_ONLY:
                raise ValueError(
                    f"both-mode stage '{stage.id}' depends on pro-only stage '{dep}'; "
                    "this would break Basic mode"
                )


validate_dag()
