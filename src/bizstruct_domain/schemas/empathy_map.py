from pydantic import Field
from .fields import FromGeneratedMixin, SanitizedModel


class EmpathyMapGenerated(SanitizedModel):
    """
        Generation contract of EmpathyMap: only what the LLM writes. The system
        fields (id, project_id) are added by EmpathyMap, which extends this model.
    """
    persona_name: str = Field(
        ...,
        description="Name of the persona for whom the empathy map is created.",
        examples=["Tech-Savvy Millennial"],
    )
    persona_demographics: str = Field(
        ...,
        description="Demographic information of the persona.",
        examples=["Age: 25-35, Urban, College-educated"],
    )
    sees: list[str] = Field(
        min_length=1,
        description="What the persona sees in their environment.",
        examples=[
            ["Advertisements for new apps and gadgets"],
            ["Friends using the latest technology"],
            ["Tech blogs and news articles"],
        ]
    )
    hears: list[str] = Field(
        min_length=1,
        description="What the persona hears from others.",
        examples=[
            ["Friends discussing new apps"],
            ["Podcasts about technology trends"],
        ]
    )
    thinks_and_feels: list[str] = Field(
        min_length=1,
        description="What the persona thinks and feels.",
        examples=[
            ["Excited about new technology"],
            ["Concerned about privacy and data security"],
        ],
    )
    says_and_does: list[str] = Field(
        min_length=1,
        description="What the persona says and does.",
        examples=[
            ["Shares tech news on social media"],
            ["Participates in online tech forums"],
        ],
    )
    pains: list[str] = Field(
        min_length=1,
        description="The persona's pains or frustrations.",
        examples=[
            ["Overwhelmed by too many app choices"],
            ["Frustrated with apps that have poor user experience"],
        ],
    )
    gains: list[str] = Field(
        min_length=1,
        description="The persona's gains or desires.",
        examples=[
            ["Wants apps that are easy to use"],
            ["Wants apps that provide value"],
            ["Wants apps that respect privacy"],
        ],
    )


class EmpathyMap(EmpathyMapGenerated, FromGeneratedMixin):
    id: str = Field(
        ...,
        description="Unique identifier for the empathy map.",
        examples=["empathy_map_001"],
    )
    project_id: str = Field(
        ...,
        description="Identifier of the project this empathy map belongs to.",
        examples=["project_001"],
    )
