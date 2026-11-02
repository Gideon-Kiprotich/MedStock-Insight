"""Add persisted, non-secret application settings."""

import uuid

import sqlalchemy as sa

from alembic import op

revision = "20261102_settings"
down_revision = "20261002_analytics"
branch_labels = None
depends_on = None

SETTINGS_ID = uuid.UUID("8a767f26-9c2f-4f56-9c43-1a2d4b8d9e10")


def upgrade():
    table = op.create_table(
        "system_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "forecast_default_horizon_days",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
        sa.Column(
            "reporting_default_days",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.CheckConstraint(
            "forecast_default_horizon_days IN (7, 14, 30)",
            name="ck_system_settings_forecast_horizon",
        ),
        sa.CheckConstraint(
            "reporting_default_days IN (7, 30, 90)",
            name="ck_system_settings_reporting_days",
        ),
    )
    op.bulk_insert(
        table,
        [
            {
                "id": SETTINGS_ID,
                "forecast_default_horizon_days": 30,
                "reporting_default_days": 30,
                "updated_by": None,
            }
        ],
    )


def downgrade():
    op.drop_table("system_settings")
