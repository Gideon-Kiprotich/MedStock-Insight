"""Separate reproducible analytical snapshots from operational records."""

import sqlalchemy as sa

from alembic import op

revision = "20261002_analytics"
down_revision = "20260930_kenya_reference"
branch_labels = None
depends_on = None


def upgrade():
    # SQLite assigns NUMERIC affinity to the PostgreSQL type name UUID; rare
    # hexadecimal IDs resembling scientific notation can then lose precision.
    # CHAR(32) retains the same UUID contract. PostgreSQL remains native UUID.
    if op.get_bind().dialect.name == "sqlite":
        # Snapshot the Phase 9 columns; migration behavior must not depend on
        # ORM models added by a future release.
        uuid_columns = {
            "facilities": ["id"],
            "medicines": ["id"],
            "ml_model_versions": ["id"],
            "roles": ["id"],
            "batches": ["id", "facility_id", "medicine_id"],
            "facility_medicine_policies": ["id", "facility_id", "medicine_id"],
            "forecast_runs": ["id", "facility_id", "medicine_id", "model_version_id"],
            "inventory_balances": ["id", "facility_id", "medicine_id"],
            "users": ["id", "role_id", "facility_id"],
            "audit_logs": ["id", "user_id", "entity_id"],
            "forecast_points": ["id", "forecast_run_id"],
            "inventory_transactions": ["id", "facility_id", "medicine_id", "created_by"],
            "purchase_orders": ["id", "facility_id", "created_by"],
            "risk_assessments": ["id", "facility_id", "medicine_id", "forecast_run_id"],
            "purchase_order_items": ["id", "purchase_order_id", "medicine_id"],
            "redistribution_recommendations": [
                "id",
                "source_facility_id",
                "destination_facility_id",
                "medicine_id",
                "destination_risk_assessment_id",
                "created_by",
                "reviewed_by",
            ],
            "redistribution_transfers": [
                "id",
                "recommendation_id",
                "source_facility_id",
                "destination_facility_id",
                "medicine_id",
                "batch_id",
                "approved_by",
                "dispatched_by",
                "received_by",
                "cancelled_by",
            ],
        }
        # Reject existing numeric coercion before rebuilding any table. A cast
        # cannot recover the original 128-bit identifier after precision loss.
        for table, columns in uuid_columns.items():
            for column in columns:
                invalid = op.get_bind().scalar(
                    sa.text(
                        f'SELECT count(*) FROM "{table}" WHERE "{column}" IS NOT NULL '
                        f'AND typeof("{column}") != :uuid_storage'
                    ),
                    {"uuid_storage": "text"},
                )
                if invalid:
                    raise RuntimeError(
                        "Existing SQLite UUID data was numerically coerced. "
                        "Restore an intact backup, or seed a separate empty demonstration database."
                    )
        for table, columns in uuid_columns.items():
            with op.batch_alter_table(table) as batch:
                for column in columns:
                    batch.alter_column(column, type_=sa.Uuid())
    op.create_table(
        "analytical_experiments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
    )
    op.create_index("ix_analytical_experiments_kind", "analytical_experiments", ["kind"])


def downgrade():
    op.drop_table("analytical_experiments")
