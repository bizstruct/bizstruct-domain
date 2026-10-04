from collections.abc import Iterable, Mapping, Sequence

from pydantic import Field, model_validator
from .fields import SanitizedModel

from .enums import (
    SegmentRelationType,
    FreePatternSubtype,
    OpenBusinessModelPatternSubtype,
    Pattern,
    CanvasBranch,
)

class SegmentPair(SanitizedModel):
    """
        Represents a pair of segments in a business context.
    """
    empathy_map_id_a: str = Field(
        ...,
        description="Identifier of the first empathy map in the segment pair.",
        examples=["empathy_map_001"],
    )
    empathy_map_id_b: str = Field(
        ...,
        description="Identifier of the second empathy map in the segment pair.",
        examples=["empathy_map_002"],
    )

    @model_validator(mode="after")
    def ids_must_differ(self) -> "SegmentPair":
        """
            Validates that the two empathy map identifiers are different.
        """
        if self.empathy_map_id_a == self.empathy_map_id_b:
            raise ValueError(
                "The two empathy map identifiers must be different."
            )
        return self


class _PairwiseScores(SanitizedModel):
    """
        The two scores shared by the persisted and the generation-time pair
        score; which pair they belong to is added by the subclass.
    """
    synergy: int = Field(
        ...,
        ge=0,
        le=5,
        description="A score representing the synergy between the two segments, on a scale from 0 to 5.",
        examples=[3, 4, 5],
    )
    conflict: int = Field(
        ...,
        ge=-7,
        le=0,
        description="A score representing the conflict between the two segments, on a scale from -7 to 0.",
        examples=[-2, -4, -6],
    )

    @property
    def net_score(self) -> int:
        return self.synergy + self.conflict


class PairwiseSegmentScore(_PairwiseScores):
    """
        Represents a score between two segments in a business context.

        Bounds follow the BMG document's NetScore formula: synergy 0..+5,
        conflict -7..0. Thresholds for branch/pattern decisions (e.g.
        Multi-Sided at net_score >= +3) are calibrated against this range;
        widening it invalidates those thresholds.
    """
    segment_pair: SegmentPair = Field(
        ...,
        description="The pair of segments being scored.",
    )


