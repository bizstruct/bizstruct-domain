from pydantic import Field, model_validator
from .fields import FromGeneratedMixin, SanitizedModel


class PitchGenerated(SanitizedModel):
    """
        Generation contract of Pitch: only what the LLM writes. The system
        fields (business_case_id, canvas_id, id, project_id, storytelling_id, swot_id, team_info_id) are added by Pitch, which extends this model.
    """
    hook: str = Field(
        ...,
        description="A brief and compelling hook for the pitch.",
        examples=["Revolutionizing the way we connect with our customers."],
    )
    business_model_summary: str = Field(
        ...,
        description="A concise summary of the business model being pitched.",
        examples=["Our platform leverages AI to provide personalized recommendations to users."],
    )
    competitive_advantages: list[str] = Field(
        ...,
        min_length=1,
        description="A list of competitive advantages that differentiate the business from its competitors.",
        examples=[
            ["Proprietary AI algorithms", "Strong brand recognition", "Exclusive partnerships"],
        ],
    )
    risk_analysis: list[str] = Field(
        ...,
        min_length=1,
        description="A list of potential risks associated with the business and strategies to mitigate them.",
        examples=[
            ["Market volatility: Diversify product offerings to reduce dependency on a single market segment."],
        ],
    )
    team_section: str | None = Field(
        None,
        description="A section highlighting the team behind the business, if applicable.",
        examples=["Our team consists of experienced professionals with a proven track record in the industry."],
    )
    financial_analysis_section: str | None = Field(
        None,
        description="A section providing a financial analysis of the business, if applicable.",
        examples=["Our financial projections indicate a steady growth trajectory over the next five years."],
    )


class Pitch(PitchGenerated, FromGeneratedMixin):
    """
        Represents a business pitch with various attributes and sections.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the pitch.",
        examples=["pitch_001"],
    )
    project_id: str = Field(
        ...,
        description="Identifier of the project this pitch is associated with.",
        examples=["project_001"],
    )
    storytelling_id: str = Field(
        ...,
        description="Identifier of the storytelling this pitch is associated with.",
        examples=["storytelling_001"],
    )
    canvas_id: str = Field(
        ...,
        description="Identifier of the canvas this pitch is associated with.",
        examples=["canvas_001"],
    )
    swot_id: str = Field(
        ...,
        description="Identifier of the SWOT analysis this pitch is associated with.",
        examples=["swot_001"],
    )
    team_info_id: str | None = Field(
        None,
        description="Identifier of the team information this pitch is associated with, if applicable.",
        examples=["team_info_001"],
    )
    business_case_id: str | None = Field(
        None,
        description="Identifier of the business case this pitch is associated with, if applicable.",
        examples=["business_case_001"],
    )

    @model_validator(mode="after")
    def optional_sections_match_ids(self) -> "Pitch":
        """
        Validates that if team_info_id is provided, then team_section must also be provided,
        and vice versa.Similarly, if business_case_id is provided,
        then financial_analysis_section must also be provided, and vice versa.
        """
        if bool(self.team_info_id) != bool(self.team_section):
            raise ValueError("team_info_id and team_section must both be provided or both be None.")
        if bool(self.business_case_id) != bool(self.financial_analysis_section):
            raise ValueError("business_case_id and financial_analysis_section must both be provided or both be None.")
        return self