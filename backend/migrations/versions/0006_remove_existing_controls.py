"""Remove the obsolete existing-controls field and clear generated mitigation titles."""

from alembic import op
import sqlalchemy as sa

revision = "0006_remove_existing_controls"
down_revision = "0005_mitigation_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("architecture_risks") as batch:
        batch.drop_column("existing_controls")
    op.execute("UPDATE risk_mitigations SET title = '' WHERE title = 'Treatment plan' AND description = '' AND status = 'Draft'")


def downgrade() -> None:
    with op.batch_alter_table("architecture_risks") as batch:
        batch.add_column(sa.Column("existing_controls", sa.String(length=2000), nullable=False, server_default=""))