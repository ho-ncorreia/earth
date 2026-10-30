from datetime import date, datetime
from typing import Generic, Literal, TypeVar
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=160)
    role_id: int = Field(gt=0)
    temporary_password: str = Field(min_length=12, max_length=256)


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    role_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class UserPasswordReset(BaseModel):
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
    architecture_domain_id: int | None = Field(default=None, gt=0)
    project_reference: str = Field(default="", max_length=120)
    jira_jpd_url: str = Field(default="", max_length=1000)
    confluence_url: str = Field(default="", max_length=1000)
    confidentiality: Literal["Public", "Internal", "Confidential", "Restricted"] = "Internal"
    target_review_date: date | None = None

    @field_validator("jira_jpd_url", "confluence_url")
    @classmethod
    def validate_external_link(cls, value: str) -> str:
        if value:
            parsed = urlsplit(value)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError("External study links must be HTTP(S) URLs without embedded credentials")
        return value


class StudyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=1000)
    business_context: str | None = Field(default=None, max_length=4000)
    business_objectives: str | None = Field(default=None, max_length=4000)
    scope: str | None = Field(default=None, max_length=4000)
    out_of_scope: str | None = Field(default=None, max_length=4000)
    architecture_domain: str | None = Field(default=None, max_length=120)
    architecture_domain_id: int | None = Field(default=None, gt=0)
    project_reference: str | None = Field(default=None, max_length=120)
    jira_jpd_url: str | None = Field(default=None, max_length=1000)
    confluence_url: str | None = Field(default=None, max_length=1000)
    confidentiality: Literal["Public", "Internal", "Confidential", "Restricted"] | None = None
    target_review_date: date | None = None
    status: Literal["Draft", "In Progress", "Ready for Review", "Under Review", "Approved", "Closed", "Archived"] | None = None

    @field_validator("jira_jpd_url", "confluence_url")
    @classmethod
    def validate_external_link(cls, value: str | None) -> str | None:
        if value:
            parsed = urlsplit(value)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError("External study links must be HTTP(S) URLs without embedded credentials")
        return value


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
    architecture_domain_id: int | None
    project_reference: str
    jira_jpd_url: str
    confluence_url: str
    lead_architect_id: int
    status: str
    confidentiality: str
    target_review_date: date | None
    row_version: int
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ArchitectureDomainCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ArchitectureDomainUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool | None = None


class ArchitectureDomainOut(BaseModel):
    id: int
    name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class RiskObjectInput(BaseModel):
    object_type: str = Field(min_length=1, max_length=80)
    object_ref: str = Field(default="", max_length=240)


class RiskObjectOut(RiskObjectInput):
    risk_object_id: str
    risk_id: int

    model_config = ConfigDict(from_attributes=True)


class RiskSourceInput(BaseModel):
    source_type: str = Field(min_length=1, max_length=80)
    source_ref: str = Field(default="", max_length=240)


class RiskSourceOut(RiskSourceInput):
    risk_source_id: str
    risk_id: int

    model_config = ConfigDict(from_attributes=True)


class RiskScopeInput(BaseModel):
    scope_type: str = Field(min_length=1, max_length=80)
    scope_ref: str = Field(default="", max_length=240)


class RiskScopeOut(RiskScopeInput):
    risk_scope_id: str
    risk_id: int

    model_config = ConfigDict(from_attributes=True)


class RiskMitigationInput(BaseModel):
    title: str = Field(default="", max_length=240)
    description: str = Field(default="", max_length=2000)
    residual_probability: int | None = Field(default=None, ge=1, le=4)
    residual_impact: int | None = Field(default=None, ge=1, le=4)
    treatment_strategy: Literal["Avoid", "Reduce", "Transfer", "Accept"] = "Reduce"
    control_effectiveness: Literal["Unknown", "Low", "Moderate", "High"] = "Unknown"

    @model_validator(mode="after")
    def validate_residual_pair(self):
        if (self.residual_probability is None) != (self.residual_impact is None):
            raise ValueError("Residual probability and impact must be provided together")
        return self


class RiskMitigationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=2000)
    residual_probability: int | None = Field(default=None, ge=1, le=4)
    residual_impact: int | None = Field(default=None, ge=1, le=4)
    treatment_strategy: Literal["Avoid", "Reduce", "Transfer", "Accept"] | None = None
    control_effectiveness: Literal["Unknown", "Low", "Moderate", "High"] | None = None

    @model_validator(mode="after")
    def validate_residual_pair(self):
        if (self.residual_probability is None) != (self.residual_impact is None):
            raise ValueError("Residual probability and impact must be provided together")
        return self


class RiskMitigationAttachmentOut(BaseModel):
    id: str
    file_name: str
    content_type: str
    file_size: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskMitigationReviewOut(BaseModel):
    id: str
    reviewer_id: int
    reviewer_name: str
    decision: Literal["Approved", "Rejected"]
    comment: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskMitigationOut(BaseModel):
    mitigation_id: str
    risk_id: int
    risk_identifier: str
    risk_title: str
    title: str
    description: str
    residual_probability: int | None
    residual_impact: int | None
    residual_score: int | None
    treatment_strategy: str
    control_effectiveness: str
    status: Literal["Draft", "Submitted", "Approved", "Rejected"]
    submitted_at: datetime | None
    validated_at: datetime | None
    validated_by_id: int | None
    validation_comment: str
    updated_at: datetime
    attachments: list[RiskMitigationAttachmentOut]
    reviews: list[RiskMitigationReviewOut]

    model_config = ConfigDict(from_attributes=True)


class RiskMitigationReviewInput(BaseModel):
    decision: Literal["Approved", "Rejected"]
    comment: str = Field(default="", max_length=2000)


