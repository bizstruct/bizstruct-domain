"""Valid-instance builders shared by the tests of `bizstruct_domain.schemas`.

Each builder returns a minimal valid model; tests override only the fields
they are about, so a failure points at the one field under test.
"""

from typing import Any

from bizstruct_domain.schemas.canvas import Canvas, CanvasCard, CanvasSections
from bizstruct_domain.schemas.customer_scenario import CustomerScenario
from bizstruct_domain.schemas.enums import (
    THREAT_QUESTIONS_BY_CLUSTER,
    CanvasBranch,
    CanvasSection,
    ERRCActionType,
    Pattern,
    SegmentRelationType,
    SwotCluster,
    ThreatQuestion,
)
from bizstruct_domain.schemas.errc import Errc, ErrcMove
from bizstruct_domain.schemas.optional_inputs import EnvironmentScan, Source
from bizstruct_domain.schemas.pattern import CanvasGroup, PatternTag, Patterns
from bizstruct_domain.schemas.pitch import Pitch
from bizstruct_domain.schemas.swot import (
    Swot,
    SwotAxisStatement,
    SwotClusterResult,
    SwotOpportunity,
    SwotThreat,
)

SECTION_NAMES = [s.value for s in CanvasSection]


def cards(prefix: str, n: int) -> list[CanvasCard]:
    return [CanvasCard(id=f"{prefix}_{i}", text=f"{prefix} card {i}") for i in range(n)]


def sections(per_section: int = 2, **overrides: list[CanvasCard]) -> CanvasSections:
    """CanvasSections with `per_section` cards everywhere, except `overrides`."""
    data: dict[str, list[CanvasCard]] = {
        name: cards(name, per_section) for name in SECTION_NAMES
    }
    data.update(overrides)
    return CanvasSections(**data)


def canvas(**overrides: Any) -> Canvas:
    data: dict[str, Any] = dict(
        id="canvas_001",
        group_id="canvas_group_001",
        empathy_map_ids=["empathy_map_001"],
        version=1,
        sections=sections(2),
    )
    data.update(overrides)
    return Canvas(**data)


def customer_scenario(id: str = "cs_001", **overrides: Any) -> CustomerScenario:
    data: dict[str, Any] = dict(
        id=id,
        empathy_map_id="empathy_map_001",
        situation_narrative="A narrative.",
        open_questions=[],
    )
    data.update(overrides)
    return CustomerScenario(**data)


def group(id: str, n_maps: int, relation: SegmentRelationType) -> CanvasGroup:
    return CanvasGroup(
        id=id,
        empathy_map_ids=[f"{id}_map_{i}" for i in range(n_maps)],
        relation_type=relation,
    )


def tag(pattern: Pattern, subtype: Any = None) -> PatternTag:
    return PatternTag(pattern=pattern, subtype=subtype, rationale="because")


def patterns(**overrides: Any) -> Patterns:
    data: dict[str, Any] = dict(
        id="patterns_001",
        project_id="project_001",
        pairwise_scores=[],
        groups=[group("canvas_group_001", 2, SegmentRelationType.SEGMENTED)],
        branch_decision=CanvasBranch.UNIFIED_MODEL,
        pattern_tags=[],
    )
    data.update(overrides)
    return Patterns(**data)


def axis(score: int, importance: int = 5) -> SwotAxisStatement:
    return SwotAxisStatement(
        positive_statement="pos",
        negative_statement="neg",
        score=score,
        importance=importance,
        certainty=5,
    )


def threat(question: ThreatQuestion, score: int = 1) -> SwotThreat:
    return SwotThreat(question=question, text="threat", score=score)


def opportunity(score: int) -> SwotOpportunity:
    return SwotOpportunity(text="opportunity", score=score)


def catalog(kind: SwotCluster, scores: list[int] | int = 1) -> list[SwotThreat]:
    """The exact threat catalog of `kind`; `scores` is one int for all or one per question."""
    questions = THREAT_QUESTIONS_BY_CLUSTER[kind]
    per_question = scores if isinstance(scores, list) else [scores] * len(questions)
    return [threat(q, sc) for q, sc in zip(questions, per_question, strict=True)]


def cluster(
    kind: SwotCluster,
    axes: list[SwotAxisStatement] | None = None,
    threats: list[SwotThreat] | None = None,
    opportunities: list[SwotOpportunity] | None = None,
) -> SwotClusterResult:
    """A valid cluster by default: 2 axis statements, 1 opportunity, the exact threat catalog rated 1."""
    return SwotClusterResult(
        cluster=kind,
        axis_statements=axes if axes is not None else [axis(1), axis(2)],
        opportunities=opportunities if opportunities is not None else [opportunity(3)],
        threats=threats if threats is not None else catalog(kind),
    )


def swot(clusters: list[SwotClusterResult] | None = None, **overrides: Any) -> Swot:
    data: dict[str, Any] = dict(
        id="swot_001",
        canvas_id="canvas_001",
        canvas_version=1,
        clusters=clusters or [cluster(k) for k in SwotCluster],
    )
    data.update(overrides)
    return Swot(**data)


def move(
    action: ERRCActionType,
    target_card_text: str | None = None,
    new_text: str | None = None,
    section: CanvasSection = CanvasSection.CHANNELS,
) -> ErrcMove:
    return ErrcMove(
        action=action,
        target_section=section,
        target_card_text=target_card_text,
        new_text=new_text,
        opposite_side_impact="impact",
        rationale="why",
    )


def errc(moves: list[ErrcMove] | None = None, **overrides: Any) -> Errc:
    data: dict[str, Any] = dict(
        id="errc_001",
        canvas_id="canvas_001",
        swot_id="swot_001",
        from_version=1,
        to_version=2,
        result_canvas_id="canvas_002",
        moves=moves if moves is not None else [move(ERRCActionType.CREATE, new_text="new")],
    )
    data.update(overrides)
    return Errc(**data)


def source() -> Source:
    return Source(title="Report", retrieved_at="2026-09-30", note="supports figure")


def environment_scan(id: str = "environment_scan_001") -> EnvironmentScan:
    return EnvironmentScan(
        id=id,
        project_id="project_001",
        sources=[source()],
        market_forces=["m"],
        industry_forces=["i"],
        key_trends=["t"],
        macroeconomic_forces=["e"],
    )


def pitch(**overrides: Any) -> Pitch:
    data: dict[str, Any] = dict(
        id="pitch_001",
        project_id="project_001",
        storytelling_id="storytelling_001",
        canvas_id="canvas_001",
        swot_id="swot_001",
        hook="hook",
        business_model_summary="summary",
        competitive_advantages=["adv"],
        risk_analysis=["risk"],
    )
    data.update(overrides)
    return Pitch(**data)
