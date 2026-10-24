"""Add architecture studies and risks."""

from alembic import op
import sqlalchemy as sa

revision = "0002_studies_risks"
down_revision = "0001_identity_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "architecture_studies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("identifier", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("business_context", sa.String(length=4000), nullable=False),
        sa.Column("business_objectives", sa.String(length=4000), nullable=False),
        sa.Column("scope", sa.String(length=4000), nullable=False),
        sa.Column("out_of_scope", sa.String(length=4000), nullable=False),
        sa.Column("architecture_domain", sa.String(length=120), nullable=False),
        sa.Column("project_reference", sa.String(length=120), nullable=False),
        sa.Column("lead_architect_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("confidentiality", sa.String(length=40), nullable=False),
        sa.Column("target_review_date", sa.Date(), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("identifier", name="uq_architecture_studies_identifier"),
    )
    op.create_index("ix_architecture_studies_identifier", "architecture_studies", ["identifier"], unique=True)
    op.create_index("ix_architecture_studies_lead_architect_id", "architecture_studies", ["lead_architect_id"])
    op.create_index("ix_architecture_studies_status", "architecture_studies", ["status"])
    op.create_table(
        "architecture_risks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("identifier", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(length=4000), nullable=False),
        sa.Column("cause", sa.String(length=2000), nullable=False),
        sa.Column("risk_event", sa.String(length=2000), nullable=False),
        sa.Column("consequences", sa.String(length=2000), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("family", sa.String(length=120), nullable=False),
        sa.Column("architecture_domain", sa.String(length=120), nullable=False),
        sa.Column("probability", sa.Integer(), nullable=False),
        sa.Column("impact", sa.Integer(), nullable=False),
        sa.Column("residual_probability", sa.Integer(), nullable=True),
        sa.Column("residual_impact", sa.Integer(), nullable=True),
        sa.Column("existing_controls", sa.String(length=2000), nullable=False),
        sa.Column("control_effectiveness", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("treatment_strategy", sa.String(length=40), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("study_id", sa.Integer(), sa.ForeignKey("architecture_studies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("detection_date", sa.Date(), nullable=True),
        sa.Column("target_resolution_date", sa.Date(), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("identifier", name="uq_architecture_risks_identifier"),
    )
    op.create_index("ix_architecture_risks_identifier", "architecture_risks", ["identifier"], unique=True)
    op.create_index("ix_architecture_risks_status", "architecture_risks", ["status"])
    op.create_index("ix_architecture_risks_owner_id", "architecture_risks", ["owner_id"])
    op.create_index("ix_architecture_risks_study_id", "architecture_risks", ["study_id"])


def downgrade() -> None:
    op.drop_index("ix_architecture_risks_study_id", table_name="architecture_risks")
    op.drop_index("ix_architecture_risks_owner_id", table_name="architecture_risks")
    op.drop_index("ix_architecture_risks_status", table_name="architecture_risks")
    op.drop_index("ix_architecture_risks_identifier", table_name="architecture_risks")
    op.drop_table("architecture_risks")
    op.drop_index("ix_architecture_studies_status", table_name="architecture_studies")
    op.drop_index("ix_architecture_studies_lead_architect_id", table_name="architecture_studies")
    op.drop_index("ix_architecture_studies_identifier", table_name="architecture_studies")
    op.drop_table("architecture_studies")