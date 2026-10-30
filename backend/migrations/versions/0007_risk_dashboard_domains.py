"""Add architecture-domain reference data and align the risk workflow."""

from alembic import op
import sqlalchemy as sa

revision = "0007_risk_dashboard_domains"
down_revision = "0006_remove_existing_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "architecture_domains",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_architecture_domains_name"),
    )
    op.create_index("ix_architecture_domains_name", "architecture_domains", ["name"])
    with op.batch_alter_table("architecture_studies") as batch:
        batch.add_column(sa.Column("architecture_domain_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_architecture_studies_domain", "architecture_domains", ["architecture_domain_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_architecture_studies_architecture_domain_id", ["architecture_domain_id"])
    op.execute("UPDATE architecture_risks SET status = 'Open' WHERE status IN ('Identified', 'Assessed', 'Treatment Defined')")
    op.execute("UPDATE architecture_risks SET status = 'In Progress' WHERE status IN ('Mitigation in Progress', 'Monitoring')")
    op.execute("UPDATE architecture_risks SET status = 'Closed' WHERE status = 'Accepted'")


def downgrade() -> None:
    op.execute("UPDATE architecture_risks SET status = 'Identified' WHERE status = 'Open'")
    op.execute("UPDATE architecture_risks SET status = 'Mitigation in Progress' WHERE status = 'In Progress'")
    with op.batch_alter_table("architecture_studies") as batch:
        batch.drop_index("ix_architecture_studies_architecture_domain_id")
        batch.drop_constraint("fk_architecture_studies_domain", type_="foreignkey")
        batch.drop_column("architecture_domain_id")
    op.drop_index("ix_architecture_domains_name", table_name="architecture_domains")
    op.drop_table("architecture_domains")
