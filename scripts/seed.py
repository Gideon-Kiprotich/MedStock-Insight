from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.core import (
    Facility,
    FacilityMedicinePolicy,
    ForecastModelCode,
    InventoryBalance,
    InventoryTransaction,
    InventoryTransactionType,
    Medicine,
    MLModelVersion,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Role,
    RoleCode,
    User,
)

ROLE_DEFS = {
    RoleCode.ADMINISTRATOR: ("Administrator", "System administration and configuration"),
    RoleCode.INVENTORY_OFFICER: ("Inventory Officer", "Facility inventory and transaction operations"),
    RoleCode.SUPPLY_CHAIN_MANAGER: ("Supply Chain Manager", "Supply-chain oversight and redistribution approvals"),
}

FACILITIES = [
    ("FAC-001", "Demo Facility North", "Demo County", "Hospital"),
    ("FAC-002", "Demo Facility Central", "Demo County", "Health Centre"),
    ("FAC-003", "Demo Facility South", "Demo County", "Hospital"),
]

MEDICINES = [
    ("MED-001", "Paracetamol", "500 mg", "Tablet", "Analgesic", "tablet"),
    ("MED-002", "Amoxicillin", "500 mg", "Capsule", "Antibiotic", "capsule"),
    ("MED-003", "Artemether/Lumefantrine", "20/120 mg", "Tablet", "Antimalarial", "tablet"),
]

MODEL_DEFS = [
    (
        ForecastModelCode.MOVING_AVERAGE_7D,
        "7-Day Moving Average",
        "Moving Average",
        "1.0",
        {"window_days": 7},
    ),
    (
        ForecastModelCode.RANDOM_FOREST,
        "Random Forest Demand Forecast",
        "RandomForestRegressor",
        "1.0",
        {"n_estimators": 200, "max_depth": 12, "min_samples_leaf": 2, "random_state": 42},
    ),
]


def add_demo_consumption(db, admin_id, facilities, medicines) -> None:
    start = date.today() - timedelta(days=89)
    existing = db.scalar(select(InventoryTransaction.id).limit(1))
    if existing is not None:
        return

    for f_idx, facility in enumerate(facilities, start=1):
        for m_idx, medicine in enumerate(medicines, start=1):
            initial_stock = Decimal("1800")
            db.add(
                InventoryTransaction(
                    facility_id=facility.id,
                    medicine_id=medicine.id,
                    transaction_type=InventoryTransactionType.RECEIPT,
                    quantity=initial_stock,
                    transaction_date=start,
                    reference_number=f"DEMO-RECEIPT-{facility.code}-{medicine.code}",
                    notes="Simulated demonstration stock; not live facility data.",
                    created_by=admin_id,
                )
            )
            balance = initial_stock
            for day_offset in range(90):
                current_day = start + timedelta(days=day_offset)
                weekday_effect = [1, 2, 3, 1, 2, -2, -3][current_day.weekday()]
                trend = day_offset // 30
                quantity = Decimal(str(8 + (f_idx * 2) + (m_idx * 2) + weekday_effect + trend))
                quantity = max(quantity, Decimal("2"))
                db.add(
                    InventoryTransaction(
                        facility_id=facility.id,
                        medicine_id=medicine.id,
                        transaction_type=InventoryTransactionType.CONSUMPTION,
                        quantity=quantity,
                        transaction_date=current_day,
                        reference_number=f"DEMO-CONS-{facility.code}-{medicine.code}-{day_offset:03d}",
                        notes="Simulated daily consumption for forecasting demonstration.",
                        created_by=admin_id,
                    )
                )
                balance -= quantity

            inventory = db.scalar(
                select(InventoryBalance).where(
                    InventoryBalance.facility_id == facility.id,
                    InventoryBalance.medicine_id == medicine.id,
                )
            )
            if inventory is None:
                inventory = InventoryBalance(
                    facility_id=facility.id,
                    medicine_id=medicine.id,
                    quantity_on_hand=max(balance, Decimal("0")),
                )
                db.add(inventory)
            else:
                inventory.quantity_on_hand = max(balance, Decimal("0"))


with SessionLocal() as db:
    roles = {}
    for code, (name, description) in ROLE_DEFS.items():
        role = db.scalar(select(Role).where(Role.code == code))
        if role is None:
            role = Role(code=code, name=name, description=description)
            db.add(role)
            db.flush()
        roles[code] = role

    admin = db.scalar(select(User).where(User.email == "admin@medstock.local"))
    if admin is None:
        admin = User(
            email="admin@medstock.local",
            full_name="Demo Administrator",
            password_hash=hash_password("ChangeMe123!"),
            role_id=roles[RoleCode.ADMINISTRATOR].id,
        )
        db.add(admin)
        db.flush()

    facilities = []
    for code, name, county, facility_type in FACILITIES:
        facility = db.scalar(select(Facility).where(Facility.code == code))
        if facility is None:
            facility = Facility(code=code, name=name, county=county, facility_type=facility_type)
            db.add(facility)
            db.flush()
        facilities.append(facility)

    medicines = []
    for code, generic_name, strength, dosage_form, category, unit in MEDICINES:
        medicine = db.scalar(select(Medicine).where(Medicine.code == code))
        if medicine is None:
            medicine = Medicine(
                code=code,
                generic_name=generic_name,
                strength=strength,
                dosage_form=dosage_form,
                category=category,
                unit_of_measure=unit,
            )
            db.add(medicine)
            db.flush()
        medicines.append(medicine)

    for facility in facilities:
        for medicine in medicines:
            policy = db.scalar(
                select(FacilityMedicinePolicy).where(
                    FacilityMedicinePolicy.facility_id == facility.id,
                    FacilityMedicinePolicy.medicine_id == medicine.id,
                )
            )
            if policy is None:
                policy = FacilityMedicinePolicy(
                    facility_id=facility.id,
                    medicine_id=medicine.id,
                    safety_stock=Decimal("250"),
                    reorder_point=Decimal("400"),
                    lead_time_days=14,
                )
                db.add(policy)

    for code, name, algorithm, version, hyperparameters in MODEL_DEFS:
        model = db.scalar(select(MLModelVersion).where(MLModelVersion.code == code))
        if model is None:
            db.add(
                MLModelVersion(
                    code=code,
                    name=name,
                    algorithm=algorithm,
                    version=version,
                    hyperparameters=hyperparameters,
                    is_active=True,
                )
            )

    db.flush()
    add_demo_consumption(db, admin.id, facilities, medicines)

    po = db.scalar(select(PurchaseOrder).where(PurchaseOrder.reference_number == "DEMO-PO-FAC-001-MED-001"))
    if po is None:
        po = PurchaseOrder(
            facility_id=facilities[0].id,
            supplier_name="Demo Supplier",
            expected_delivery_date=date.today() + timedelta(days=10),
            status=PurchaseOrderStatus.CONFIRMED,
            reference_number="DEMO-PO-FAC-001-MED-001",
            created_by=admin.id,
        )
        db.add(po)
        db.flush()
        db.add(
            PurchaseOrderItem(
                purchase_order_id=po.id,
                medicine_id=medicines[0].id,
                quantity_ordered=Decimal("600"),
                quantity_received=Decimal("0"),
            )
        )
    db.commit()
    print("Demo seed complete. All facility and consumption data is simulated and not live facility data.")
