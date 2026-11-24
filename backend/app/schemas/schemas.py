import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    organization_name: str = Field(min_length=2, max_length=200)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CompanyProfileIn(BaseModel):
    legal_name: str = Field(min_length=2, max_length=250)
    business_type: str | None = None
    sectors: list[str] = Field(default_factory=list)
    udyam_number: str | None = None
    dpiit_startup_number: str | None = None
    gstin: str | None = Field(default=None, min_length=15, max_length=15)
    pan_last_four: str | None = Field(default=None, min_length=4, max_length=4)
    registered_state: str | None = None
    annual_turnover_inr: Decimal | None = Field(default=None, ge=0)
    years_in_business: float | None = Field(default=None, ge=0)


class CompanyProfileOut(CompanyProfileIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    organization_id: uuid.UUID


class TenderIn(BaseModel):
    source: str = Field(min_length=2, max_length=50)
    external_id: str = Field(min_length=1, max_length=150)
    title: str = Field(min_length=3)
    description: str | None = None
    procuring_entity: str | None = None
    category: str | None = None
    state: str | None = None
    estimated_value_inr: Decimal | None = Field(default=None, ge=0)
    published_at: datetime | None = None
    submission_deadline: datetime | None = None
    source_url: HttpUrl | None = None
    status: str = "unknown"
    metadata: dict = Field(default_factory=dict)


class TenderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: uuid.UUID
    source: str
    external_id: str
    title: str
    description: str | None
    procuring_entity: str | None
    category: str | None
    state: str | None
    estimated_value_inr: Decimal | None
    published_at: datetime | None
    submission_deadline: datetime | None
    source_url: str | None
    status: str
    metadata_json: dict = Field(validation_alias="metadata_json")


class RequirementIn(BaseModel):
    requirement_type: str
    title: str
    description: str | None = None
    operator: str | None = None
    numeric_value: Decimal | None = Field(default=None, ge=0)
    unit: str | None = None
    is_mandatory: bool = True
    source_page: int | None = Field(default=None, ge=1)
    source_quote: str | None = None
    extraction_confidence: float | None = Field(default=None, ge=0, le=1)


class RequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tender_id: uuid.UUID
    requirement_type: str
    title: str
    description: str | None
    operator: str | None
    numeric_value: Decimal | None
    unit: str | None
    is_mandatory: bool
    source_page: int | None
    source_quote: str | None
    extraction_confidence: float | None


class AssessmentOut(BaseModel):
    id: uuid.UUID
    tender_id: uuid.UUID
    result: str
    score: float | None
    result_details: dict
