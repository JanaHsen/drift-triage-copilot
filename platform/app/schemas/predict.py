"""
Request and response schemas for the prediction endpoint.

These models mirror the UCI Bank Marketing dataset's raw columns (minus
duration, which leaks the target). Pydantic validates every field on the way
in: wrong types, missing fields, or invalid categorical values produce a 422
response with a structured error before the model ever runs. The brief's
requirement "Bad inputs return structured errors, never stack traces" is
satisfied automatically because that's how FastAPI + Pydantic behave by default.

Why the field aliases: several columns in the dataset have dots in their names
(emp.var.rate, cons.price.idx, ...). Python identifiers can't contain dots, so
we use Pydantic Field(alias=...) to let JSON requests use the dataset's
original column names while the Python attributes use underscores. Without
this, callers would have to remember a translation table — annoying and
error-prone.

Why Literal for categorical fields: it makes invalid categorical values fail
at validation with a clear error listing the allowed values. The downside is
that adding a new category to the model means updating this file too, but
that's the right kind of friction — schema changes should be deliberate.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ----------------------------------------------------------------------------
# Categorical value vocabularies — taken from the dataset's actual values.
# These come from the EDA work in the notebook, not from outside knowledge.
# ----------------------------------------------------------------------------

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
    """
    A single bank-marketing prediction request — raw features as they would
    appear in the bank's customer database at the moment of prediction.
    Notably absent: `duration`, which only exists after the call ends and
    therefore can't be a valid input feature.
    """

    # populate_by_name lets requests use either the alias OR the field name.
    # extra="forbid" rejects unknown fields with a clear error — this is what
    # catches a caller who accidentally sends `duration`.
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    # Demographics
    age: int = Field(ge=18, le=100, description="Customer age in years")
    job: JobLiteral
    marital: MaritalLiteral
    education: EducationLiteral

    # Credit profile
    default: YesNoUnknownLiteral = Field(description="Has credit in default?")
    housing: YesNoUnknownLiteral = Field(description="Has housing loan?")
    loan: YesNoUnknownLiteral = Field(description="Has personal loan?")

    # Contact context for this campaign
    contact: ContactLiteral
    month: MonthLiteral = Field(description="Last contact month")
    day_of_week: DayOfWeekLiteral = Field(description="Last contact day")
    campaign: int = Field(ge=1, description="Contacts during this campaign")

    # Previous-campaign history. pdays==999 is the sentinel for "never
    # contacted before" — we'll engineer this into two features inside the
    # platform before scoring. Caller doesn't need to know that.
    pdays: int = Field(ge=0, le=999, description="Days since last contact (999 = never)")
    previous: int = Field(ge=0, description="Contacts before this campaign")
    poutcome: PoutcomeLiteral = Field(description="Outcome of previous campaign")

    # Macroeconomic indicators — quarterly-ish. Names with dots use aliases.
    emp_var_rate: float = Field(alias="emp.var.rate", description="Employment variation rate")
    cons_price_idx: float = Field(alias="cons.price.idx", description="Consumer price index")
    cons_conf_idx: float = Field(alias="cons.conf.idx", description="Consumer confidence index")
    euribor3m: float = Field(ge=0.0, description="Euribor 3-month rate")
    nr_employed: float = Field(alias="nr.employed", description="Number of employees (thousands)")


class PredictionResponse(BaseModel):
    """
    Response for a single prediction. The probability is the model's raw
    output; the prediction is the boolean classification using the operating
    threshold tuned in the notebook (recall >= 0.75 rule). Both are returned
    so callers can use either, and so the threshold change is auditable.
    """

    prediction: bool = Field(description="True if customer will subscribe")
    probability: float = Field(ge=0.0, le=1.0, description="P(subscribe)")
    threshold: float = Field(description="Operating threshold used")
    model_name: str
    model_version: str
    prediction_id: UUID = Field(description="Unique ID for this prediction (links to predictions log)")
    timestamp: datetime
