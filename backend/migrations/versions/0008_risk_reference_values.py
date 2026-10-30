"""Add configurable risk object, source, and scope reference values."""

from alembic import op
import sqlalchemy as sa

revision = "0008_risk_reference_values"
down_revision = "0007_risk_dashboard_domains"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "risk_reference_values",
        sa.Column("id", sa.String(length=60), primary_key=True),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("label_en", sa.String(length=160), nullable=False),
        sa.Column("label_fr", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("category", "code", name="uq_risk_reference_values_category_code"),
    )
    op.create_index("ix_risk_reference_values_category", "risk_reference_values", ["category"])


def downgrade() -> None:
    op.drop_index("ix_risk_reference_values_category", table_name="risk_reference_values")
    op.drop_table("risk_reference_values")