class CanvasGroup(SanitizedModel):
    """
        Represents a group of segments in a business context.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the canvas group (referenced by Canvas.group_id).",
        examples=["canvas_group_001"],
    )
    empathy_map_ids: list[str] = Field(
        ...,
        min_length=1,
        description="A list of empathy map identifiers that belong to this canvas group.",
        examples=[["empathy_map_001", "empathy_map_002"]],
    )
    relation_type: SegmentRelationType = Field(
        ...,
        description="The type of relationship between the segments in this canvas group.",
        examples=[
            SegmentRelationType.MULTI_SIDED,
            SegmentRelationType.SEGMENTED,
            SegmentRelationType.DIVERSIFIED,
        ],
    )


class PatternTag(SanitizedModel):
    """
        Represents a tag for a business model pattern in a business context.
    """
    pattern: Pattern = Field(
        ...,
        description="The business model pattern to which this tag applies.",
        examples=[
            Pattern.UNBUNDLING,
            Pattern.LONG_TAIL,
            Pattern.MULTI_SIDED_PLATFORM,
            Pattern.FREE,
            Pattern.OPEN_BUSINESS_MODEL,
        ],
    )
    subtype: FreePatternSubtype | OpenBusinessModelPatternSubtype | None = Field(
        None,
        description="The subtype of the business model pattern, if applicable.",
        examples=[
            FreePatternSubtype.FREEMIUM,
            OpenBusinessModelPatternSubtype.OUTSIDE_IN,
            OpenBusinessModelPatternSubtype.INSIDE_OUT,
        ],
    )
    rationale: str = Field(
        ...,
        description="A rationale explaining the reasoning behind the pattern tag.",
        examples=["The business model is primarily driven by customer needs and feedback."],
    )

    _SUBTYPE_BY_PATTERN: dict[Pattern, type] = {
        Pattern.FREE: FreePatternSubtype,
        Pattern.OPEN_BUSINESS_MODEL: OpenBusinessModelPatternSubtype,
    }

    @model_validator(mode="after")
    def subtype_matches_pattern(self) -> "PatternTag":
        """
            Validates that the subtype matches the specified pattern.
        """
        expected_type = self._SUBTYPE_BY_PATTERN.get(self.pattern)
        if expected_type and not isinstance(self.subtype, expected_type):
            raise ValueError(
                f"The subtype must be of type {expected_type.__name__} for the pattern {self.pattern.value}."
            )
        if not expected_type and self.subtype is not None:
            raise ValueError(
                f"The subtype must be None for the pattern {self.pattern.value}."
            )
        return self


def _check_multi_sided_platform(
    tags: Iterable["PatternTag"],
    groups: Iterable[tuple[SegmentRelationType, int]],
) -> None:
    """MULTI_SIDED_PLATFORM needs a group that is BOTH relation_type MULTI_SIDED
    AND has at least two segments. `groups` is (relation_type, segment count)."""
    if not any(t.pattern == Pattern.MULTI_SIDED_PLATFORM for t in tags):
        return
    if not any(rel == SegmentRelationType.MULTI_SIDED and size >= 2 for rel, size in groups):
        raise ValueError(
            "A multi-sided platform pattern requires at least one group with two or more empathy maps."
        )


def _check_unique_patterns(tags: Iterable["PatternTag"]) -> None:
    """Each business model pattern is tagged at most once."""
    seen = [t.pattern for t in tags]
    repeated = sorted({p.value for p in seen if seen.count(p) > 1})
    if repeated:
        raise ValueError(f"Each pattern may be tagged only once. Repeated: {', '.join(repeated)}.")


class Patterns(SanitizedModel):
    """
        Represents a collection of patterns in a business context.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the patterns instance.",
        examples=["patterns_001"],
    )
    project_id: str = Field(
        ...,
        description="Identifier of the project this patterns instance is associated with.",
        examples=["project_001"],
    )
    pairwise_scores: list[PairwiseSegmentScore] = Field(
        ...,
        description="A list of pairwise segment scores for the segments in this patterns instance.",
        examples=[
            [
                PairwiseSegmentScore(
                    segment_pair=SegmentPair(
                        empathy_map_id_a="empathy_map_001",
                        empathy_map_id_b="empathy_map_002",
                    ),
                    synergy=4,
                    conflict=-2,
                ),
                PairwiseSegmentScore(
                    segment_pair=SegmentPair(
                        empathy_map_id_a="empathy_map_001",
                        empathy_map_id_b="empathy_map_003",
                    ),
                    synergy=5,
                    conflict=-1,
                ),
            ],
        ],
    )
    groups: list[CanvasGroup] = Field(
        ...,
        min_length=1,
        description="A list of canvas groups for the segments in this patterns instance.",
        examples=[
            [
                CanvasGroup(
                    id="canvas_group_001",
                    empathy_map_ids=["empathy_map_001", "empathy_map_002"],
                    relation_type=SegmentRelationType.MULTI_SIDED,
                ),
                CanvasGroup(
                    id="canvas_group_002",
                    empathy_map_ids=["empathy_map_003", "empathy_map_004"],
                    relation_type=SegmentRelationType.SEGMENTED,
                ),
            ],
        ],
    )
    branch_decision: CanvasBranch = Field(
        ...,
        description="The branch decision for the canvas in this patterns instance.",
        examples=[
            CanvasBranch.UNIFIED_MODEL,
            CanvasBranch.SPLIT_MODEL,
        ],
    )
    pattern_tags: list[PatternTag] = Field(
        ...,
        max_length=5,
        description="A list of pattern tags for the business model patterns in this patterns instance.",
        examples=[
            [
                PatternTag(
                    pattern=Pattern.FREE,
                    subtype=FreePatternSubtype.FREEMIUM,
                    rationale="The business model is primarily driven by customer needs and feedback.",
                ),
                PatternTag(
                    pattern=Pattern.OPEN_BUSINESS_MODEL,
                    subtype=OpenBusinessModelPatternSubtype.OUTSIDE_IN,
                    rationale="The business model is primarily driven by external resources and partnerships.",
                ),
            ],
        ],
    )

    @model_validator(mode="after")
    def branch_matches_group_count(self) -> "Patterns":
        """
            Validates that the branch decision matches the number of groups.
        """
        expected = CanvasBranch.UNIFIED_MODEL if len(self.groups) == 1 else CanvasBranch.SPLIT_MODEL
        if self.branch_decision != expected:
            raise ValueError(
                f"The branch decision {self.branch_decision.value}"
                f" does not match the number of groups ({len(self.groups)}). "
                f"Expected {expected.value}."
            )
        return self

    @model_validator(mode="after")
    def multi_sided_requires_two_maps(self) -> "Patterns":
        """
            Validates that a multi-sided platform pattern requires at least two empathy maps.
        """
        _check_multi_sided_platform(
            self.pattern_tags, [(g.relation_type, len(g.empathy_map_ids)) for g in self.groups]
        )
        return self

    @model_validator(mode="after")
    def pattern_tags_are_unique(self) -> "Patterns":
        """
            Validates that each business model pattern is tagged at most once.
        """
        _check_unique_patterns(self.pattern_tags)
        return self