class RiskConfigurationOut(BaseModel):
    mitigation_validation_stale_days: int = Field(ge=1, le=3650)


class RiskConfigurationUpdate(BaseModel):
    mitigation_validation_stale_days: int = Field(ge=1, le=3650)


class RiskTaxonomyFamilyUpdate(BaseModel):
    name_en: str = Field(min_length=1, max_length=160)
    name_fr: str = Field(min_length=1, max_length=160)


class RiskTaxonomyTypeUpdate(BaseModel):
    label_en: str = Field(min_length=1, max_length=240)
    label_fr: str = Field(min_length=1, max_length=240)


class RiskReferenceValueCreate(BaseModel):
    category: Literal["object_type", "source_type", "scope_type"]
    label_en: str = Field(min_length=1, max_length=160)
    label_fr: str = Field(min_length=1, max_length=160)


class RiskReferenceValueUpdate(BaseModel):
    label_en: str | None = Field(default=None, min_length=1, max_length=160)
    label_fr: str | None = Field(default=None, min_length=1, max_length=160)
    is_active: bool | None = None


class RiskReferenceValueOut(BaseModel):
    id: str
    category: str
    code: str
    label_en: str
    label_fr: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ArdoqSettingsUpdate(BaseModel):
    root_workspace_id: str = Field(min_length=1, max_length=100)
    component_type_ids: dict[str, str]


class ArdoqSettingsOut(BaseModel):
    api_host: str
    org_label: str
    token_configured: bool
    root_workspace_id: str
    component_type_ids: dict[str, str]


class ArdoqComponentOut(BaseModel):
    code: str
    name: str
    component_type: str
    type_id: str


class RiskAssessmentOut(BaseModel):
    assessment_id: str
    risk_id: int
    assessment_type: Literal["Inherent", "Residual"]
    probability: int
    impact: int
    criticality: int

    model_config = ConfigDict(from_attributes=True)


class RiskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=4000)
    cause: str = Field(default="", max_length=2000)
    risk_event: str = Field(default="", max_length=2000)
    consequences: str = Field(default="", max_length=2000)
    category: str = Field(default="", max_length=120)
    family: str = Field(default="", max_length=120)
    family_id: str | None = Field(default=None, pattern=r"^F0[1-8]$")
    subfamily_id: str | None = Field(default=None, pattern=r"^F0[1-8]\.\d{2}$")
    risk_definition_id: str | None = Field(default=None, max_length=12)
    objects: list[RiskObjectInput] = Field(default_factory=list)
    sources: list[RiskSourceInput] = Field(default_factory=list)
    scopes: list[RiskScopeInput] = Field(default_factory=list)
    mitigations: list[RiskMitigationInput] = Field(default_factory=list)
    architecture_domain: str = Field(default="", max_length=120)
    probability: int = Field(ge=1, le=4)
    impact: int = Field(ge=1, le=4)
    residual_probability: int | None = Field(default=None, ge=1, le=4)
    residual_impact: int | None = Field(default=None, ge=1, le=4)
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
    family_id: str | None = Field(default=None, pattern=r"^F0[1-8]$")
    subfamily_id: str | None = Field(default=None, pattern=r"^F0[1-8]\.\d{2}$")
    risk_definition_id: str | None = Field(default=None, max_length=12)
    objects: list[RiskObjectInput] | None = None
    sources: list[RiskSourceInput] | None = None
    scopes: list[RiskScopeInput] | None = None
    architecture_domain: str | None = Field(default=None, max_length=120)
    probability: int | None = Field(default=None, ge=1, le=4)
    impact: int | None = Field(default=None, ge=1, le=4)
    residual_probability: int | None = Field(default=None, ge=1, le=4)
    residual_impact: int | None = Field(default=None, ge=1, le=4)
    control_effectiveness: Literal["Unknown", "Low", "Moderate", "High"] | None = None
    treatment_strategy: Literal["Avoid", "Reduce", "Transfer", "Accept"] | None = None
    study_id: int | None = Field(default=None, gt=0)
    detection_date: date | None = None
    target_resolution_date: date | None = None
    status: Literal["Open", "In Progress", "Closed", "Archived", "Reopened"] | None = None


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
    family_id: str | None
    family_label: str | None
    family_label_en: str | None
    subfamily_id: str | None
    subfamily_label: str | None
    subfamily_label_en: str | None
    risk_definition_id: str | None
    objects: list[RiskObjectOut]
    sources: list[RiskSourceOut]
    scopes: list[RiskScopeOut]
    assessments: list[RiskAssessmentOut]
    mitigations: list[RiskMitigationOut]
    architecture_domain: str
    probability: int
    impact: int
    inherent_score: int
    residual_probability: int | None
    residual_impact: int | None
    residual_score: int | None
    criticality: str
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


class RiskHelpOut(BaseModel):
    id: str
    risk_code: str
    risk_number: int
    subfamily_id: str
    title_en: str
    title_fr: str
    description_en: str
    description_fr: str
    causes: list[str]
    causes_fr: list[str]
    impacts: list[str]
    impacts_fr: list[str]
    data_quality_notes: list[str]

    model_config = ConfigDict(from_attributes=True)


class RiskHelpUpdate(BaseModel):
    title_en: str = Field(min_length=1, max_length=240)
    title_fr: str = Field(min_length=1, max_length=240)
    description_en: str = Field(min_length=1, max_length=4000)
    description_fr: str = Field(default="", max_length=4000)
    causes: list[str]
    causes_fr: list[str] = Field(default_factory=list)
    impacts: list[str]
    impacts_fr: list[str] = Field(default_factory=list)
    data_quality_notes: list[str]


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