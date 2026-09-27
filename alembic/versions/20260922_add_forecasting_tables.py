"""add forecasting tables

Revision ID: 20260922_forecasting
Revises:
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260922_forecasting"
down_revision = "initial_20260922"
branch_labels = None
depends_on = None


def upgrade() -> None:
    forecast_model_code = postgresql.ENUM(
        "MOVING_AVERAGE_7D",
        "RANDOM_FOREST",
        name="forecast_model_code",
        create_type=True,
    )
    forecast_run_status = postgresql.ENUM(
        "COMPLETED",
        "FAILED",
        name="forecast_run_status",
        create_type=True,
    )
    bind = op.get_bind()
    forecast_model_code.create(bind, checkfirst=True)
    forecast_run_status.create(bind, checkfirst=True)

    op.create_table(
        "ml_model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", forecast_model_code, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("algorithm", sa.String(length=150), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("hyperparameters", sa.JSON(), nullable=True),
        sa.Column("evaluation_metrics", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_ml_model_versions_code"),
    )

    op.create_table(
        "forecast_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medicine_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("forecast_start_date", sa.Date(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("training_start_date", sa.Date(), nullable=False),
        sa.Column("training_end_date", sa.Date(), nullable=False),
        sa.Column("data_points_used", sa.Integer(), nullable=False),
        sa.Column("mae", sa.Numeric(14, 4), nullable=True),
        sa.Column("status", forecast_run_status, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["medicine_id"], ["medicines.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["model_version_id"], ["ml_model_versions.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_forecast_runs_facility_id", "forecast_runs", ["facility_id"])
    op.create_index("ix_forecast_runs_medicine_id", "forecast_runs", ["medicine_id"])
    op.create_index("ix_forecast_runs_generated_at", "forecast_runs", ["generated_at"])

    op.create_table(
        "forecast_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("forecast_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("predicted_demand", sa.Numeric(14, 4), nullable=False),
        sa.Column("lower_bound", sa.Numeric(14, 4), nullable=True),
        sa.Column("upper_bound", sa.Numeric(14, 4), nullable=True),
        sa.ForeignKeyConstraint(["forecast_run_id"], ["forecast_runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("forecast_run_id", "target_date", name="uq_forecast_point_run_date"),
    )
    op.create_index("ix_forecast_points_forecast_run_id", "forecast_points", ["forecast_run_id"])


def downgrade() -> None:
    op.drop_index("ix_forecast_points_forecast_run_id", table_name="forecast_points")
    op.drop_table("forecast_points")
    op.drop_index("ix_forecast_runs_generated_at", table_name="forecast_runs")
    op.drop_index("ix_forecast_runs_medicine_id", table_name="forecast_runs")
    op.drop_index("ix_forecast_runs_facility_id", table_name="forecast_runs")
    op.drop_table("forecast_runs")
    op.drop_table("ml_model_versions")
    bind = op.get_bind()
    postgresql.ENUM(name="forecast_run_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="forecast_model_code").drop(bind, checkfirst=True)
