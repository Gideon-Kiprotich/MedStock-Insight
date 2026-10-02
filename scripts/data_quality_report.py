"""Print measured reference and synthetic data quality metrics after seeding."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.core import (
    Facility,
    FacilityMedicinePolicy,
    InventoryTransaction,
    InventoryTransactionType,
    Medicine,
    RedistributionRecommendation,
    RedistributionTransfer,
    Role,
    User,
)


def main():
    with SessionLocal() as db:
        facilities = db.scalars(select(Facility).where(Facility.source_type == "KMHFR")).all()
        medicines = db.scalars(select(Medicine).where(Medicine.source_type == "KEML")).all()
        users = db.scalars(select(User).where(User.is_demo_user.is_(True))).all()
        roles = {r.id: r.code.value for r in db.scalars(select(Role)).all()}
        bounds = db.execute(select(func.min(InventoryTransaction.transaction_date),
                                   func.max(InventoryTransaction.transaction_date))
                            .where(InventoryTransaction.reference_number.like("SYN-KENYA-%"))).one()
        consumption = db.scalar(select(func.count()).select_from(InventoryTransaction).where(
            InventoryTransaction.transaction_type == InventoryTransactionType.CONSUMPTION,
            InventoryTransaction.reference_number.like("SYN-KENYA-%"))) or 0
        stockouts = db.scalar(select(func.count()).select_from(InventoryTransaction).where(
            (InventoryTransaction.reference_number.like("SYN-KENYA-STOCKOUT-%") |
             (InventoryTransaction.reference_number.like("SYN-KENYA-ADJUSTMENT_OUT-%") &
              (InventoryTransaction.reference_number.like("%-150") |
               InventoryTransaction.reference_number.like("%-515")))))) or 0
        series = db.scalar(select(func.count()).select_from(FacilityMedicinePolicy).join(
            Facility, FacilityMedicinePolicy.facility_id == Facility.id).where(Facility.source_type == "KMHFR")) or 0
        print("# Kenya/Nairobi data quality report")
        print("\n## SOURCE-VERIFIED REFERENCE DATA")
        print(f"Facilities: {len(facilities)}; KMHFR source coverage: {sum(bool(f.source_url and f.source_record_id) for f in facilities)}/{len(facilities)}")
        print(f"Ownership: {dict(Counter(f.ownership_category for f in facilities))}")
        print(f"KEPH levels: {dict(Counter(f.keph_level for f in facilities))}")
        print(f"Prototype transfer network: {', '.join(f.name for f in facilities if f.transfer_eligible)}")
        print(f"Medicine formulations: {len(medicines)}; distinct name/form/strength combinations: {len({(m.generic_name, m.dosage_form, m.strength) for m in medicines})}")
        print(f"KEML source coverage: {sum(bool(m.source_url and m.keml_section) for m in medicines)}/{len(medicines)}")
        print(f"Categories: {dict(Counter(m.category for m in medicines))}")
        print(f"AWaRe populated: {sum(bool(m.aware_classification) for m in medicines)}/{len(medicines)}")
        print("Facility source: KMHFR public records, retrieved 2026-09-30; medicine source: KEML 2023, retrieved 2026-09-30.")
        print("Supplier identity: KEMSA official website, retrieved 2026-09-30; the purchase order is synthetic.")
        print("\n## SYNTHETIC DEMONSTRATION DATA")
        print(f"Daily consumption dates: {bounds[0]} to {bounds[1]}; observations: {consumption}")
        print(f"Medicine-facility series: {series}; distinct operational facilities: {sum(f.transfer_eligible for f in facilities)}")
        print(f"Deliberate historical stockout events: {stockouts}")
        print(f"Redistribution recommendations: {db.scalar(select(func.count()).select_from(RedistributionRecommendation)) or 0}; transfers: {db.scalar(select(func.count()).select_from(RedistributionTransfer)) or 0}")
        print("Configured synthetic redistribution scenarios: 4 (completed flow, multiple shortages, no feasible donor, safety-stock cap)")
        print(f"Demo users: {len(users)}; roles: {dict(Counter(roles.get(u.role_id) for u in users))}")
        print(f"Facility assignment: {dict(Counter(next((f.name for f in facilities if f.id == u.facility_id), 'Unassigned') for u in users))}")
        print("No real staff, patient, inventory, consumption, procurement or transfer activity is represented.")


if __name__ == "__main__":
    main()
