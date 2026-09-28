import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.patterns import Patterns, PatternTag
from bizstruct_domain.enums import CanvasBranchingDecision, Pattern, PatternSubtype

_RATIONALE = "The segments share one channel and one core value proposition."


def _tag(pattern: Pattern, subtype: PatternSubtype | None = None) -> dict:
    return dict(pattern=pattern, subtype=subtype, rationale=_RATIONALE)


def _patterns(**overrides) -> dict:
    data = dict(
        pattern_tags=[_tag(Pattern.LONG_TAIL)],
        segment_count=1,
        branching_decision=CanvasBranchingDecision.A_SHARED,
        branching_rationale=_RATIONALE,
    )
    data.update(overrides)
    return data


def test_valid_patterns_passes():
    Patterns(**_patterns())


def test_zero_tags_is_valid():
    Patterns(**_patterns(pattern_tags=[]))


def test_one_segment_can_fit_several_patterns():
    tags = [
        _tag(Pattern.LONG_TAIL),
        _tag(Pattern.FREE, PatternSubtype.FREEMIUM),
        _tag(Pattern.OPEN_BUSINESS_MODEL, PatternSubtype.OUTSIDE_IN),
    ]
    Patterns(**_patterns(pattern_tags=tags))


def test_repeated_pattern_rejected():
    with pytest.raises(ValidationError):
        Patterns(**_patterns(pattern_tags=[_tag(Pattern.LONG_TAIL), _tag(Pattern.LONG_TAIL)]))


def test_multi_sided_platform_with_one_segment_rejected():
    with pytest.raises(ValidationError, match="multi_sided_platform"):
        Patterns(**_patterns(pattern_tags=[_tag(Pattern.MULTI_SIDED_PLATFORM)], segment_count=1))


def test_multi_sided_platform_with_two_segments_passes():
    Patterns(**_patterns(pattern_tags=[_tag(Pattern.MULTI_SIDED_PLATFORM)], segment_count=2))


def test_branching_with_one_segment_rejected():
    with pytest.raises(ValidationError, match="b_branching"):
        Patterns(**_patterns(branching_decision=CanvasBranchingDecision.B_BRANCHING, segment_count=1))


def test_branching_with_several_segments_passes():
    Patterns(**_patterns(branching_decision=CanvasBranchingDecision.B_BRANCHING, segment_count=3))


def test_zero_segment_count_rejected():
    with pytest.raises(ValidationError):
        Patterns(**_patterns(segment_count=0))


@pytest.mark.parametrize("pattern", [Pattern.FREE, Pattern.OPEN_BUSINESS_MODEL])
def test_pattern_with_subtypes_requires_subtype(pattern):
    with pytest.raises(ValidationError):
        PatternTag(**_tag(pattern))


def test_subtype_on_pattern_without_subtypes_rejected():
    with pytest.raises(ValidationError):
        PatternTag(**_tag(Pattern.LONG_TAIL, PatternSubtype.FREEMIUM))


def test_subtype_of_other_pattern_rejected():
    with pytest.raises(ValidationError):
        PatternTag(**_tag(Pattern.FREE, PatternSubtype.INSIDE_OUT))
