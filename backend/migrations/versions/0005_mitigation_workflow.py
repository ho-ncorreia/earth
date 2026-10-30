"""Add mitigation approval workflow, attachments, settings, and study links."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0005_mitigation_workflow"
down_revision = "0004_risk_taxonomy_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    study_columns = {column["name"] for column in inspector.get_columns("architecture_studies")}
    missing_study_columns = [
        column for name, column in (
            ("jira_jpd_url", sa.Column("jira_jpd_url", sa.String(length=1000), nullable=False, server_default="")),
            ("confluence_url", sa.Column("confluence_url", sa.String(length=1000), nullable=False, server_default="")),
        ) if name not in study_columns
    ]
    if missing_study_columns:
        with op.batch_alter_table("architecture_studies") as batch:
            for column in missing_study_columns:
                batch.add_column(column)

    mitigation_columns = {column["name"] for column in inspector.get_columns("risk_mitigations")}
    missing_mitigation_columns = [
        column for name, column in (
            ("title", sa.Column("title", sa.String(length=240), nullable=False, server_default="")),
            ("residual_probability", sa.Column("residual_probability", sa.Integer(), nullable=True)),
            ("residual_impact", sa.Column("residual_impact", sa.Integer(), nullable=True)),
            ("treatment_strategy", sa.Column("treatment_strategy", sa.String(length=40), nullable=False, server_default="Reduce")),
            ("control_effectiveness", sa.Column("control_effectiveness", sa.String(length=40), nullable=False, server_default="Unknown")),
            ("submitted_at", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True)),
            ("validated_at", sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True)),
            ("validated_by_id", sa.Column("validated_by_id", sa.Integer(), nullable=True)),
            ("validation_comment", sa.Column("validation_comment", sa.String(length=2000), nullable=False, server_default="")),
            ("updated_at", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)),
        ) if name not in mitigation_columns
    ]
    mitigation_fks = {fk["name"] for fk in inspector.get_foreign_keys("risk_mitigations")}
    needs_rebuild = bool(missing_mitigation_columns or "fk_risk_mitigations_validated_by" not in mitigation_fks)
    if needs_rebuild:
        with op.batch_alter_table("risk_mitigations") as batch:
            for column in missing_mitigation_columns:
                batch.add_column(column)
            if "fk_risk_mitigations_validated_by" not in mitigation_fks:
                batch.create_foreign_key("fk_risk_mitigations_validated_by", "users", ["validated_by_id"], ["id"], ondelete="SET NULL")
    op.execute("UPDATE risk_mitigations SET status = 'Draft' WHERE status NOT IN ('Approved', 'Submitted', 'Rejected')")
    op.execute("UPDATE risk_mitigations SET title = 'Treatment plan' WHERE title = ''")
    inspector = inspect(op.get_bind())
    existing_indexes = {index["name"] for index in inspector.get_indexes("risk_mitigations")}
    if "ix_risk_mitigations_status" not in existing_indexes:
        op.create_index("ix_risk_mitigations_status", "risk_mitigations", ["status"])
    if not inspector.has_table("risk_mitigation_attachments"):
        op.create_table(
            "risk_mitigation_attachments",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("mitigation_id", sa.String(length=36), sa.ForeignKey("risk_mitigations.mitigation_id", ondelete="CASCADE"), nullable=False),
            sa.Column("file_name", sa.String(length=255), nullable=False),
            sa.Column("storage_name", sa.String(length=80), nullable=False, unique=True),
            sa.Column("content_type", sa.String(length=120), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("uploaded_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    inspector = inspect(op.get_bind())
    if "ix_risk_mitigation_attachments_mitigation_id" not in {index["name"] for index in inspector.get_indexes("risk_mitigation_attachments")}:
        op.create_index("ix_risk_mitigation_attachments_mitigation_id", "risk_mitigation_attachments", ["mitigation_id"])
    if not inspector.has_table("risk_mitigation_reviews"):
        op.create_table(
            "risk_mitigation_reviews",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("mitigation_id", sa.String(length=36), sa.ForeignKey("risk_mitigations.mitigation_id", ondelete="CASCADE"), nullable=False),
            sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("decision", sa.String(length=20), nullable=False),
            sa.Column("comment", sa.String(length=2000), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    inspector = inspect(op.get_bind())
    if "ix_risk_mitigation_reviews_mitigation_id" not in {index["name"] for index in inspector.get_indexes("risk_mitigation_reviews")}:
        op.create_index("ix_risk_mitigation_reviews_mitigation_id", "risk_mitigation_reviews", ["mitigation_id"])
    if not inspector.has_table("risk_configuration"):
        op.create_table(
            "risk_configuration",
            sa.Column("key", sa.String(length=80), primary_key=True),
            sa.Column("value", sa.String(length=240), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    configuration_exists = op.get_bind().execute(sa.text("SELECT 1 FROM risk_configuration WHERE key = 'mitigation_validation_stale_days'")).first()
    if not configuration_exists:
        op.execute("INSERT INTO risk_configuration (key, value, updated_at) VALUES ('mitigation_validation_stale_days', '365', CURRENT_TIMESTAMP)")


def downgrade() -> None:
    op.drop_table("risk_configuration")
    op.drop_index("ix_risk_mitigation_reviews_mitigation_id", table_name="risk_mitigation_reviews")
    op.drop_table("risk_mitigation_reviews")
    op.drop_index("ix_risk_mitigation_attachments_mitigation_id", table_name="risk_mitigation_attachments")
    op.drop_table("risk_mitigation_attachments")
    op.drop_index("ix_risk_mitigations_status", table_name="risk_mitigations")
    with op.batch_alter_table("risk_mitigations") as batch:
        batch.drop_constraint("fk_risk_mitigations_validated_by", type_="foreignkey")
        batch.drop_column("updated_at")
        batch.drop_column("validation_comment")
        batch.drop_column("validated_by_id")
        batch.drop_column("validated_at")
        batch.drop_column("submitted_at")
        batch.drop_column("control_effectiveness")
        batch.drop_column("treatment_strategy")
        batch.drop_column("residual_impact")
        batch.drop_column("residual_probability")
        batch.drop_column("title")
    with op.batch_alter_table("architecture_studies") as batch:
        batch.drop_column("confluence_url")
        batch.drop_column("jira_jpd_url")
