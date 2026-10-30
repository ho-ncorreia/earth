"""Add risk taxonomy, help definitions, and risk register associations."""

from alembic import op
import sqlalchemy as sa

revision = "0004_risk_taxonomy_catalog"
down_revision = "0003_decisions_assistant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "risk_taxonomy_families",
        sa.Column("id", sa.String(length=3), primary_key=True),
        sa.Column("name_en", sa.String(length=160), nullable=False),
        sa.Column("name_fr", sa.String(length=160), nullable=False),
    )
    op.create_table(
        "risk_taxonomy_types",
        sa.Column("id", sa.String(length=6), primary_key=True),
        sa.Column("family_id", sa.String(length=3), sa.ForeignKey("risk_taxonomy_families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label_en", sa.String(length=240), nullable=False),
        sa.Column("label_fr", sa.String(length=240), nullable=False),
    )
    op.create_index("ix_risk_taxonomy_types_family_id", "risk_taxonomy_types", ["family_id"])
    op.create_table(
        "risk_help_definitions",
        sa.Column("id", sa.String(length=12), primary_key=True),
        sa.Column("risk_code", sa.String(length=12), nullable=False, unique=True),
        sa.Column("risk_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("subfamily_id", sa.String(length=6), sa.ForeignKey("risk_taxonomy_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title_en", sa.String(length=240), nullable=False),
        sa.Column("title_fr", sa.String(length=240), nullable=False),
        sa.Column("description_en", sa.String(length=4000), nullable=False),
        sa.Column("description_fr", sa.String(length=4000), nullable=False, server_default=""),
        sa.Column("causes", sa.JSON(), nullable=False),
        sa.Column("causes_fr", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("impacts", sa.JSON(), nullable=False),
        sa.Column("impacts_fr", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("data_quality_notes", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_risk_help_definitions_risk_code", "risk_help_definitions", ["risk_code"], unique=True)
    op.create_index("ix_risk_help_definitions_subfamily_id", "risk_help_definitions", ["subfamily_id"])
    for table_name, id_column, extra_columns in (
        ("risk_objects", "risk_object_id", [sa.Column("object_type", sa.String(length=80), nullable=False), sa.Column("object_ref", sa.String(length=240), nullable=False)]),
        ("risk_sources", "risk_source_id", [sa.Column("source_type", sa.String(length=80), nullable=False), sa.Column("source_ref", sa.String(length=240), nullable=False)]),
        ("risk_scopes", "risk_scope_id", [sa.Column("scope_type", sa.String(length=80), nullable=False), sa.Column("scope_ref", sa.String(length=240), nullable=False)]),
        ("risk_assessments", "assessment_id", [sa.Column("assessment_type", sa.String(length=20), nullable=False), sa.Column("probability", sa.Integer(), nullable=False), sa.Column("impact", sa.Integer(), nullable=False)]),
        ("risk_mitigations", "mitigation_id", [sa.Column("description", sa.String(length=2000), nullable=False), sa.Column("status", sa.String(length=40), nullable=False)]),
    ):
        columns = [sa.Column(id_column, sa.String(length=36), primary_key=True), sa.Column("risk_id", sa.Integer(), sa.ForeignKey("architecture_risks.id", ondelete="CASCADE"), nullable=False), *extra_columns]
        constraints = [sa.UniqueConstraint("risk_id", "assessment_type", name="uq_risk_assessments_type")] if table_name == "risk_assessments" else []
        op.create_table(table_name, *columns, *constraints)
        op.create_index(f"ix_{table_name}_risk_id", table_name, ["risk_id"])
    with op.batch_alter_table("architecture_risks") as batch:
        batch.add_column(sa.Column("family_id", sa.String(length=3), nullable=True))
        batch.add_column(sa.Column("subfamily_id", sa.String(length=6), nullable=True))
        batch.add_column(sa.Column("risk_definition_id", sa.String(length=12), nullable=True))
        batch.create_foreign_key("fk_risks_family_id", "risk_taxonomy_families", ["family_id"], ["id"], ondelete="SET NULL")
        batch.create_foreign_key("fk_risks_subfamily_id", "risk_taxonomy_types", ["subfamily_id"], ["id"], ondelete="SET NULL")
        batch.create_foreign_key("fk_risks_definition_id", "risk_help_definitions", ["risk_definition_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("architecture_risks") as batch:
        batch.drop_constraint("fk_risks_definition_id", type_="foreignkey")
        batch.drop_constraint("fk_risks_subfamily_id", type_="foreignkey")
        batch.drop_constraint("fk_risks_family_id", type_="foreignkey")
        batch.drop_column("risk_definition_id")
        batch.drop_column("subfamily_id")
        batch.drop_column("family_id")
    for table_name in ("risk_mitigations", "risk_assessments", "risk_scopes", "risk_sources", "risk_objects"):
        op.drop_index(f"ix_{table_name}_risk_id", table_name=table_name)
        op.drop_table(table_name)
    op.drop_index("ix_risk_help_definitions_subfamily_id", table_name="risk_help_definitions")
    op.drop_index("ix_risk_help_definitions_risk_code", table_name="risk_help_definitions")
    op.drop_table("risk_help_definitions")
    op.drop_index("ix_risk_taxonomy_types_family_id", table_name="risk_taxonomy_types")
    op.drop_table("risk_taxonomy_types")
    op.drop_table("risk_taxonomy_families")