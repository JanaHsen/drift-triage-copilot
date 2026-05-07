from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

JobLiteral = Literal[
    "admin.", "blue-collar", "entrepreneur", "housemaid", "management",
    "retired", "self-employed", "services", "student", "technician",
    "unemployed", "unknown",
]
MaritalLiteral = Literal["divorced", "married", "single", "unknown"]
EducationLiteral = Literal[
    "basic.4y", "basic.6y", "basic.9y", "high.school", "illiterate",
    "professional.course", "university.degree", "unknown",
]
YesNoUnknownLiteral = Literal["no", "yes", "unknown"]
ContactLiteral = Literal["cellular", "telephone"]
MonthLiteral = Literal[
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
]
DayOfWeekLiteral = Literal["mon", "tue", "wed", "thu", "fri"]
PoutcomeLiteral = Literal["failure", "nonexistent", "success"]


class PredictionRequest(BaseModel):
    """Raw bank-marketing features for a single prediction. `duration` is excluded — post-call leakage."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    age: int = Field(ge=18, le=100, description="Customer age in years")
    job: JobLiteral
    marital: MaritalLiteral
    education: EducationLiteral
    default: YesNoUnknownLiteral = Field(description="Has credit in default?")
    housing: YesNoUnknownLiteral = Field(description="Has housing loan?")
    loan: YesNoUnknownLiteral = Field(description="Has personal loan?")
    contact: ContactLiteral
    month: MonthLiteral = Field(description="Last contact month")
    day_of_week: DayOfWeekLiteral = Field(description="Last contact day")
    campaign: int = Field(ge=1, description="Contacts during this campaign")
    # 999 is the sentinel for "never contacted before" — engineered into two features before scoring.
    pdays: int = Field(ge=0, le=999, description="Days since last contact (999 = never)")
    previous: int = Field(ge=0, description="Contacts before this campaign")
    poutcome: PoutcomeLiteral = Field(description="Outcome of previous campaign")
    emp_var_rate: float = Field(alias="emp.var.rate", description="Employment variation rate")
    cons_price_idx: float = Field(alias="cons.price.idx", description="Consumer price index")
    cons_conf_idx: float = Field(alias="cons.conf.idx", description="Consumer confidence index")
    euribor3m: float = Field(ge=0.0, description="Euribor 3-month rate")
    nr_employed: float = Field(alias="nr.employed", description="Number of employees (thousands)")


class PredictionResponse(BaseModel):
    """Prediction result with probability, threshold, and model identifiers."""

    prediction: bool = Field(description="True if customer will subscribe")
    probability: float = Field(ge=0.0, le=1.0, description="P(subscribe)")
    threshold: float = Field(description="Operating threshold used")
    model_name: str
    model_version: str
    prediction_id: UUID = Field(description="Unique ID for this prediction")
    timestamp: datetime
