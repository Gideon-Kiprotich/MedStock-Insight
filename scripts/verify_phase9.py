"""Read-only verification of the six synthetic demonstration scenarios."""
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.core import (
    Facility,
    FacilityMedicinePolicy,
    InventoryBalance,
    Medicine,
    RedistributionRecommendation,
    RedistributionRecommendationStatus,
    RiskAssessment,
    RiskLevel,
)
from app.services.redistribution import get_surplus_candidates


def main():
    with SessionLocal() as db:
        facilities = {row.code: row for row in db.scalars(select(Facility))}
        medicines = {(row.generic_name, row.strength): row for row in db.scalars(select(Medicine))}
        para = medicines["Paracetamol", "500 mg"]
        epi = medicines["Epinephrine (adrenaline)", "1 mg/1 mL ampoule"]

        def row(model, code, medicine):
            return db.scalar(select(model).where(
                model.facility_id == facilities[code].id, model.medicine_id == medicine.id
            ).order_by(*( [model.assessed_at.desc()] if model is RiskAssessment else [] )))

        critical, high, shortage = row(RiskAssessment, "13080", para), row(RiskAssessment, "13156", para), row(RiskAssessment, "34027", epi)
        donor = row(InventoryBalance, "13023", epi)
        safety = row(FacilityMedicinePolicy, "13023", epi)
        para_surplus = get_surplus_candidates(db, para.id, 14)
        epi_surplus = get_surplus_candidates(db, epi.id, 14)
        recommendation = db.scalar(select(RedistributionRecommendation).where(
            RedistributionRecommendation.source_facility_id == facilities["13023"].id,
            RedistributionRecommendation.destination_facility_id == facilities["13080"].id,
            RedistributionRecommendation.medicine_id == para.id,
            RedistributionRecommendation.status == RedistributionRecommendationStatus.PENDING_REVIEW,
        ))
        checks = [
            ("DEMO_CRITICAL_SHORTAGE", "Mbagathi", "Paracetamol 500 mg",
             critical is not None and critical.risk_level == RiskLevel.CRITICAL,
             f"risk={critical.risk_level.value if critical else 'missing'}, days={critical.days_to_breach if critical else 'missing'}"),
            ("DEMO_HIGH_RISK", "Pumwani", "Paracetamol 500 mg",
             high is not None and high.risk_level == RiskLevel.HIGH,
             f"risk={high.risk_level.value if high else 'missing'}, days={high.days_to_breach if high else 'missing'}"),
            ("DEMO_SURPLUS_DONOR", "Kenyatta", "Paracetamol 500 mg",
             any(p.facility_id == facilities["13023"].id for p in para_surplus),
             f"usable_surplus={next((p.available_surplus for p in para_surplus if p.facility_id == facilities['13023'].id), 0)}"),
            ("DEMO_REDISTRIBUTION", "Kenyatta to Mbagathi", "Paracetamol 500 mg",
             recommendation is not None and recommendation.recommended_quantity > 0,
             f"pending_quantity={recommendation.recommended_quantity if recommendation else 'missing'}"),
            ("DEMO_NO_FEASIBLE_DONOR", "Nairobi East", "Epinephrine 1 mg/mL",
             shortage is not None and shortage.projected_shortage_units > 0 and not epi_surplus,
             f"shortage={shortage.projected_shortage_units if shortage else 'missing'}, donors={len(epi_surplus)}"),
            ("DEMO_SAFETY_STOCK_CONSTRAINT", "Kenyatta", "Epinephrine 1 mg/mL",
             donor is not None and safety is not None and
             Decimal(donor.quantity_on_hand) > Decimal(safety.safety_stock) and not epi_surplus,
             f"stock={donor.quantity_on_hand if donor else 'missing'}, safety={safety.safety_stock if safety else 'missing'}, usable_surplus=0"),
        ]
        print(json.dumps([{"scenario": name, "facility": facility, "medicine": medicine,
                           "passed": bool(passed), "observed": observed}
                          for name, facility, medicine, passed, observed in checks], indent=2, default=str))
        if not all(passed for _, _, _, passed, _ in checks):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
