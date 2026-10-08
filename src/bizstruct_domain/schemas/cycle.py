"""The Canvas -> SWOT -> ERRC loop as pure functions (ADR-0009, ADR-0012).

Finality is derived, never stored. The versions of the loop are the Swots of
the `swot_errc_cycle` row in version order; their scores are
`Swot.weighted_weakness_threat_score` (lower is better). The loop goes on only
while the score strictly decreases and fewer than `MAX_CANVAS_VERSIONS`
versions exist; the final version is "the last better version": the one just
before the first step that did not decrease, or the last one if every step did.
Equal scores count as NOT decreased.
"""

from collections.abc import Sequence

from .canvas import Canvas
from .swot import Swot

MAX_CANVAS_VERSIONS = 5


def _check(scores: Sequence[float]) -> None:
    if not scores:
        raise ValueError("At least one score is required.")
    if len(scores) > MAX_CANVAS_VERSIONS:
        raise ValueError(f"At most {MAX_CANVAS_VERSIONS} versions exist, got {len(scores)} scores.")


def loop_should_continue(scores: Sequence[float]) -> bool:
    """Whether to generate one more canvas version, given the scores of the versions so far
    (version order). False when `MAX_CANVAS_VERSIONS` versions exist or the last score did not
    decrease versus the previous one; True for a single score."""
    _check(scores)
    if len(scores) >= MAX_CANVAS_VERSIONS:
        return False
    return len(scores) == 1 or scores[-1] < scores[-2]


def select_final_version(scores: Sequence[float]) -> int:
    """The final version number (1-based): the last version before the first step whose score did not
    decrease versus the previous one; the last version if every step decreased."""
    _check(scores)
    for i in range(1, len(scores)):
        if scores[i] >= scores[i - 1]:
            return i
    return len(scores)


def _in_version_order(swots: Sequence[Swot]) -> list[Swot]:
    ordered = sorted(swots, key=lambda s: s.canvas_version)
    versions = [s.canvas_version for s in ordered]
    if versions != list(range(1, len(ordered) + 1)):
        raise ValueError(f"Swot versions must be exactly 1..n with no gap or duplicate, got {versions}.")
    return ordered


def final_swot(swots: Sequence[Swot]) -> Swot:
    """The Swot of the final version (`select_final_version` over the Swots' scores)."""
    ordered = _in_version_order(swots)
    return ordered[select_final_version([s.weighted_weakness_threat_score for s in ordered]) - 1]


def final_canvas(canvases: Sequence[Canvas], swots: Sequence[Swot]) -> Canvas:
    """The final canvas: the one the final Swot evaluated (matched by `Swot.canvas_id`)."""
    swot = final_swot(swots)
    for canvas in canvases:
        if canvas.id == swot.canvas_id:
            return canvas
    raise ValueError(f"Final Swot {swot.id} evaluates canvas {swot.canvas_id}, which was not provided.")
