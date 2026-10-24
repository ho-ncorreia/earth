from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, JSON, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)

decision_studies = Table(
    "decision_studies",
    Base.metadata,
    Column("decision_id", ForeignKey("architecture_decisions.id", ondelete="CASCADE"), primary_key=True),
    Column("study_id", ForeignKey("architecture_studies.id", ondelete="CASCADE"), primary_key=True),
)

decision_risks = Table(
    "decision_risks",
    Base.metadata,
    Column("decision_id", ForeignKey("architecture_decisions.id", ondelete="CASCADE"), primary_key=True),
    Column("risk_id", ForeignKey("architecture_risks.id", ondelete="CASCADE"), primary_key=True),
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(240), default="")
    permissions: Mapped[list["Permission"]] = relationship(secondary=role_permissions, lazy="selectin")
    users: Mapped[list["User"]] = relationship(back_populates="role")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(240), default="")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), index=True)
    role: Mapped[Role] = relationship(back_populates="users", lazy="joined")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __mapper_args__ = {"version_id_col": row_version}


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    actor_email: Mapped[str] = mapped_column(String(320), default="system")
    action: Mapped[str] = mapped_column(String(120), index=True)
    object_type: Mapped[str] = mapped_column(String(120), index=True)
    object_id: Mapped[str] = mapped_column(String(120), default="")
    previous_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(80), default="")
    origin: Mapped[str] = mapped_column(String(80), default="web")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class ArchitectureStudy(Base):
    __tablename__ = "architecture_studies"
    __table_args__ = (UniqueConstraint("identifier", name="uq_architecture_studies_identifier"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    identifier: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(String(1000), default="")
    business_context: Mapped[str] = mapped_column(String(4000), default="")
    business_objectives: Mapped[str] = mapped_column(String(4000), default="")
    scope: Mapped[str] = mapped_column(String(4000), default="")
    out_of_scope: Mapped[str] = mapped_column(String(4000), default="")
    architecture_domain: Mapped[str] = mapped_column(String(120), default="")
    project_reference: Mapped[str] = mapped_column(String(120), default="")
    lead_architect_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="Draft", index=True)
    confidentiality: Mapped[str] = mapped_column(String(40), default="Internal")
    target_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    lead_architect: Mapped[User] = relationship(lazy="joined")

    __mapper_args__ = {"version_id_col": row_version}


class ArchitectureRisk(Base):
    __tablename__ = "architecture_risks"
    __table_args__ = (UniqueConstraint("identifier", name="uq_architecture_risks_identifier"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    identifier: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(String(4000))
    cause: Mapped[str] = mapped_column(String(2000), default="")
    risk_event: Mapped[str] = mapped_column(String(2000), default="")
    consequences: Mapped[str] = mapped_column(String(2000), default="")
    category: Mapped[str] = mapped_column(String(120), default="")
    family: Mapped[str] = mapped_column(String(120), default="")
    architecture_domain: Mapped[str] = mapped_column(String(120), default="")
    probability: Mapped[int] = mapped_column(Integer)
    impact: Mapped[int] = mapped_column(Integer)
    residual_probability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_impact: Mapped[int | None] = mapped_column(Integer, nullable=True)
    existing_controls: Mapped[str] = mapped_column(String(2000), default="")
    control_effectiveness: Mapped[str] = mapped_column(String(40), default="Unknown")
    status: Mapped[str] = mapped_column(String(40), default="Identified", index=True)
    treatment_strategy: Mapped[str] = mapped_column(String(40), default="Reduce")
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    study_id: Mapped[int | None] = mapped_column(ForeignKey("architecture_studies.id", ondelete="SET NULL"), nullable=True, index=True)
    detection_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_resolution_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    owner: Mapped[User | None] = relationship(foreign_keys=[owner_id], lazy="joined")

    __mapper_args__ = {"version_id_col": row_version}

    @property
    def inherent_score(self) -> int:
        return self.probability * self.impact

    @property
    def residual_score(self) -> int | None:
        if self.residual_probability is None or self.residual_impact is None:
            return None
        return self.residual_probability * self.residual_impact

    @property
    def criticality(self) -> str:
        return risk_criticality(self.inherent_score)


def risk_criticality(score: int) -> str:
    if score >= 12:
        return "Critical"
    if score >= 8:
        return "High"
    if score >= 4:
        return "Medium"
    return "Low"


class ArchitectureDecision(Base):
    __tablename__ = "architecture_decisions"
    __table_args__ = (UniqueConstraint("number", name="uq_architecture_decisions_number"),)
    __table_args__ = (UniqueConstraint("number", name="uq_architecture_decisions_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(240))
    context: Mapped[str] = mapped_column(String(4000), default="")
    problem_statement: Mapped[str] = mapped_column(String(4000), default="")
    decision_drivers: Mapped[str] = mapped_column(String(3000), default="")
    selected_option: Mapped[str] = mapped_column(String(240), default="")
    decision_rationale: Mapped[str] = mapped_column(String(4000), default="")
    positive_consequences: Mapped[str] = mapped_column(String(3000), default="")
    negative_consequences: Mapped[str] = mapped_column(String(3000), default="")
    assumptions: Mapped[str] = mapped_column(String(3000), default="")
    constraints: Mapped[str] = mapped_column(String(3000), default="")
    principles: Mapped[str] = mapped_column(String(2000), default="")
    patterns_and_standards: Mapped[str] = mapped_column(String(2000), default="")
    status: Mapped[str] = mapped_column(String(40), default="Draft", index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    decision_authority: Mapped[str] = mapped_column(String(240), default="")
    rejection_rationale: Mapped[str] = mapped_column(String(2000), default="")
    decision_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    superseded_by_id: Mapped[int | None] = mapped_column(ForeignKey("architecture_decisions.id", ondelete="SET NULL"), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    owner: Mapped[User] = relationship(foreign_keys=[owner_id], lazy="joined")
    superseded_by: Mapped["ArchitectureDecision | None"] = relationship(remote_side="ArchitectureDecision.id", foreign_keys=[superseded_by_id])
    options: Mapped[list["DecisionOption"]] = relationship(back_populates="decision", cascade="all, delete-orphan", order_by="DecisionOption.position", lazy="selectin")
    related_studies: Mapped[list[ArchitectureStudy]] = relationship(secondary=decision_studies, lazy="selectin")
    related_risks: Mapped[list[ArchitectureRisk]] = relationship(secondary=decision_risks, lazy="selectin")
    versions: Mapped[list["DecisionVersion"]] = relationship(back_populates="decision", cascade="all, delete-orphan", order_by="DecisionVersion.version", lazy="selectin")

    __mapper_args__ = {"version_id_col": row_version}


class DecisionOption(Base):
    __tablename__ = "decision_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("architecture_decisions.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(String(3000), default="")
    advantages: Mapped[str] = mapped_column(String(2000), default="")
    disadvantages: Mapped[str] = mapped_column(String(2000), default="")
    decision: Mapped[ArchitectureDecision] = relationship(back_populates="options")


class DecisionVersion(Base):
    __tablename__ = "decision_versions"
    __table_args__ = (UniqueConstraint("decision_id", "version", name="uq_decision_versions_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("architecture_decisions.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    decision: Mapped[ArchitectureDecision] = relationship(back_populates="versions")


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), default="Architecture question")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    messages: Mapped[list["AIMessage"]] = relationship(back_populates="conversation", cascade="all, delete-orphan", order_by="AIMessage.created_at", lazy="selectin")


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("ai_conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(String(12000))
    model: Mapped[str] = mapped_column(String(120), default="")
    prompt_version: Mapped[str] = mapped_column(String(40), default="ea-grounded-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    conversation: Mapped[AIConversation] = relationship(back_populates="messages")
    sources: Mapped[list["SourceReference"]] = relationship(back_populates="message", cascade="all, delete-orphan", lazy="selectin")


class SourceReference(Base):
    __tablename__ = "source_references"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("ai_messages.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(40))
    object_id: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(240))
    excerpt: Mapped[str] = mapped_column(String(1000), default="")
    message: Mapped[AIMessage] = relationship(back_populates="sources")