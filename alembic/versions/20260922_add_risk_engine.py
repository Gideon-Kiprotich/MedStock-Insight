"""add purchase order and stockout risk tables

Revision ID: 20260922_risk
Revises: 20260922_forecasting
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260922_risk"
down_revision = "20260922_forecasting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    purchase_status = postgresql.ENUM(
        "DRAFT", "CONFIRMED", "PARTIALLY_RECEIVED", "RECEIVED", "CANCELLED",
        name="purchase_order_status", create_type=True
    )
    risk_level = postgresql.ENUM(
        "CRITICAL", "HIGH", "MEDIUM", "LOW", name="risk_level", create_type=True
    )
    bind = op.get_bind()
    purchase_status.create(bind, checkfirst=True)
    risk_level.create(bind, checkfirst=True)

    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_name", sa.String(length=200), nullable=True),
        sa.Column("expected_delivery_date", sa.Date(), nullable=False),
        sa.Column("status", purchase_status, nullable=False),
        sa.Column("reference_number", sa.String(length=100), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("reference_number", name="uq_purchase_orders_reference_number"),
    )
    op.create_index("ix_purchase_orders_facility_id", "purchase_orders", ["facility_id"])
    op.create_index("ix_purchase_orders_expected_delivery_date", "purchase_orders", ["expected_delivery_date"])

    op.create_table(
        "purchase_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medicine_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_ordered", sa.Numeric(14, 2), nullable=False),
        sa.Column("quantity_received", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["medicine_id"], ["medicines.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("purchase_order_id", "medicine_id", name="uq_po_item_medicine"),
    )
    op.create_index("ix_purchase_order_items_purchase_order_id", "purchase_order_items", ["purchase_order_id"])
    op.create_index("ix_purchase_order_items_medicine_id", "purchase_order_items", ["medicine_id"])

    op.create_table(
        "risk_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medicine_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("forecast_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("risk_level", risk_level, nullable=False),
        sa.Column("currently_out_of_stock", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("days_to_breach", sa.Integer(), nullable=True),
        sa.Column("projected_breach_date", sa.Date(), nullable=True),
        sa.Column("projected_stockout_date", sa.Date(), nullable=True),
        sa.Column("projected_shortage_units", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("inventory_on_hand", sa.Numeric(14, 2), nullable=False),
        sa.Column("safety_stock", sa.Numeric(14, 2), nullable=False),
        sa.Column("reorder_point", sa.Numeric(14, 2), nullable=False),
        sa.Column("incoming_stock_quantity", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("forecast_horizon_days", sa.Integer(), nullable=False),
        sa.Column("calculation_version", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["medicine_id"], ["medicines.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["forecast_run_id"], ["forecast_runs.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_risk_assessments_facility_id", "risk_assessments", ["facility_id"])
    op.create_index("ix_risk_assessments_medicine_id", "risk_assessments", ["medicine_id"])
    op.create_index("ix_risk_assessments_forecast_run_id", "risk_assessments", ["forecast_run_id"])
    op.create_index("ix_risk_assessments_assessed_at", "risk_assessments", ["assessed_at"])
    op.create_index("ix_risk_assessments_risk_level", "risk_assessments", ["risk_level"])


def downgrade() -> None:
    op.drop_index("ix_risk_assessments_risk_level", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_assessed_at", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_forecast_run_id", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_medicine_id", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_facility_id", table_name="risk_assessments")
    op.drop_table("risk_assessments")
    op.drop_index("ix_purchase_order_items_medicine_id", table_name="purchase_order_items")
    op.drop_index("ix_purchase_order_items_purchase_order_id", table_name="purchase_order_items")
    op.drop_table("purchase_order_items")
    op.drop_index("ix_purchase_orders_expected_delivery_date", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_facility_id", table_name="purchase_orders")
    op.drop_table("purchase_orders")
    bind = op.get_bind()
    postgresql.ENUM(name="risk_level").drop(bind, checkfirst=True)
    postgresql.ENUM(name="purchase_order_status").drop(bind, checkfirst=True)
