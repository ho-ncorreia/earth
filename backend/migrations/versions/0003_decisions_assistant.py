"""Add architecture decisions and grounded assistant history."""

from alembic import op
import sqlalchemy as sa

revision = "0003_decisions_assistant"
down_revision = "0002_studies_risks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "architecture_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("number", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("context", sa.String(length=4000), nullable=False),
        sa.Column("problem_statement", sa.String(length=4000), nullable=False),
        sa.Column("decision_drivers", sa.String(length=3000), nullable=False),
        sa.Column("selected_option", sa.String(length=240), nullable=False),
        sa.Column("decision_rationale", sa.String(length=4000), nullable=False),
        sa.Column("positive_consequences", sa.String(length=3000), nullable=False),
        sa.Column("negative_consequences", sa.String(length=3000), nullable=False),
        sa.Column("assumptions", sa.String(length=3000), nullable=False),
        sa.Column("constraints", sa.String(length=3000), nullable=False),
        sa.Column("principles", sa.String(length=2000), nullable=False),
        sa.Column("patterns_and_standards", sa.String(length=2000), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("decision_authority", sa.String(length=240), nullable=False),
        sa.Column("rejection_rationale", sa.String(length=2000), nullable=False),
        sa.Column("decision_date", sa.Date(), nullable=True),
        sa.Column("review_date", sa.Date(), nullable=True),
        sa.Column("superseded_by_id", sa.Integer(), sa.ForeignKey("architecture_decisions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("number", name="uq_architecture_decisions_number"),
    )
    op.create_index("ix_architecture_decisions_number", "architecture_decisions", ["number"], unique=True)
    op.create_index("ix_architecture_decisions_status", "architecture_decisions", ["status"])
    op.create_index("ix_architecture_decisions_owner_id", "architecture_decisions", ["owner_id"])
    op.create_table(
        "decision_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("decision_id", sa.Integer(), sa.ForeignKey("architecture_decisions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(length=3000), nullable=False),
        sa.Column("advantages", sa.String(length=2000), nullable=False),
        sa.Column("disadvantages", sa.String(length=2000), nullable=False),
    )
    op.create_index("ix_decision_options_decision_id", "decision_options", ["decision_id"])
    op.create_table(
        "decision_studies",
        sa.Column("decision_id", sa.Integer(), sa.ForeignKey("architecture_decisions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("study_id", sa.Integer(), sa.ForeignKey("architecture_studies.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "decision_risks",
        sa.Column("decision_id", sa.Integer(), sa.ForeignKey("architecture_decisions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("risk_id", sa.Integer(), sa.ForeignKey("architecture_risks.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "decision_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("decision_id", sa.Integer(), sa.ForeignKey("architecture_decisions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("decision_id", "version", name="uq_decision_versions_number"),
    )
    op.create_index("ix_decision_versions_decision_id", "decision_versions", ["decision_id"])
    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_conversations_owner_id", "ai_conversations", ["owner_id"])
    op.create_table(
        "ai_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.String(length=12000), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_messages_conversation_id", "ai_messages", ["conversation_id"])
    op.create_table(
        "source_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("ai_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("object_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("excerpt", sa.String(length=1000), nullable=False),
    )
    op.create_index("ix_source_references_message_id", "source_references", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_source_references_message_id", table_name="source_references")
    op.drop_table("source_references")
    op.drop_index("ix_ai_messages_conversation_id", table_name="ai_messages")
    op.drop_table("ai_messages")
    op.drop_index("ix_ai_conversations_owner_id", table_name="ai_conversations")
    op.drop_table("ai_conversations")
    op.drop_index("ix_decision_versions_decision_id", table_name="decision_versions")
    op.drop_table("decision_versions")
    op.drop_table("decision_risks")
    op.drop_table("decision_studies")
    op.drop_index("ix_decision_options_decision_id", table_name="decision_options")
    op.drop_table("decision_options")
    op.drop_index("ix_architecture_decisions_owner_id", table_name="architecture_decisions")
    op.drop_index("ix_architecture_decisions_status", table_name="architecture_decisions")
    op.drop_index("ix_architecture_decisions_number", table_name="architecture_decisions")
    op.drop_table("architecture_decisions")