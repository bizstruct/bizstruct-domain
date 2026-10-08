"""The Canvas -> SWOT -> ERRC loop as pure functions (ADR-0012): when to continue, which version is final."""
import itertools

import pytest

import schema_builders as b
from bizstruct_domain.schemas import (
    MAX_CANVAS_VERSIONS,
    SwotCluster,
    final_canvas,
    final_swot,
    loop_should_continue,
    select_final_version,
)

# --------------------------------------------------------------------------- loop_should_continue


def test_a_single_score_continues():
    assert loop_should_continue([40.0]) is True


def test_continues_while_the_score_strictly_decreases():
    assert loop_should_continue([50, 40]) is True
    assert loop_should_continue([50, 40, 30, 20]) is True


def test_stops_when_the_last_score_did_not_decrease():
    assert loop_should_continue([50, 60]) is False
    assert loop_should_continue([50, 40, 45]) is False


def test_equal_counts_as_not_decreased():
    assert loop_should_continue([50, 50]) is False
    assert loop_should_continue([50, 40, 40]) is False


def test_stops_at_five_versions_even_if_still_improving():
    assert loop_should_continue([50, 40, 30, 20, 10]) is False


def test_only_the_last_step_counts():
    # an earlier increase cannot occur in a real loop (it would have stopped), but the rule is about the last step
    assert loop_should_continue([50, 60, 55]) is True


@pytest.mark.parametrize("scores", [[], [1] * (MAX_CANVAS_VERSIONS + 1)])
def test_out_of_range_input_is_an_error(scores):
    with pytest.raises(ValueError):
        loop_should_continue(scores)
    with pytest.raises(ValueError):
        select_final_version(scores)


# --------------------------------------------------------------------------- select_final_version


@pytest.mark.parametrize(
    ("scores", "final"),
    [
        ([40], 1),                              # one version
        ([50, 60], 1),                          # no improvement: v1 is final
        ([50, 50], 1),                          # equal is not an improvement
        ([50, 40, 30, 20, 10], 5),              # steady improvement to v5
        ([50, 40, 30, 35], 3),                  # stops at k=3: the worse v4 is not final
        ([50, 40, 45, 30], 2),                  # first non-decreasing step ends it; later scores are ignored
        ([50, 40, 40], 2),                      # equal after an improvement
        ([50, 40, 30, 30, 10], 3),
        ([10, 20, 30, 40, 50], 1),              # worsening from the start
        ([50, 40, 30, 20, 25], 4),              # the fifth version is worse than the fourth
    ],
)
def test_select_final_version_cases(scores, final):
    assert select_final_version(scores) == final


# Exhaustive property checks: every sequence of 1..5 scores drawn from a small alphabet.
ALL = [list(s) for n in range(1, MAX_CANVAS_VERSIONS + 1) for s in itertools.product(range(4), repeat=n)]


def test_final_version_is_in_range_and_its_prefix_strictly_decreases():
    for scores in ALL:
        final = select_final_version(scores)
        assert 1 <= final <= len(scores)
        prefix = scores[:final]
        assert all(prefix[i] < prefix[i - 1] for i in range(1, len(prefix))), scores


def test_final_is_the_last_version_exactly_when_every_step_decreased():
    for scores in ALL:
        every_step_decreased = all(scores[i] < scores[i - 1] for i in range(1, len(scores)))
        assert (select_final_version(scores) == len(scores)) == every_step_decreased, scores


def test_a_non_final_cycle_ends_with_a_step_that_did_not_decrease():
    for scores in ALL:
        final = select_final_version(scores)
        if final < len(scores):
            assert scores[final] >= scores[final - 1], scores


def test_scores_after_the_first_non_decreasing_step_do_not_matter():
    for scores in ALL:
        final = select_final_version(scores)
        if final < len(scores):
            for tail in itertools.product(range(4), repeat=len(scores) - final - 1):
                variant = scores[: final + 1] + list(tail)
                assert select_final_version(variant) == final, (scores, variant)