class SegmentPairGenerated(SanitizedModel):
    """
        A pair of segments as the generator writes it: by alias, never by real id.
    """
    segment_alias_a: str = Field(
        ...,
        min_length=1,
        description="Alias of the first segment, exactly as defined in the prompt (for example \"S1\").",
        examples=["S1"],
    )
    segment_alias_b: str = Field(
        ...,
        min_length=1,
        description="Alias of the second segment, exactly as defined in the prompt (for example \"S2\").",
        examples=["S2"],
    )

    @model_validator(mode="after")
    def aliases_must_differ(self) -> "SegmentPairGenerated":
        """
            Validates that the two aliases are different.
        """
        if self.segment_alias_a == self.segment_alias_b:
            raise ValueError("The two segment aliases must be different.")
        return self


class PairwiseSegmentScoreGenerated(_PairwiseScores):
    """
        A pairwise score as the generator writes it: the pair is given by aliases.
        Same bounds as PairwiseSegmentScore (synergy 0..5, conflict -7..0).
    """
    segment_pair: SegmentPairGenerated = Field(
        ...,
        description="The pair of segments being scored, by alias.",
    )


class CanvasGroupGenerated(SanitizedModel):
    """
        A group of segments as the generator writes it: by alias, without an id
        (group ids are assigned by the system).
    """
    segment_aliases: list[str] = Field(
        ...,
        min_length=1,
        description="Aliases of the segments that belong to this group, as defined in the prompt.",
        examples=[["S1", "S2"]],
    )
    relation_type: SegmentRelationType = Field(
        ...,
        description="The type of relationship between the segments in this group.",
        examples=[
            SegmentRelationType.MULTI_SIDED,
            SegmentRelationType.SEGMENTED,
            SegmentRelationType.DIVERSIFIED,
        ],
    )


