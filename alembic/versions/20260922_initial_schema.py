"""initial schema

Revision ID: initial_20260922
Revises:
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "initial_20260922"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    role_code = postgresql.ENUM(
        "ADMINISTRATOR",
        "INVENTORY_OFFICER",
        "SUPPLY_CHAIN_MANAGER",
        name="role_code",
        create_type=True,
    )
    inventory_transaction_type = postgresql.ENUM(
        "RECEIPT",
        "CONSUMPTION",
        "ADJUSTMENT_IN",
        "ADJUSTMENT_OUT",
        "TRANSFER_IN",
        "TRANSFER_OUT",
        name="inventory_transaction_type",
        create_type=True,
    )
    bind = op.get_bind()
    role_code.create(bind, checkfirst=True)
    inventory_transaction_type.create(bind, checkfirst=True)

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", role_code, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )

    op.create_table(
        "facilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("county", sa.String(length=100), nullable=True),
        sa.Column("facility_type", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_facilities_code"),
    )
    op.create_index("ix_facilities_code", "facilities", ["code"])

    op.create_table(
        "medicines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("generic_name", sa.String(length=200), nullable=False),
        sa.Column("strength", sa.String(length=100), nullable=True),
        sa.Column("dosage_form", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("unit_of_measure", sa.String(length=30), nullable=False, server_default="unit"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_medicines_code"),
    )
    op.create_index("ix_medicines_code", "medicines", ["code"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "facility_medicine_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medicine_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("safety_stock", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("reorder_point", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("lead_time_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["medicine_id"], ["medicines.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_facility_medicine_policies_facility_id",
        "facility_medicine_policies",
        ["facility_id"],
    )
    op.create_index(
        "ix_facility_medicine_policies_medicine_id",
        "facility_medicine_policies",
        ["medicine_id"],
    )

    op.create_table(
        "inventory_balances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medicine_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_on_hand", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["medicine_id"], ["medicines.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_inventory_balances_facility_id", "inventory_balances", ["facility_id"])
    op.create_index("ix_inventory_balances_medicine_id", "inventory_balances", ["medicine_id"])

    op.create_table(
        "inventory_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medicine_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_type", inventory_transaction_type, nullable=False),
        sa.Column("quantity", sa.Numeric(14, 2), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("reference_number", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["medicine_id"], ["medicines.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_inventory_transactions_facility_id", "inventory_transactions", ["facility_id"])
    op.create_index("ix_inventory_transactions_medicine_id", "inventory_transactions", ["medicine_id"])
    op.create_index("ix_inventory_transactions_transaction_date", "inventory_transactions", ["transaction_date"])


def downgrade() -> None:
    op.drop_index("ix_inventory_transactions_transaction_date", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_medicine_id", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_facility_id", table_name="inventory_transactions")
    op.drop_table("inventory_transactions")
    op.drop_index("ix_inventory_balances_medicine_id", table_name="inventory_balances")
    op.drop_index("ix_inventory_balances_facility_id", table_name="inventory_balances")
    op.drop_table("inventory_balances")
    op.drop_index("ix_facility_medicine_policies_medicine_id", table_name="facility_medicine_policies")
    op.drop_index("ix_facility_medicine_policies_facility_id", table_name="facility_medicine_policies")
    op.drop_table("facility_medicine_policies")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_medicines_code", table_name="medicines")
    op.drop_table("medicines")
    op.drop_index("ix_facilities_code", table_name="facilities")
    op.drop_table("facilities")
    op.drop_table("roles")
    bind = op.get_bind()
    postgresql.ENUM(name="inventory_transaction_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="role_code").drop(bind, checkfirst=True)
