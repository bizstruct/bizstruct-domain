"""Generation-chain definition: stage graph, dependencies, and DAG validation.

This is the formalization of docs/adr/0008-bmg-domain-rewrite.md (which
supersedes the stage order of ADR-0001). Consumers (bizstruct-ml,
bizstruct-be, bizstruct-fe via schemas/chain.json) must read the graph from
here rather than hardcoding it locally.

Deliberately NOT modeled here (ADR-0008, "Boundary of this package"):
- Multiplicity. The graph describes the shape of one pass. How many
  instances of a stage a project has (one empathy_map per customer segment,
  one or N canvases after the Patterns A/B decision, versioned iterations)
  and how those instances link to each other is bizstruct-be's job.
- The Canvas -> SWOT -> ERRC iteration loop and its stopping rule
  (weighted Weaknesses + Threats). That is orchestration in
  bizstruct-be/bizstruct-ml, not an edge in this graph. The graph stays
  acyclic by design (see `validate_dag`).
- Product tiers (Basic/Pro). There is one full graph. Which subset of it a
  project runs is bizstruct-be's decision. The graph only says which inputs
  are required (`depends_on`) and which are optional (`optional_depends_on`).
"""

from pydantic import BaseModel, ConfigDict


class Stage(BaseModel):
    """A single step of the business-model generation pipeline.

    Dependency semantics:
    - `depends_on` (hard): the stage cannot be generated until every one
      of these is done. Only hard dependencies define `topological_order`
      and readiness (`stage_machine.ready_stages`).
    - `optional_depends_on`: inputs that make the result more complete or
      better grounded when present, but whose absence does not block the
      stage (e.g. SWOT without an environment scan, ERRC without a SWOT).
      The domain only declares that the input is optional. Whether to wait
      for it before starting the stage, and how to generate without it
      (prompt, expected completeness), is decided by the consumers
      (bizstruct-be for orchestration, bizstruct-ml for generation).
      Optional edges still count for invalidation
      (`stage_machine.dependents_of`): if an optional input changes, a
      result that may have used it is stale.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    title_uk: str
    depends_on: tuple[str, ...]
    optional_depends_on: tuple[str, ...] = ()
    requires_user_gate: bool
    source: str


STAGES: tuple[Stage, ...] = (
    Stage(
        id="brief",
        title_uk="Нормалізація ідеї",
        depends_on=(),
        requires_user_gate=False,
        source="-",
    ),
    Stage(
        id="team_info",
        title_uk="Дані команди",
        depends_on=(),
        requires_user_gate=False,
        source="BMG, Outlook -> Business Plan (p. 268)",
    ),
    Stage(
        id="business_case",
        title_uk="Ринкові бенчмарки",
        depends_on=("brief",),
        requires_user_gate=False,
        source="BMG, Design -> Prototyping (p. 165) + Outlook -> Business Plan, Financial Analysis (p. 269)",
    ),
    Stage(
        id="empathy_map",
        title_uk="Карта емпатії",
        depends_on=("brief",),
        requires_user_gate=False,
        source="BMG, Customer Insights",
    ),
    Stage(
        id="environment_scan",
        title_uk="Аналіз середовища (4 сили)",
        depends_on=("brief", "empathy_map"),
        requires_user_gate=False,
        source="BMG, Business Model Environment",
    ),
    Stage(
        id="value_map",
        title_uk="Ціннісна пропозиція",
        depends_on=("empathy_map",),
        requires_user_gate=False,
        # Outside BMG's scope by the project's own framing — kept as-is
        # pending a product decision, see ADR-0008, open question 1.
        source="Value Proposition Design",
    ),
    Stage(
        id="customer_scenario",
        title_uk="Клієнтський сценарій",
        depends_on=("empathy_map",),
        requires_user_gate=False,
        source="BMG, Design -> Scenarios, type 1: customer scenarios (pp. 182-185)",
    ),
    Stage(
        id="ideation",
        title_uk="Епіцентр і \"What if\"",
        depends_on=("brief", "empathy_map"),
        requires_user_gate=False,
        source="BMG, Design -> Ideation (pp. 136-141)",
    ),
    Stage(
        id="patterns",
        title_uk="Патерни і рішення А/Б",
        depends_on=("customer_scenario", "ideation"),
        requires_user_gate=False,
        source="BMG, Patterns (pp. 56-119)",
    ),
    Stage(
        id="models_options",
        title_uk="Варіанти монетизації",
        depends_on=("value_map", "patterns"),
        requires_user_gate=True,
        # No direct counterpart in BMG — kept as a separate stage pending a
        # product decision, see ADR-0008, open question 2.
        source="BMG, Design -> Ideation (project extension)",
    ),
    Stage(
        id="canvas",
        title_uk="Business Model Canvas",
        depends_on=("empathy_map", "value_map", "customer_scenario", "patterns", "models_options"),
        requires_user_gate=False,
        source="BMG, ядро",
    ),
    Stage(
        id="assessment",
        title_uk="SWOT-оцінка",
        depends_on=("canvas", "patterns"),
        optional_depends_on=("environment_scan",),
        requires_user_gate=False,
        source="BMG, Strategy -> Evaluating Business Models (pp. 212-225)",
    ),
    Stage(
        id="errc",
        title_uk="ERRC-альтернативи",
        depends_on=("canvas", "patterns"),
        optional_depends_on=("assessment",),
        requires_user_gate=True,
        source="BMG, Strategy -> Business Model Perspective on Blue Ocean Strategy (pp. 226-231)",
    ),
    Stage(
        id="hypotheses",
        title_uk="Гіпотези D/V/F",
        depends_on=("canvas", "errc"),
        requires_user_gate=False,
        source="Testing Business Ideas",
    ),
    Stage(
        id="scenario",
        title_uk="Сценарій майбутнього",
        depends_on=("canvas",),
        requires_user_gate=False,
        source="BMG, Design -> Scenarios, type 2: future scenarios (pp. 186-189)",
    ),
    Stage(
        id="pitch",
        title_uk="Пітч",
        depends_on=("canvas", "errc", "scenario"),
        optional_depends_on=("team_info", "business_case"),
        requires_user_gate=False,
        source="BMG, Design -> Storytelling (pp. 170-179) + Outlook -> Business Plan (pp. 268-269)",
    ),
)


def topological_order() -> tuple[str, ...]:
    """Deterministic topological order of stage ids over hard dependencies.

    Only `depends_on` constrains the order; `optional_depends_on` does not
    (see `Stage`). Ties are broken by position in STAGES, so the result is
    reproducible across runs and independent of dict/set iteration order.
    """
    index = {s.id: i for i, s in enumerate(STAGES)}

    remaining = list(STAGES)
    resolved: set[str] = set()
    order: list[str] = []

    while remaining:
        ready = [s for s in remaining if all(dep in resolved for dep in s.depends_on)]
        if not ready:
            raise ValueError("cycle detected among remaining stages: " + ", ".join(s.id for s in remaining))
        ready.sort(key=lambda s: index[s.id])
        next_stage = ready[0]
        order.append(next_stage.id)
        resolved.add(next_stage.id)
        remaining.remove(next_stage)

    return tuple(order)


def _assert_acyclic(edges: dict[str, tuple[str, ...]], label: str) -> None:
    resolved: set[str] = set()
    remaining = list(edges)
    while remaining:
        ready = [stage_id for stage_id in remaining if all(dep in resolved for dep in edges[stage_id])]
        if not ready:
            raise ValueError(f"cycle detected in {label}: " + ", ".join(remaining))
        for stage_id in ready:
            resolved.add(stage_id)
            remaining.remove(stage_id)


def validate_dag() -> None:
    """Validate STAGES.

    - stage ids are unique;
    - every `depends_on` / `optional_depends_on` reference is a known stage;
    - no stage lists the same dependency as both hard and optional;
    - hard dependencies alone are acyclic, and so are hard + optional
      together (an optional input that transitively depends on its own
      consumer could never be available to it).
    """
    ids = [s.id for s in STAGES]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate stage ids in STAGES: {sorted(i for i in ids if ids.count(i) > 1)}")
    known = set(ids)

    for stage in STAGES:
        for dep in (*stage.depends_on, *stage.optional_depends_on):
            if dep not in known:
                raise ValueError(f"stage '{stage.id}' depends on unknown stage '{dep}'")
            if dep == stage.id:
                raise ValueError(f"stage '{stage.id}' depends on itself")
        overlap = set(stage.depends_on) & set(stage.optional_depends_on)
        if overlap:
            raise ValueError(
                f"stage '{stage.id}' lists {sorted(overlap)} in both depends_on and optional_depends_on"
            )

    _assert_acyclic({s.id: s.depends_on for s in STAGES}, "hard dependencies")
    _assert_acyclic({s.id: (*s.depends_on, *s.optional_depends_on) for s in STAGES}, "hard + optional dependencies")


validate_dag()
