from pydantic import BaseModel, Field, model_validator

from .enums import (
    SegmentRelationType,
    FreePatternSubtype,
    OpenBusinessModelPatternSubtype,
    Pattern,
    CanvasBranch,
)

class SegmentPair(BaseModel):
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


class PairwiseSegmentScore(BaseModel):
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


class CanvasGroup(BaseModel):
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


class PatternTag(BaseModel):
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


class Patterns(BaseModel):
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
        has_multi_sided_tag = any(t.pattern == Pattern.MULTI_SIDED_PLATFORM for t in self.pattern_tags)
        if not has_multi_sided_tag:
            return self

        has_matching_group = any(
            g.relation_type == SegmentRelationType.MULTI_SIDED and len(g.empathy_map_ids) >= 2
            for g in self.groups
        )
        if not has_matching_group:
            raise ValueError(
                "A multi-sided platform pattern requires at least one group with two or more empathy maps."
            )
        return self
