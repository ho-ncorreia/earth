from datetime import date, datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=160)
    role_id: int = Field(gt=0)
    temporary_password: str = Field(min_length=12, max_length=256)


class RoleOut(BaseModel):
    id: int
    name: str
    description: str
    permissions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def extract_permission_codes(cls, value):
        if not isinstance(value, dict) and hasattr(value, "permissions"):
            return {
                "id": value.id,
                "name": value.name,
                "description": value.description,
                "permissions": [permission.code for permission in value.permissions],
            }
        return value


class UserOut(BaseModel):
    id: int
    email: EmailStr
    display_name: str
    is_active: bool
    role: RoleOut
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditEventOut(BaseModel):
    id: int
    actor_email: str
    action: str
    object_type: str
    object_id: str
    previous_value: dict | None
    new_value: dict | None
    correlation_id: str
    origin: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudyCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=1000)
    business_context: str = Field(default="", max_length=4000)
    business_objectives: str = Field(default="", max_length=4000)
    scope: str = Field(default="", max_length=4000)
    out_of_scope: str = Field(default="", max_length=4000)
    architecture_domain: str = Field(default="", max_length=120)
    project_reference: str = Field(default="", max_length=120)
    confidentiality: Literal["Public", "Internal", "Confidential", "Restricted"] = "Internal"
    target_review_date: date | None = None


class StudyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=1000)
    business_context: str | None = Field(default=None, max_length=4000)
    business_objectives: str | None = Field(default=None, max_length=4000)
    scope: str | None = Field(default=None, max_length=4000)
    out_of_scope: str | None = Field(default=None, max_length=4000)
    architecture_domain: str | None = Field(default=None, max_length=120)
    project_reference: str | None = Field(default=None, max_length=120)
    confidentiality: Literal["Public", "Internal", "Confidential", "Restricted"] | None = None
    target_review_date: date | None = None
    status: Literal["Draft", "In Progress", "Ready for Review", "Under Review", "Approved", "Closed", "Archived"] | None = None


class StudyOut(BaseModel):
    id: int
    identifier: str
    title: str
    description: str
    business_context: str
    business_objectives: str
    scope: str
    out_of_scope: str
    architecture_domain: str
    project_reference: str
    lead_architect_id: int
    status: str
    confidentiality: str
    target_review_date: date | None
    row_version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=4000)
    cause: str = Field(default="", max_length=2000)
    risk_event: str = Field(default="", max_length=2000)
    consequences: str = Field(default="", max_length=2000)
    category: str = Field(default="", max_length=120)
    family: str = Field(default="", max_length=120)
    architecture_domain: str = Field(default="", max_length=120)
    probability: int = Field(ge=1, le=4)
    impact: int = Field(ge=1, le=4)
    residual_probability: int | None = Field(default=None, ge=1, le=4)
    residual_impact: int | None = Field(default=None, ge=1, le=4)
    existing_controls: str = Field(default="", max_length=2000)
    control_effectiveness: Literal["Unknown", "Low", "Moderate", "High"] = "Unknown"
    treatment_strategy: Literal["Avoid", "Reduce", "Transfer", "Accept"] = "Reduce"
    study_id: int | None = Field(default=None, gt=0)
    detection_date: date | None = None
    target_resolution_date: date | None = None

    @model_validator(mode="after")
    def validate_residual_pair(self):
        if (self.residual_probability is None) != (self.residual_impact is None):
            raise ValueError("Residual probability and impact must be provided together")
        return self


class RiskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    cause: str | None = Field(default=None, max_length=2000)
    risk_event: str | None = Field(default=None, max_length=2000)
    consequences: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=120)
    family: str | None = Field(default=None, max_length=120)
    architecture_domain: str | None = Field(default=None, max_length=120)
    probability: int | None = Field(default=None, ge=1, le=4)
    impact: int | None = Field(default=None, ge=1, le=4)
    residual_probability: int | None = Field(default=None, ge=1, le=4)
    residual_impact: int | None = Field(default=None, ge=1, le=4)
    existing_controls: str | None = Field(default=None, max_length=2000)
    control_effectiveness: Literal["Unknown", "Low", "Moderate", "High"] | None = None
    treatment_strategy: Literal["Avoid", "Reduce", "Transfer", "Accept"] | None = None
    study_id: int | None = Field(default=None, gt=0)
    detection_date: date | None = None
    target_resolution_date: date | None = None
    status: Literal["Identified", "Assessed", "Treatment Defined", "Mitigation in Progress", "Monitoring", "Accepted", "Closed"] | None = None


class RiskOut(BaseModel):
    id: int
    identifier: str
    title: str
    description: str
    cause: str
    risk_event: str
    consequences: str
    category: str
    family: str
    architecture_domain: str
    probability: int
    impact: int
    inherent_score: int
    residual_probability: int | None
    residual_impact: int | None
    residual_score: int | None
    criticality: str
    existing_controls: str
    control_effectiveness: str
    status: str
    treatment_strategy: str
    owner_id: int | None
    study_id: int | None
    detection_date: date | None
    target_resolution_date: date | None
    row_version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class DecisionOptionIn(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=3000)
    advantages: str = Field(default="", max_length=2000)
    disadvantages: str = Field(default="", max_length=2000)