def test_the_loop_and_the_final_version_agree():
    """Run the loop the way an orchestrator would: it never goes past the first non-decreasing step, and the
    final version of what it produced is the last one that was better."""
    for scores in ALL:
        produced = 1
        while produced < len(scores) and loop_should_continue(scores[:produced]):
            produced += 1
        history = scores[:produced]
        final = select_final_version(history)
        stopped_by_cap = produced == MAX_CANVAS_VERSIONS
        worse_last_step = produced >= 2 and history[-1] >= history[-2]
        if worse_last_step:
            assert final == produced - 1, scores
        else:
            assert final == produced and (stopped_by_cap or produced == len(scores)), scores


def test_select_final_version_does_not_mutate_its_input():
    scores = [50, 40, 45]
    select_final_version(scores)
    assert scores == [50, 40, 45]


# --------------------------------------------------------------------------- final_swot / final_canvas


def swot_scoring(total: int, version: int, canvas_id: str | None = None):
    """A valid Swot whose weighted_weakness_threat_score is `total` (21..105: the fixed threat catalog,
    every threat at least 1 and at most 5)."""
    extra = total - 21
    assert 0 <= extra <= 84
    clusters = []
    for kind in SwotCluster:
        questions = b.catalog(kind)
        scores = []
        for _ in questions:
            bump = min(4, extra)
            extra -= bump
            scores.append(1 + bump)
        clusters.append(b.cluster(kind, axes=[b.axis(1), b.axis(2)], threats=b.catalog(kind, scores)))
    swot = b.swot(clusters, id=f"swot_{version}", canvas_id=canvas_id or f"canvas_{version}", canvas_version=version)
    assert swot.weighted_weakness_threat_score == total
    return swot


def cycle(*totals: int):
    swots = [swot_scoring(t, v) for v, t in enumerate(totals, start=1)]
    canvases = [b.canvas(id=f"canvas_{v}", version=v) for v in range(1, len(totals) + 1)]
    return canvases, swots


@pytest.mark.parametrize(
    ("totals", "final"),
    [
        ((60,), 1),
        ((60, 70), 1),                          # no improvement: v1 final
        ((90, 80, 70, 60, 50), 5),              # steady improvement to v5
        ((90, 80, 70, 75), 3),                  # stop at k = 3
        ((90, 80, 80), 2),                      # equal scores
    ],
)
def test_final_swot_and_canvas_follow_the_scores(totals, final):
    canvases, swots = cycle(*totals)
    assert final_swot(swots).canvas_version == final
    assert final_canvas(canvases, swots).version == final
    assert final_canvas(canvases, swots).id == f"canvas_{final}"


def test_the_input_order_does_not_matter():
    canvases, swots = cycle(90, 80, 85)
    assert final_swot(list(reversed(swots))).canvas_version == 2
    assert final_canvas(list(reversed(canvases)), list(reversed(swots))).id == "canvas_2"


def test_swot_versions_must_be_one_to_n_without_gap_or_duplicate():
    _, swots = cycle(90, 80, 70)
    with pytest.raises(ValueError, match="1..n"):
        final_swot([swots[0], swots[2]])
    with pytest.raises(ValueError, match="1..n"):
        final_swot([swots[0], swots[0]])


def test_the_final_canvas_must_be_provided():
    canvases, swots = cycle(90, 80, 85)
    with pytest.raises(ValueError, match="not provided"):
        final_canvas([canvases[0], canvases[2]], swots)


def test_the_final_canvas_is_matched_by_the_swots_canvas_id_not_only_by_number():
    canvases, swots = cycle(90, 80)
    other = b.canvas(id="canvas_of_another_group", version=2)
    assert final_canvas([canvases[0], other, canvases[1]], swots).id == "canvas_2"


def test_versions_are_ordered_by_canvas_version_not_by_id_or_input_order():
    canvases, swots = cycle(90, 80, 85)
    renamed = [s.model_copy(update={"id": name}) for s, name in zip(swots, ["z", "m", "a"])]  # ids sort the other way
    assert final_swot(list(reversed(renamed))).id == "m"
