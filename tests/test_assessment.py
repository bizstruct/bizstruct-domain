import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.assessment import Assessment, SWOTStatement
from bizstruct_domain.enums import SWOTCluster


def _statement(**overrides) -> dict:
    data = dict(text="Our value propositions are well aligned with customer needs.", importance=7, certainty=6)
    data.update(overrides)
    return data


def _cluster(cluster: SWOTCluster) -> dict:
    return dict(
        cluster=cluster,
        strengths=[_statement()],
        weaknesses=[_statement()],
        opportunities=[_statement()],
        threats=[_statement()],
    )


def _clusters(order: list[SWOTCluster] | None = None) -> list[dict]:
    return [_cluster(c) for c in (order or list(SWOTCluster))]


def test_valid_assessment_passes():
    Assessment(clusters=_clusters())


def test_wrong_cluster_order_rejected():
    with pytest.raises(ValidationError):
        Assessment(clusters=_clusters(list(reversed(SWOTCluster))))


def test_missing_cluster_rejected():
    with pytest.raises(ValidationError):
        Assessment(clusters=_clusters()[:3])


def test_duplicate_cluster_rejected():
    order = [SWOTCluster.VALUE_PROPOSITION] * 4
    with pytest.raises(ValidationError):
        Assessment(clusters=_clusters(order))


def test_empty_quadrant_rejected():
    clusters = _clusters()
    clusters[0]["threats"] = []
    with pytest.raises(ValidationError):
        Assessment(clusters=clusters)


@pytest.mark.parametrize("field", ["importance", "certainty"])
@pytest.mark.parametrize("value", [0, 11])
def test_scores_out_of_range_rejected(field, value):
    with pytest.raises(ValidationError):
        SWOTStatement(**_statement(**{field: value}))
