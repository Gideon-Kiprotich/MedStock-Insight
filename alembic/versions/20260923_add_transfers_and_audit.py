"""add transfers, batches, and audit trail tables

Revision ID: 20260923_transfers_audit
Revises: 20260922_redistribution
Create Date: 2026-09-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260923_transfers_audit"
down_revision = "20260922_redistribution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Batches table
    op.create_table(
        "batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medicine_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_number", sa.String(100), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["medicine_id"], ["medicines.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("facility_id", "medicine_id", "batch_number", name="uq_batch_facility_medicine_number"),
    )
    op.create_index("ix_batches_facility_id", "batches", ["facility_id"])
    op.create_index("ix_batches_medicine_id", "batches", ["medicine_id"])
    op.create_index("ix_batches_batch_number", "batches", ["batch_number"])
    op.create_index("ix_batches_expiry_date", "batches", ["expiry_date"])

    # 2. Transfer status enum
    transfer_status_enum = postgresql.ENUM(
        "APPROVED", "IN_TRANSIT", "COMPLETED", "CANCELLED",
        name="redistribution_transfer_status", create_type=True,
    )
    bind = op.get_bind()
    transfer_status_enum.create(bind, checkfirst=True)

    # 3. Redistribution transfers table
    op.create_table(
        "redistribution_transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medicine_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", transfer_status_enum, nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recommendation_id"], ["redistribution_recommendations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["destination_facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["medicine_id"], ["medicines.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dispatched_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["received_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_redistribution_transfers_recommendation_id", "redistribution_transfers", ["recommendation_id"])
    op.create_index("ix_redistribution_transfers_source_facility_id", "redistribution_transfers", ["source_facility_id"])
    op.create_index("ix_redistribution_transfers_destination_facility_id", "redistribution_transfers", ["destination_facility_id"])
    op.create_index("ix_redistribution_transfers_medicine_id", "redistribution_transfers", ["medicine_id"])
    op.create_index("ix_redistribution_transfers_batch_id", "redistribution_transfers", ["batch_id"])
    op.create_index("ix_redistribution_transfers_status", "redistribution_transfers", ["status"])

    # 4. Audit logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_state", sa.JSON(), nullable=True),
        sa.Column("new_state", sa.JSON(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("redistribution_transfers")
    bind = op.get_bind()
    transfer_status_enum = postgresql.ENUM(
        "APPROVED", "IN_TRANSIT", "COMPLETED", "CANCELLED",
        name="redistribution_transfer_status",
    )
    transfer_status_enum.drop(bind, checkfirst=True)
    op.drop_table("batches")