class PatternsGenerated(SanitizedModel):
    """
        Generation contract of Patterns: only what the LLM writes. Segments are
        referenced by ALIASES defined in the prompt, never by real ids. Group ids
        are assigned by the system and `branch_decision` is derived from the number
        of groups (one group: unified_model, otherwise split_model); use
        `patterns_from_generated` to build the persisted Patterns.
    """
    pairwise_scores: list[PairwiseSegmentScoreGenerated] = Field(
        ...,
        description="A list of pairwise segment scores, one per pair of segments, by alias.",
        examples=[
            [
                PairwiseSegmentScoreGenerated(
                    segment_pair=SegmentPairGenerated(segment_alias_a="S1", segment_alias_b="S2"),
                    synergy=4,
                    conflict=-2,
                ),
            ],
        ],
    )
    groups: list[CanvasGroupGenerated] = Field(
        ...,
        min_length=1,
        description="The canvas groups of the segments, by alias.",
        examples=[
            [
                CanvasGroupGenerated(
                    segment_aliases=["S1", "S2"],
                    relation_type=SegmentRelationType.MULTI_SIDED,
                ),
                CanvasGroupGenerated(
                    segment_aliases=["S3"],
                    relation_type=SegmentRelationType.SEGMENTED,
                ),
            ],
        ],
    )
    pattern_tags: list[PatternTag] = Field(
        ...,
        max_length=5,
        description="A list of pattern tags for the business model patterns, each pattern at most once.",
        examples=[
            [
                PatternTag(
                    pattern=Pattern.MULTI_SIDED_PLATFORM,
                    subtype=None,
                    rationale="Two interdependent customer groups need each other.",
                ),
            ],
        ],
    )

    @model_validator(mode="after")
    def multi_sided_requires_two_segments(self) -> "PatternsGenerated":
        """
            Validates that a multi-sided platform pattern requires a MULTI_SIDED group with two or more segments.
        """
        _check_multi_sided_platform(
            self.pattern_tags, [(g.relation_type, len(g.segment_aliases)) for g in self.groups]
        )
        return self

    @model_validator(mode="after")
    def pattern_tags_are_unique(self) -> "PatternsGenerated":
        """
            Validates that each business model pattern is tagged at most once.
        """
        _check_unique_patterns(self.pattern_tags)
        return self


def patterns_from_generated(
    generated: PatternsGenerated,
    *,
    id: str,
    project_id: str,
    segment_ids: Mapping[str, str],
    group_ids: Sequence[str],
) -> Patterns:
    """Build the persisted Patterns from its generation contract (pure, no I/O).

    `segment_ids` maps every alias used in the prompt to the real empathy map id;
    `group_ids` gives one id per generated group, in order. `branch_decision` is
    derived (one group: unified_model, otherwise split_model).

    Raises:
        ValueError: on an alias missing from `segment_ids`, or when
            `len(group_ids)` differs from the number of groups. A pydantic
            ValidationError (also a ValueError) signals that the mapped result
            breaks a persisted validator, e.g. two aliases mapped to one id.
    """
    if len(group_ids) != len(generated.groups):
        raise ValueError(
            f"Expected {len(generated.groups)} group ids (one per generated group), got {len(group_ids)}."
        )

    def real(alias: str) -> str:
        try:
            return segment_ids[alias]
        except KeyError:
            raise ValueError(f"Unknown segment alias '{alias}'.") from None

    return Patterns.model_validate(
        {
            "id": id,
            "project_id": project_id,
            "pairwise_scores": [
                {
                    "segment_pair": {
                        "empathy_map_id_a": real(score.segment_pair.segment_alias_a),
                        "empathy_map_id_b": real(score.segment_pair.segment_alias_b),
                    },
                    "synergy": score.synergy,
                    "conflict": score.conflict,
                }
                for score in generated.pairwise_scores
            ],
            "groups": [
                {
                    "id": group_id,
                    "empathy_map_ids": [real(alias) for alias in group.segment_aliases],
                    "relation_type": group.relation_type,
                }
                for group_id, group in zip(group_ids, generated.groups, strict=True)
            ],
            "branch_decision": (
                CanvasBranch.UNIFIED_MODEL if len(generated.groups) == 1 else CanvasBranch.SPLIT_MODEL
            ),
            "pattern_tags": [tag.model_dump() for tag in generated.pattern_tags],
        }
    )
