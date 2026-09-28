from datetime import date

import pytest
from pydantic import ValidationError

from bizstruct_domain.blocks.business_case import BusinessCase
from bizstruct_domain.blocks.team_info import TeamInfo


def test_team_info_minimal_passes():
    TeamInfo(members=[dict(name="Olena", role="CEO", experience="Ten years in logistics.")])


def test_team_info_without_members_rejected():
    with pytest.raises(ValidationError):
        TeamInfo(members=[])


def _sales(case: str) -> dict:
    return dict(case=case, assumptions="Conversion of 2% from organic traffic.", projection="1,000 users in year one.")


def _business_case(**overrides) -> dict:
    data = dict(
        market_benchmarks=[
            dict(metric="Typical monthly price", value="$20-40", source="Industry report 2026", retrieved_at=date(2026, 9, 1)),
        ],
        breakeven_formula="Fixed costs / (price - variable cost per unit)",
        sales_scenarios=[_sales("conservative"), _sales("base"), _sales("optimistic")],
        capital_costs=[dict(item="Initial development", estimate="$50k")],
        operating_costs=[dict(item="Hosting", estimate="$1k/month")],
        funding_requirements="About $150k to reach breakeven in 18 months.",
        profit_potential="Positive cash flow from month 19 under the base scenario.",
    )
    data.update(overrides)
    return data


def test_business_case_valid_passes():
    BusinessCase(**_business_case())


def test_business_case_sales_scenarios_out_of_order_rejected():
    with pytest.raises(ValidationError):
        BusinessCase(**_business_case(sales_scenarios=[_sales("base"), _sales("conservative"), _sales("optimistic")]))


def test_business_case_benchmark_without_source_rejected():
    benchmark = dict(metric="Typical monthly price", value="$20-40", retrieved_at=date(2026, 9, 1))
    with pytest.raises(ValidationError):
        BusinessCase(**_business_case(market_benchmarks=[benchmark]))
