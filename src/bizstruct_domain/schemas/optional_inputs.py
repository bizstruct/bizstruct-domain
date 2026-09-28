from pydantic import BaseModel, Field


class TeamMember(BaseModel):
    """
        Represents a team member involved in the business structuring process.
    """
    name: str = Field(
        ...,
        description="The name of the team member.",
        examples=["Alice Johnson", "Bob Smith"],
    )
    role: str = Field(
        ...,
        description="The role of the team member within the business structuring process.",
        examples=["Project Manager", "Business Analyst"],
    )
    relevant_experience: str = Field(
        ...,
        description="A brief description of the team member's relevant experience.",
        examples=[
            "Alice has over 10 years of experience in business strategy and market analysis.",
            "Bob has a background in financial modeling and risk assessment.",
        ],
    )
    key_competencies: list[str] = Field(
        ...,
        description="A list of the team member's key competencies.",
        examples=[
            ["Strategic Planning", "Market Analysis", "Customer Relationship Management"],
            ["Financial Modeling", "Risk Assessment", "Data Analysis"],
        ],
    )


class TeamInfo(BaseModel):
    """
        Represents information about the team involved in the business structuring process.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the team.",
        examples=["team_001"],
    )
    project_id: str = Field(
        ...,
        description="Identifier of the project this team is associated with.",
        examples=["project_001"],
    )
    members: list[TeamMember] = Field(
        ...,
        min_length=1,
        description="A list of team members involved in the business structuring process.",
        examples=[
            [
                TeamMember(
                    name="Alice Johnson",
                    role="Project Manager",
                    relevant_experience="Alice has over 10 years of experience in business strategy and market analysis.",
                    key_competencies=["Strategic Planning", "Market Analysis", "Customer Relationship Management"],
                ),
                TeamMember(
                    name="Bob Smith",
                    role="Business Analyst",
                    relevant_experience="Bob has a background in financial modeling and risk assessment.",
                    key_competencies=["Financial Modeling", "Risk Assessment", "Data Analysis"],
                ),
            ],
        ],
    )


class SalesScenario(BaseModel):
    """
        Represents a sales scenario in a business context.
    """
    name: str = Field(
        ...,
        description="The name of the sales scenario.",
        examples=["High Demand Scenario", "Low Demand Scenario"],
    )
    description: str = Field(
        ...,
        description="A brief description of the sales scenario.",
        examples=[
            "In this scenario, the company experiences high demand for its products due to market trends and customer preferences.",
            "In this scenario, the company faces low demand for its products due to market saturation and changing customer preferences.",
        ],
    )


class BusinessCase(BaseModel):
    """
        Represents a business case in a business context.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the business case.",
        examples=["business_case_001"],
    )
    project_id: str = Field(
        ...,
        description="Identifier of the project this business case is associated with.",
        examples=["project_001"],
    )
    market_benchmarks: str = Field(
        ...,
        description="A brief description of the market benchmarks relevant to the business case.",
        examples=[
            "The market benchmarks indicate a growing demand for eco-friendly products, with a projected annual growth rate of 10% over the next five years.",
            "The market benchmarks suggest a declining trend in consumer interest for traditional products, with a projected annual decrease of 5% in sales over the next three years.",
        ],
    )
    breakeven_formula: str = Field(
        ...,
        description="The formula used to calculate the breakeven point for the business case.",
        examples=[
            "Breakeven Point = Fixed Costs / (Selling Price per Unit - Variable Cost per Unit)",
            "Breakeven Point = Total Fixed Costs / (Unit Selling Price - Unit Variable Cost)",
        ],
    )
    sales_scenarios: list[SalesScenario] = Field(
        ...,
        min_length=1,
        description="A list of sales scenarios relevant to the business case.",
        examples=[
            [
                SalesScenario(
                    name="High Demand Scenario",
                    description="In this scenario, the company experiences high demand for its products due to market trends and customer preferences.",
                ),
                SalesScenario(
                    name="Low Demand Scenario",
                    description="In this scenario, the company faces low demand for its products due to market saturation and changing customer preferences.",
                ),
            ],
        ],
    )
    capital_and_operating_costs: str = Field(
        ...,
        description="A brief description of the capital and operating costs associated with the business case.",
        examples=[
            "The capital costs include the purchase of new machinery and equipment, while the operating costs cover expenses such as labor, utilities, and raw materials.",
            "The capital costs involve the construction of a new production facility, while the operating costs encompass maintenance, staffing, and supply chain management.",
        ],
    )
    funding_requirements: str = Field(
        ...,
        description="A brief description of the funding requirements for the business case.",
        examples=[
            "The funding requirements include securing a loan of $500,000 to cover initial capital expenditures and working capital needs.",
            "The funding requirements involve raising $1 million in equity investment to support the expansion of production capacity and market entry strategies.",
        ],
    )
    profit_potential_notes: str = Field(
        ...,
        description="Notes on the profit potential of the business case.",
        examples=[
            "The profit potential is significant, with projected net profits of $200,000 in the first year and a steady increase in profitability over the next five years.",
            "The profit potential is moderate, with expected net profits of $50,000 in the first year and gradual growth as market share increases and operational efficiencies are realized.",
        ],
    )


class EnvironmentScan(BaseModel):
    """
        Represents an environment scan in a business context.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the environment scan.",
        examples=["environment_scan_001"],
    )
    project_id: str = Field(
        ...,
        description="Identifier of the project this environment scan is associated with.",
        examples=["project_001"],
    )
    market_forces: list[str] = Field(
        ...,
        min_length=1,
        description="A list of market forces relevant to the environment scan.",
        examples=[["Market volatility", "Regulatory changes"]],
    )
    industry_forces: list[str] = Field(
        ...,
        min_length=1,
        description="A list of industry forces relevant to the environment scan.",
        examples=[["Competitive rivalry", "Supplier power"]],
    )
    key_trends: list[str] = Field(
        ...,
        min_length=1,
        description="A list of key trends relevant to the environment scan.",
        examples=[["Digital transformation", "Sustainability initiatives"]],
    )
    macroeconomic_forces: list[str] = Field(
        ...,
        min_length=1,
        description="A list of macroeconomic forces relevant to the environment scan.",
        examples=[["Interest rate fluctuations", "Inflation trends"]],
    )

