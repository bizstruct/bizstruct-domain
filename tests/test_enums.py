from bizstruct_domain.enums import (
    PATTERN_SUBTYPES,
    SWOT_CLUSTER_SECTIONS,
    CanvasSection,
    Epicenter,
    Pattern,
    SWOTCluster,
)


def test_epicenter_has_exactly_four_values():
    # "multiple epicenter" is expressed as Ideation.epicenters holding more
    # than one value, not as a fifth enum value (ADR-0008).
    assert len(list(Epicenter)) == 4
    assert "multiple_epicenter" not in {e.value for e in Epicenter}


def test_pattern_has_exactly_five_values():
    assert len(list(Pattern)) == 5


def test_pattern_subtypes_covers_all_patterns():
    assert set(PATTERN_SUBTYPES.keys()) == set(Pattern)


def test_no_invented_epicenter_values():
    values = {e.value for e in Epicenter}
    assert "competitor_driven" not in values


def test_no_invented_pattern_values():
    values = {p.value for p in Pattern}
    assert "paid" not in values


def test_swot_clusters_partition_the_nine_canvas_sections():
    assert set(SWOT_CLUSTER_SECTIONS) == set(SWOTCluster)
    covered = [section for sections in SWOT_CLUSTER_SECTIONS.values() for section in sections]
    assert sorted(covered) == sorted(CanvasSection)