class DecisionOptionOut(DecisionOptionIn):
    id: int
    position: int

    model_config = ConfigDict(from_attributes=True)


class DecisionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    context: str = Field(default="", max_length=4000)
    problem_statement: str = Field(default="", max_length=4000)
    decision_drivers: str = Field(default="", max_length=3000)
    options: list[DecisionOptionIn] = Field(default_factory=list, max_length=12)
    selected_option: str = Field(default="", max_length=240)
    decision_rationale: str = Field(default="", max_length=4000)
    positive_consequences: str = Field(default="", max_length=3000)
    negative_consequences: str = Field(default="", max_length=3000)
    assumptions: str = Field(default="", max_length=3000)
    constraints: str = Field(default="", max_length=3000)
    principles: str = Field(default="", max_length=2000)
    patterns_and_standards: str = Field(default="", max_length=2000)
    related_study_ids: list[int] = Field(default_factory=list, max_length=50)
    related_risk_ids: list[int] = Field(default_factory=list, max_length=50)


class DecisionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    context: str | None = Field(default=None, max_length=4000)
    problem_statement: str | None = Field(default=None, max_length=4000)
    decision_drivers: str | None = Field(default=None, max_length=3000)
    options: list[DecisionOptionIn] | None = Field(default=None, max_length=12)
    selected_option: str | None = Field(default=None, max_length=240)
    decision_rationale: str | None = Field(default=None, max_length=4000)
    positive_consequences: str | None = Field(default=None, max_length=3000)
    negative_consequences: str | None = Field(default=None, max_length=3000)
    assumptions: str | None = Field(default=None, max_length=3000)
    constraints: str | None = Field(default=None, max_length=3000)
    principles: str | None = Field(default=None, max_length=2000)
    patterns_and_standards: str | None = Field(default=None, max_length=2000)
    related_study_ids: list[int] | None = Field(default=None, max_length=50)
    related_risk_ids: list[int] | None = Field(default=None, max_length=50)
    status: Literal["Draft", "Proposed", "Under Review", "Accepted", "Rejected", "Superseded", "Deprecated"] | None = None
    decision_authority: str | None = Field(default=None, max_length=240)
    rejection_rationale: str | None = Field(default=None, max_length=2000)
    decision_date: date | None = None
    review_date: date | None = None
    superseded_by_id: int | None = Field(default=None, gt=0)


class DecisionOut(BaseModel):
    id: int
    number: str
    title: str
    context: str
    problem_statement: str
    decision_drivers: str
    options: list[DecisionOptionOut]
    selected_option: str
    decision_rationale: str
    positive_consequences: str
    negative_consequences: str
    assumptions: str
    constraints: str
    principles: str
    patterns_and_standards: str
    status: str
    owner_id: int
    owner: UserOut
    decision_authority: str
    rejection_rationale: str
    decision_date: date | None
    review_date: date | None
    superseded_by_id: int | None
    related_study_ids: list[int] = Field(default_factory=list)
    related_risk_ids: list[int] = Field(default_factory=list)
    version: int
    row_version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def flatten_relations(cls, value):
        if not isinstance(value, dict) and hasattr(value, "related_studies"):
            return {
                **{field: getattr(value, field) for field in (
                    "id", "number", "title", "context", "problem_statement", "decision_drivers", "options",
                    "selected_option", "decision_rationale", "positive_consequences", "negative_consequences",
                    "assumptions", "constraints", "principles", "patterns_and_standards", "status", "owner_id",
                    "owner", "decision_authority", "rejection_rationale", "decision_date", "review_date",
                    "superseded_by_id", "version", "row_version", "created_at", "updated_at",
                )},
                "related_study_ids": [study.id for study in value.related_studies],
                "related_risk_ids": [risk.id for risk in value.related_risks],
            }
        return value


class DecisionVersionOut(BaseModel):
    version: int
    snapshot: dict
    created_by_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatAsk(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = Field(default=None, gt=0)


class SourceReferenceOut(BaseModel):
    id: int
    source_type: str
    object_id: int
    title: str
    excerpt: str

    model_config = ConfigDict(from_attributes=True)


class AIMessageOut(BaseModel):
    id: int
    role: str
    content: str
    model: str
    prompt_version: str
    created_at: datetime
    sources: list[SourceReferenceOut]

    model_config = ConfigDict(from_attributes=True)


class AIConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIConversationDetailOut(AIConversationOut):
    messages: list[AIMessageOut]


class ChatResponse(BaseModel):
    conversation: AIConversationOut
    user_message: AIMessageOut
    assistant_message: AIMessageOut