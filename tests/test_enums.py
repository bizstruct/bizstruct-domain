from bizstruct_domain.enums import PATTERN_SUBTYPES, Epicenter, Pattern


def test_epicenter_has_exactly_five_values():
    assert len(list(Epicenter)) == 5


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
