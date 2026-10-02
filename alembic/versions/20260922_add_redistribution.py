"""add redistribution recommendation tables

Revision ID: 20260922_redistribution
Revises: 20260922_risk
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260922_redistribution"
down_revision = "20260922_risk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    status_enum = postgresql.ENUM(
        "PENDING_REVIEW", "APPROVED", "REJECTED", "EXPIRED", "CANCELLED",
        name="redistribution_recommendation_status", create_type=True,
    )
    bind = op.get_bind()
    status_enum.create(bind, checkfirst=True)

    with op.batch_alter_table("inventory_balances") as batch_op:
        batch_op.create_unique_constraint(
            "uq_inventory_balance_facility_medicine",
            ["facility_id", "medicine_id"],
        )

    op.create_table(
        "redistribution_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("source_facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medicine_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_risk_assessment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("planning_horizon_days", sa.Integer(), nullable=False),
        sa.Column("source_surplus_units", sa.Numeric(14, 2), nullable=False),
        sa.Column("destination_shortage_units", sa.Numeric(14, 2), nullable=False),
        sa.Column("recommended_quantity", sa.Numeric(14, 2), nullable=False),
        sa.Column("source_inventory_before", sa.Numeric(14, 2), nullable=False),
        sa.Column("destination_inventory_before", sa.Numeric(14, 2), nullable=False),
        sa.Column("source_safety_stock", sa.Numeric(14, 2), nullable=False),
        sa.Column("destination_safety_stock", sa.Numeric(14, 2), nullable=False),
        sa.Column("source_projected_end_inventory", sa.Numeric(14, 2), nullable=False),
        sa.Column("destination_projected_end_inventory", sa.Numeric(14, 2), nullable=False),
        sa.Column("constraint_results", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["destination_facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["medicine_id"], ["medicines.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["destination_risk_assessment_id"], ["risk_assessments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_redistribution_recommendations_source_facility_id", "redistribution_recommendations", ["source_facility_id"])
    op.create_index("ix_redistribution_recommendations_destination_facility_id", "redistribution_recommendations", ["destination_facility_id"])
    op.create_index("ix_redistribution_recommendations_medicine_id", "redistribution_recommendations", ["medicine_id"])
    op.create_index("ix_redist_recom_dest_risk_id", "redistribution_recommendations", ["destination_risk_assessment_id"])
    op.create_index("ix_redistribution_recommendations_status", "redistribution_recommendations", ["status"])
    op.create_index("ix_redistribution_recommendations_expires_at", "redistribution_recommendations", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_redistribution_recommendations_expires_at", table_name="redistribution_recommendations")
    op.drop_index("ix_redistribution_recommendations_status", table_name="redistribution_recommendations")
    op.drop_index("ix_redist_recom_dest_risk_id", table_name="redistribution_recommendations")
    op.drop_index("ix_redistribution_recommendations_medicine_id", table_name="redistribution_recommendations")
    op.drop_index("ix_redistribution_recommendations_destination_facility_id", table_name="redistribution_recommendations")
    op.drop_index("ix_redistribution_recommendations_source_facility_id", table_name="redistribution_recommendations")
    op.drop_table("redistribution_recommendations")
    op.drop_constraint("uq_inventory_balance_facility_medicine", "inventory_balances", type_="unique")
    bind = op.get_bind()
    postgresql.ENUM(name="redistribution_recommendation_status").drop(bind, checkfirst=True)
