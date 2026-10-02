from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, aliased

from app.models.core import (
    Facility,
    InventoryBalance,
    Medicine,
    RedistributionRecommendation,
    RedistributionRecommendationStatus,
    RedistributionTransfer,
    RedistributionTransferStatus,
    RiskAssessment,
    RiskLevel,
)
from app.schemas.dashboard import (
    DashboardFacilitySummary,
    DashboardInventoryHealth,
    DashboardRedistributionItem,
    DashboardResponse,
    DashboardRiskItem,
    DashboardSummary,
    DashboardTransferItem,
)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_dashboard_read_model(
    db: Session,
    facility_id: UUID | None = None,
    medicine_id: UUID | None = None,
    risk_level: RiskLevel | None = None,
    transfer_status: RedistributionTransferStatus | None = None,
    recommendation_status: RedistributionRecommendationStatus | None = None,
    worklist_limit: int = 20,
) -> DashboardResponse:
    now = datetime.now(timezone.utc)

    # 1. Operational Counts
    facilities_query = select(func.count()).select_from(Facility).where(Facility.is_active.is_(True))
    if facility_id:
        facilities_query = facilities_query.where(Facility.id == facility_id)
    facilities_count = db.scalar(facilities_query) or 0

    medicines_query = select(func.count()).select_from(Medicine).where(Medicine.is_active.is_(True))
    if medicine_id:
        medicines_query = medicines_query.where(Medicine.id == medicine_id)
    medicines_tracked = db.scalar(medicines_query) or 0

    # 2. Latest Risk Assessments Query
    # Fetch risk assessments matching filters
    risk_filters = []
    if facility_id:
        risk_filters.append(RiskAssessment.facility_id == facility_id)
    if medicine_id:
        risk_filters.append(RiskAssessment.medicine_id == medicine_id)
    if risk_level:
        risk_filters.append(RiskAssessment.risk_level == risk_level)

    risk_stmt = (
        select(RiskAssessment, Facility, Medicine)
        .join(Facility, RiskAssessment.facility_id == Facility.id)
        .join(Medicine, RiskAssessment.medicine_id == Medicine.id)
        .where(Facility.is_active.is_(True), Medicine.is_active.is_(True), *risk_filters)
    )
    risk_rows = db.execute(risk_stmt).all()

    critical_count = 0
    high_count = 0
    medium_count = 0
    low_count = 0
    active_stockouts = 0

    risk_items: list[DashboardRiskItem] = []
    for risk, fac, med in risk_rows:
        if risk.risk_level == RiskLevel.CRITICAL:
            critical_count += 1
        elif risk.risk_level == RiskLevel.HIGH:
            high_count += 1
        elif risk.risk_level == RiskLevel.MEDIUM:
            medium_count += 1
        elif risk.risk_level == RiskLevel.LOW:
            low_count += 1

        if risk.currently_out_of_stock or Decimal(risk.inventory_on_hand) <= 0:
            active_stockouts += 1

        risk_items.append(
            DashboardRiskItem(
                facility_id=fac.id,
                facility_code=fac.code,
                facility_name=fac.name,
                medicine_id=med.id,
                medicine_code=med.code,
                generic_name=f"{med.generic_name} — {med.strength} {med.dosage_form}".strip(),
                current_stock=Decimal(risk.inventory_on_hand),
                safety_stock=Decimal(risk.safety_stock),
                days_until_breach=risk.days_to_breach,
                projected_stockout_date=risk.projected_stockout_date,
                risk_level=risk.risk_level,
                forecast_run_id=risk.forecast_run_id,
                assessed_at=risk.assessed_at,
                data_classification="PREDICTED",
            )
        )

    # Sort risk items deterministically by urgency (CRITICAL -> HIGH -> MEDIUM -> LOW), then days_to_breach asc
    level_order = {RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1, RiskLevel.MEDIUM: 2, RiskLevel.LOW: 3}
    risk_items.sort(
        key=lambda r: (
            level_order.get(r.risk_level, 99),
            r.days_until_breach if r.days_until_breach is not None else 9999,
            r.facility_code,
            r.medicine_code,
        )
    )
    worklist = risk_items[:worklist_limit]

    # 3. Redistribution Recommendations Queue
    rec_filters = []
    if facility_id:
        rec_filters.append(
            (RedistributionRecommendation.source_facility_id == facility_id)
            | (RedistributionRecommendation.destination_facility_id == facility_id)
        )
    if medicine_id:
        rec_filters.append(RedistributionRecommendation.medicine_id == medicine_id)
    if recommendation_status:
        rec_filters.append(RedistributionRecommendation.status == recommendation_status)
    else:
        # Default queue shows actionable recommendations
        rec_filters.append(
            RedistributionRecommendation.status.in_(
                [RedistributionRecommendationStatus.PENDING_REVIEW, RedistributionRecommendationStatus.APPROVED]
            )
        )

    SourceFac = aliased(Facility)
    DestFac = aliased(Facility)

    rec_stmt = (
        select(RedistributionRecommendation, SourceFac, DestFac, Medicine)
        .join(SourceFac, RedistributionRecommendation.source_facility_id == SourceFac.id)
        .join(DestFac, RedistributionRecommendation.destination_facility_id == DestFac.id)
        .join(Medicine, RedistributionRecommendation.medicine_id == Medicine.id)
        .where(SourceFac.is_active.is_(True), DestFac.is_active.is_(True), Medicine.is_active.is_(True), *rec_filters)
        .order_by(RedistributionRecommendation.created_at.desc())
    )
    rec_rows = db.execute(rec_stmt).all()

    redistribution_queue: list[DashboardRedistributionItem] = []
    pending_count = 0
    for rec, s_fac, d_fac, med in rec_rows:
        # Check expiration for actionable status display
        current_status = rec.status
        if current_status == RedistributionRecommendationStatus.PENDING_REVIEW:
            if _ensure_utc(rec.expires_at) <= now:
                current_status = RedistributionRecommendationStatus.EXPIRED
            else:
                pending_count += 1

        redistribution_queue.append(
            DashboardRedistributionItem(
                recommendation_id=rec.id,
                source_facility_id=s_fac.id,
                source_facility_name=s_fac.name,
                destination_facility_id=d_fac.id,
                destination_facility_name=d_fac.name,
                medicine_id=med.id,
                medicine_name=f"{med.generic_name} — {med.strength} {med.dosage_form}".strip(),
                recommended_quantity=Decimal(rec.recommended_quantity),
                source_surplus_units=Decimal(rec.source_surplus_units),
                destination_shortage_units=Decimal(rec.destination_shortage_units),
                status=current_status,
                created_at=rec.created_at,
                expires_at=rec.expires_at,
                data_classification="RECOMMENDED",
            )
        )

    # 4. Recent Transfer Activity
    transfer_filters = []
    if facility_id:
        transfer_filters.append(
            (RedistributionTransfer.source_facility_id == facility_id)
            | (RedistributionTransfer.destination_facility_id == facility_id)
        )
    if medicine_id:
        transfer_filters.append(RedistributionTransfer.medicine_id == medicine_id)
    if transfer_status:
        transfer_filters.append(RedistributionTransfer.status == transfer_status)

    transfer_stmt = (
        select(RedistributionTransfer, SourceFac, DestFac, Medicine)
        .join(SourceFac, RedistributionTransfer.source_facility_id == SourceFac.id)
        .join(DestFac, RedistributionTransfer.destination_facility_id == DestFac.id)
        .join(Medicine, RedistributionTransfer.medicine_id == Medicine.id)
        .where(SourceFac.is_active.is_(True), DestFac.is_active.is_(True), Medicine.is_active.is_(True), *transfer_filters)
        .order_by(RedistributionTransfer.created_at.desc())
        .limit(20)
    )
    transfer_rows = db.execute(transfer_stmt).all()

    recent_transfers: list[DashboardTransferItem] = []
    in_transit_count = 0
    for tr, s_fac, d_fac, med in transfer_rows:
        if tr.status == RedistributionTransferStatus.IN_TRANSIT:
            in_transit_count += 1

        recent_transfers.append(
            DashboardTransferItem(
                transfer_id=tr.id,
                recommendation_id=tr.recommendation_id,
                source_facility_id=s_fac.id,
                source_facility_name=s_fac.name,
                destination_facility_id=d_fac.id,
                destination_facility_name=d_fac.name,
                medicine_id=med.id,
                medicine_name=med.generic_name,
                quantity=Decimal(tr.quantity),
                status=tr.status,
                created_at=tr.created_at,
                dispatched_at=tr.dispatched_at,
                received_at=tr.received_at,
                data_classification="CONFIRMED",
            )
        )

    # 5. Inventory Health Aggregate
    stockout_health = active_stockouts
    at_risk_health = critical_count + high_count + medium_count
    # Healthy count is remaining tracked medicines/balances not in stockout or risk
    healthy_health = max(medicines_tracked - stockout_health - at_risk_health, 0)

    summary = DashboardSummary(
        facilities_count=facilities_count,
        medicines_tracked=medicines_tracked,
        active_stockouts=active_stockouts,
        critical_risk_count=critical_count,
        high_risk_count=high_count,
        medium_risk_count=medium_count,
        low_risk_count=low_count,
        pending_redistribution_count=pending_count,
        in_transit_transfer_count=in_transit_count,
        inventory_health=DashboardInventoryHealth(
            healthy_count=healthy_health,
            at_risk_count=at_risk_health,
            stockout_count=stockout_health,
        ),
        data_timestamp=now,
    )

    # 6. Facility Summaries
    facility_stmt = select(Facility).where(Facility.is_active.is_(True)).order_by(Facility.code)
    if facility_id:
        facility_stmt = facility_stmt.where(Facility.id == facility_id)
    active_facilities = db.scalars(facility_stmt).all()

    facility_summaries: list[DashboardFacilitySummary] = []
    for fac in active_facilities:
        # Filter risk items for this facility
        fac_risk = [r for r in risk_items if r.facility_id == fac.id]
        fac_stockout = sum(1 for r in fac_risk if r.current_stock <= 0)
        fac_crit_high = sum(1 for r in fac_risk if r.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH))
        fac_at_risk = sum(1 for r in fac_risk if r.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM))
        fac_healthy = max(len(fac_risk) - fac_stockout - fac_at_risk, 0)

        fac_pending = sum(
            1 for r in redistribution_queue if (r.source_facility_id == fac.id or r.destination_facility_id == fac.id) and r.status == RedistributionRecommendationStatus.PENDING_REVIEW
        )
        fac_in_transit = sum(
            1 for t in recent_transfers if (t.source_facility_id == fac.id or t.destination_facility_id == fac.id) and t.status == RedistributionTransferStatus.IN_TRANSIT
        )

        facility_summaries.append(
            DashboardFacilitySummary(
                facility_id=fac.id,
                facility_code=fac.code,
                facility_name=fac.name,
                tracked_medicines=len(fac_risk),
                active_stockouts=fac_stockout,
                critical_high_risk_count=fac_crit_high,
                pending_redistributions=fac_pending,
                in_transit_transfers=fac_in_transit,
                healthy_count=fac_healthy,
                at_risk_count=fac_at_risk,
                stockout_count=fac_stockout,
            )
        )

    return DashboardResponse(
        summary=summary,
        risk_worklist=worklist,
        redistribution_queue=redistribution_queue,
        recent_transfers=recent_transfers,
        facility_summaries=facility_summaries,
    )
