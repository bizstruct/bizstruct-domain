"""Shape of the `team_info` stage — user-provided, not generated.

BMG, Outlook -> Business Plan (p. 268): "Highlight why your team is the
right one to successfully build and execute the business model you
propose." The system cannot generate this; only the user can describe their
team. It is collected at the start, alongside the brief, stored separately,
and its only consumer is `pitch` (as an optional input). If it is missing,
the pitch is generated without a team section.

Single language per project; this model doesn't carry the language.
"""

from typing import Annotated

from pydantic import ConfigDict, Field

from bizstruct_domain.sanitize import SanitizedModel

Competency = Annotated[str, Field(min_length=2, max_length=100)]


class TeamMember(SanitizedModel):
    """One team member."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=150)
    experience: str = Field(
        min_length=1,
        max_length=600,
        description="Relevant experience and track record.",
    )
    competencies: list[Competency] = Field(
        default_factory=list,
        max_length=10,
        description="Key competencies for this particular business model.",
    )


class TeamInfo(SanitizedModel):
    """The team behind the project."""

    model_config = ConfigDict(extra="forbid")

    members: list[TeamMember] = Field(min_length=1, max_length=20)
    summary: str | None = Field(
        default=None,
        max_length=1000,
        description="Why this team is the right one to build this business model.",
    )
