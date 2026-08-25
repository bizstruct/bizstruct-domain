"""Output model for the `pitch` generation stage.

Two five-slide decks, one per `bizstruct_domain.enums.PitchAudience` value
(`investor`, `customer`). `customer` is the canonical name — bizstruct-be
previously called this audience `client` while bizstruct-fe already called
it `customer`; this model settles the drift on the frontend's spelling.

Bilingual per field (`_uk`/`_en` suffixes), not a `{uk: {...}, en: {...}}`
wrapper.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

InvestorSlideType = Literal["hook", "problem", "solution", "traction", "ask"]
CustomerSlideType = Literal["opening", "empathy", "transformation", "social_proof", "invitation"]

# Fixed slide order per deck — enforced by the validators below, so the
# frontend can render each deck in this order without re-sorting.
_INVESTOR_ORDER: tuple[InvestorSlideType, ...] = ("hook", "problem", "solution", "traction", "ask")
_CUSTOMER_ORDER: tuple[CustomerSlideType, ...] = (
    "opening", "empathy", "transformation", "social_proof", "invitation",
)


class InvestorSlide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: InvestorSlideType
    headline_uk: str = Field(min_length=1, max_length=80)
    headline_en: str = Field(min_length=1, max_length=80)
    content_uk: str = Field(min_length=1, max_length=400)
    content_en: str = Field(min_length=1, max_length=400)


class CustomerSlide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: CustomerSlideType
    headline_uk: str = Field(min_length=1, max_length=80)
    headline_en: str = Field(min_length=1, max_length=80)
    content_uk: str = Field(min_length=1, max_length=400)
    content_en: str = Field(min_length=1, max_length=400)


class Pitch(BaseModel):
    """Output of the `pitch` stage: investor and customer decks."""

    model_config = ConfigDict(extra="forbid")

    investor: list[InvestorSlide] = Field(min_length=5, max_length=5)
    customer: list[CustomerSlide] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def _validate_slide_order(self) -> "Pitch":
        investor_order = tuple(s.type for s in self.investor)
        if investor_order != _INVESTOR_ORDER:
            raise ValueError(f"investor slides must be in order {_INVESTOR_ORDER}, got {investor_order}")
        customer_order = tuple(s.type for s in self.customer)
        if customer_order != _CUSTOMER_ORDER:
            raise ValueError(f"customer slides must be in order {_CUSTOMER_ORDER}, got {customer_order}")
        return self
