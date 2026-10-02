"""Add sourced reference data and synthetic user metadata.

Revision ID: 20260930_kenya_reference
Revises: 20260923_transfers_audit
"""
import sqlalchemy as sa

from alembic import op

revision = "20260930_kenya_reference"
down_revision = "20260923_transfers_audit"
branch_labels = None
depends_on = None

FACILITY_COLUMNS = {
    "official_name": sa.String(200), "display_name": sa.String(200),
    "kmhfr_code": sa.String(30), "sub_county": sa.String(100), "ward": sa.String(100),
    "latitude": sa.Float(), "longitude": sa.Float(), "keph_level": sa.String(50),
    "ownership_category": sa.String(100), "operational_status": sa.String(50),
    "service_24_hour": sa.Boolean(), "weekend_service": sa.Boolean(),
    "bed_capacity": sa.Integer(), "maternity_beds": sa.Integer(),
    "icu_beds": sa.Integer(), "hdu_beds": sa.Integer(),
    "emergency_beds": sa.Integer(), "cots": sa.Integer(), "key_services": sa.JSON(),
    "reference_note": sa.Text(),
    "source_name": sa.String(150), "source_url": sa.Text(),
    "source_type": sa.String(50), "source_record_id": sa.String(100),
    "source_version": sa.String(50), "retrieved_at": sa.DateTime(timezone=True),
    "verification_status": sa.String(50),
}
MEDICINE_COLUMNS = {
    "keml_section": sa.String(30), "level_of_use": sa.Integer(),
    "aware_classification": sa.String(30), "restricted": sa.Boolean(),
    "keml_notes": sa.Text(), "source_name": sa.String(150),
    "source_url": sa.Text(), "source_type": sa.String(50),
    "source_record_id": sa.String(100), "source_version": sa.String(50),
    "retrieved_at": sa.DateTime(timezone=True),
    "verification_status": sa.String(50),
}

def upgrade() -> None:
    for name, column_type in FACILITY_COLUMNS.items():
        op.add_column("facilities", sa.Column(name, column_type, nullable=True))
    op.add_column("facilities", sa.Column("transfer_eligible", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("uq_facilities_kmhfr_code", "facilities", ["kmhfr_code"], unique=True)
    for name, column_type in MEDICINE_COLUMNS.items():
        op.add_column("medicines", sa.Column(name, column_type, nullable=True))
    for name, column_type in {"supplier_source_name": sa.String(150), "supplier_source_url": sa.Text(), "supplier_source_type": sa.String(50)}.items():
        op.add_column("purchase_orders", sa.Column(name, column_type, nullable=True))
    op.add_column("users", sa.Column("title", sa.String(100), nullable=True))
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("facility_id", sa.UUID(), nullable=True))
        batch_op.create_foreign_key("fk_users_facility_id_facilities", "facilities", ["facility_id"], ["id"])
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("is_demo_user", sa.Boolean(), nullable=False, server_default=sa.false()))

def downgrade() -> None:
    for name in ("is_demo_user", "last_login_at"):
        op.drop_column("users", name)
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_facility_id_facilities", type_="foreignkey")
        batch_op.drop_column("facility_id")
    op.drop_column("users", "title")
    for name in ("supplier_source_type", "supplier_source_url", "supplier_source_name"):
        op.drop_column("purchase_orders", name)
    for name in reversed(list(MEDICINE_COLUMNS)):
        op.drop_column("medicines", name)
    op.drop_index("uq_facilities_kmhfr_code", table_name="facilities")
    op.drop_column("facilities", "transfer_eligible")
    for name in reversed(list(FACILITY_COLUMNS)):
        op.drop_column("facilities", name)
