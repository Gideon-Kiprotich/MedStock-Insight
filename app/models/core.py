from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RoleCode(str, enum.Enum):
    ADMINISTRATOR = "ADMINISTRATOR"
    INVENTORY_OFFICER = "INVENTORY_OFFICER"
    SUPPLY_CHAIN_MANAGER = "SUPPLY_CHAIN_MANAGER"


class InventoryTransactionType(str, enum.Enum):
    RECEIPT = "RECEIPT"
    CONSUMPTION = "CONSUMPTION"
    ADJUSTMENT_IN = "ADJUSTMENT_IN"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"


class ForecastModelCode(str, enum.Enum):
    MOVING_AVERAGE_7D = "MOVING_AVERAGE_7D"
    RANDOM_FOREST = "RANDOM_FOREST"


class ForecastRunStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PurchaseOrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class RiskLevel(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RedistributionRecommendationStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class RedistributionTransferStatus(str, enum.Enum):
    APPROVED = "APPROVED"
    IN_TRANSIT = "IN_TRANSIT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    role: Mapped[Role] = relationship(back_populates="users")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[RoleCode] = mapped_column(SAEnum(RoleCode, name="role_code"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    users: Mapped[list[User]] = relationship(back_populates="role")


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    county: Mapped[str | None] = mapped_column(String(100))
    facility_type: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Medicine(Base):
    __tablename__ = "medicines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    generic_name: Mapped[str] = mapped_column(String(200), nullable=False)
    strength: Mapped[str | None] = mapped_column(String(100))
    dosage_form: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(100))
    unit_of_measure: Mapped[str] = mapped_column(String(30), nullable=False, default="unit")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FacilityMedicinePolicy(Base):
    __tablename__ = "facility_medicine_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False
    )
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False
    )
    safety_stock: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    reorder_point: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InventoryBalance(Base):
    __tablename__ = "inventory_balances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False
    )
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False
    )
    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("facility_id", "medicine_id", name="uq_inventory_balance_facility_medicine"),
    )


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False
    )
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id", ondelete="RESTRICT"), nullable=False
    )
    transaction_type: Mapped[InventoryTransactionType] = mapped_column(
        SAEnum(InventoryTransactionType, name="inventory_transaction_type"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MLModelVersion(Base):
    __tablename__ = "ml_model_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[ForecastModelCode] = mapped_column(
        SAEnum(ForecastModelCode, name="forecast_model_code"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(150), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    hyperparameters: Mapped[dict | None] = mapped_column(JSON)
    evaluation_metrics: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ml_model_versions.id", ondelete="RESTRICT"), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    forecast_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    training_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    training_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    data_points_used: Mapped[int] = mapped_column(Integer, nullable=False)
    mae: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    status: Mapped[ForecastRunStatus] = mapped_column(
        SAEnum(ForecastRunStatus, name="forecast_run_status"), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)


class ForecastPoint(Base):
    __tablename__ = "forecast_points"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    forecast_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forecast_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    predicted_demand: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    lower_bound: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    upper_bound: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))

    __table_args__ = (UniqueConstraint("forecast_run_id", "target_date", name="uq_forecast_point_run_date"),)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    supplier_name: Mapped[str | None] = mapped_column(String(200))
    expected_delivery_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        SAEnum(PurchaseOrderStatus, name="purchase_order_status"), nullable=False
    )
    reference_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity_ordered: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    __table_args__ = (UniqueConstraint("purchase_order_id", "medicine_id", name="uq_po_item_medicine"),)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    forecast_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forecast_runs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    risk_level: Mapped[RiskLevel] = mapped_column(
        SAEnum(RiskLevel, name="risk_level"), nullable=False, index=True
    )
    currently_out_of_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    days_to_breach: Mapped[int | None] = mapped_column(Integer)
    projected_breach_date: Mapped[date | None] = mapped_column(Date)
    projected_stockout_date: Mapped[date | None] = mapped_column(Date)
    projected_shortage_units: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    inventory_on_hand: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    safety_stock: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    reorder_point: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    incoming_stock_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    forecast_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(50), nullable=False)



class RedistributionRecommendation(Base):
    __tablename__ = "redistribution_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    destination_facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    destination_risk_assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_assessments.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    status: Mapped[RedistributionRecommendationStatus] = mapped_column(
        SAEnum(
            RedistributionRecommendationStatus,
            name="redistribution_recommendation_status",
        ),
        nullable=False,
        index=True,
    )
    planning_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    source_surplus_units: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    destination_shortage_units: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    recommended_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    source_inventory_before: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    destination_inventory_before: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    source_safety_stock: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    destination_safety_stock: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    source_projected_end_inventory: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    destination_projected_end_inventory: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    constraint_results: Mapped[dict] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    facility: Mapped[Facility] = relationship()
    medicine: Mapped[Medicine] = relationship()

    __table_args__ = (
        UniqueConstraint("facility_id", "medicine_id", "batch_number", name="uq_batch_facility_medicine_number"),
    )


class RedistributionTransfer(Base):
    __tablename__ = "redistribution_transfers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("redistribution_recommendations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    destination_facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("batches.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[RedistributionTransferStatus] = mapped_column(
        SAEnum(RedistributionTransferStatus, name="redistribution_transfer_status"),
        nullable=False,
        default=RedistributionTransferStatus.APPROVED,
        index=True,
    )
    approved_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dispatched_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    source_facility: Mapped[Facility] = relationship(foreign_keys=[source_facility_id])
    destination_facility: Mapped[Facility] = relationship(foreign_keys=[destination_facility_id])
    medicine: Mapped[Medicine] = relationship()
    batch: Mapped[Batch | None] = relationship()
    recommendation: Mapped[RedistributionRecommendation] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    previous_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    user: Mapped[User | None] = relationship()


