"""Output model for the `business_case` generation stage.

BMG, Design -> Prototyping (p. 165, the third level of canvas detail) and
Outlook -> Business Plan, Financial Analysis (p. 269). Triggered by the
brief's domain at the start of the chain. It needs external research
(market benchmarks), not just text generation. It is a template plus
reference data, not a finished financial model: the final numbers come from
the final canvas's Revenue Streams / Cost Structure at the `pitch` stage,
where this is an optional input.

Every benchmark carries a source and retrieval date (ADR-0005: external
search tends to return marketing content that the model will quote with
confidence; a quantitative claim without provenance is not accepted).

Single language per project; this model doesn't carry the language.
"""

from datetime import date
from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from bizstruct_domain.sanitize import SanitizedModel

SalesCase = Literal["conservative", "base", "optimistic"]

_SALES_CASE_ORDER: tuple[SalesCase, ...] = ("conservative", "base", "optimistic")


class MarketBenchmark(SanitizedModel):
    """One external market data point for the domain."""

    model_config = ConfigDict(extra="forbid")

    metric: str = Field(min_length=3, max_length=150, description="e.g. typical price, market size, typical cost range.")
    value: str = Field(min_length=1, max_length=150)
    source: str = Field(min_length=3, max_length=300)
    retrieved_at: date


class SalesScenario(SanitizedModel):
    """One sales projection built on the benchmarks."""

    model_config = ConfigDict(extra="forbid")

    case: SalesCase
    assumptions: str = Field(min_length=20, max_length=600)
    projection: str = Field(min_length=10, max_length=600)


class CostItem(SanitizedModel):
    """One typical cost line for models of this domain/pattern."""

    model_config = ConfigDict(extra="forbid")

    item: str = Field(min_length=3, max_length=150)
    estimate: str = Field(min_length=1, max_length=150)


class BusinessCase(SanitizedModel):
    """Output of the `business_case` stage."""

    model_config = ConfigDict(extra="forbid")

    market_benchmarks: list[MarketBenchmark] = Field(min_length=1, max_length=10)
    breakeven_formula: str = Field(
        min_length=10,
        max_length=600,
        description="How the breakeven point is computed; the numbers are filled in from the final canvas at the pitch stage.",
    )
    sales_scenarios: list[SalesScenario] = Field(min_length=3, max_length=3)
    capital_costs: list[CostItem] = Field(min_length=1, max_length=10)
    operating_costs: list[CostItem] = Field(min_length=1, max_length=10)
    funding_requirements: str = Field(
        min_length=10,
        max_length=600,
        description="Estimated funding need, derived from capital costs and time to breakeven.",
    )
    profit_potential: str = Field(
        min_length=10,
        max_length=600,
        description="Profitability and cash flow over time, under the stated assumptions.",
    )

    @model_validator(mode="after")
    def _validate_sales_case_order(self) -> "BusinessCase":
        actual = tuple(s.case for s in self.sales_scenarios)
        if actual != _SALES_CASE_ORDER:
            raise ValueError(f"sales_scenarios must be in order {_SALES_CASE_ORDER}, got {actual}")
        return self
