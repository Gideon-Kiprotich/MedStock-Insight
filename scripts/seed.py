"""Seed sourced Nairobi reference entities and explicitly synthetic operations.

Run after Alembic upgrade. Re-running preserves existing ledger, transfer and audit
records. For a fresh simulation use a disposable empty database, not production data.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from uuid import uuid4

from sqlalchemy import insert, select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.core import (
    Batch,
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

REFERENCE = json.loads((Path(__file__).resolve().parents[1] / "data" / "kenya_reference.json").read_text())
SEED = 20260930
DAYS = 365
PREFIX = "SYN-KENYA-"

ROLE_DEFS = {
    RoleCode.ADMINISTRATOR: ("Administrator", "System administration and configuration"),
    RoleCode.INVENTORY_OFFICER: ("Inventory Officer", "Facility inventory and transaction operations"),
    RoleCode.SUPPLY_CHAIN_MANAGER: ("Supply Chain Manager", "Supply-chain oversight and redistribution approvals"),
}
USERS = [
    ("miriam.wanjiku.demo@medstock.example", "Miriam Wanjiku", "Inventory Officer", RoleCode.INVENTORY_OFFICER, "13080"),
    ("daniel.otieno.demo@medstock.example", "Daniel Otieno", "Supply Chain Manager", RoleCode.SUPPLY_CHAIN_MANAGER, "13023"),
    ("grace.njeri.demo@medstock.example", "Grace Njeri", "Systems Administrator", RoleCode.ADMINISTRATOR, "13023"),
    ("faith.achi.demo@medstock.example", "Faith Achieng", "Inventory Officer", RoleCode.INVENTORY_OFFICER, "17411"),
    ("peter.mutua.demo@medstock.example", "Peter Mutua", "Inventory Officer", RoleCode.INVENTORY_OFFICER, "13156"),
    ("aisha.hassan.demo@medstock.example", "Aisha Hassan", "Inventory Officer", RoleCode.INVENTORY_OFFICER, "13076"),
]
PROFILES = {
    "13023": (2.1, {"Analgesics", "Antimicrobials", "Antimalarials", "Cardiovascular", "Diabetes", "Gastrointestinal", "Respiratory", "Maternal and newborn", "Mental health", "Emergency", "Dermatological"}),
    "13080": (1.5, {"Analgesics", "Antimicrobials", "Antimalarials", "Cardiovascular", "Diabetes", "Gastrointestinal", "Respiratory", "Maternal and newborn", "Emergency", "Dermatological"}),
    "17411": (1.4, {"Analgesics", "Antimicrobials", "Antimalarials", "Cardiovascular", "Diabetes", "Gastrointestinal", "Respiratory", "Maternal and newborn", "Emergency", "Dermatological"}),
    "13156": (1.0, {"Analgesics", "Antimicrobials", "Gastrointestinal", "Maternal and newborn", "Emergency", "Dermatological"}),
    "13076": (0.9, {"Analgesics", "Antimicrobials", "Gastrointestinal", "Mental health", "Emergency", "Dermatological"}),
    "34027": (0.65, {"Analgesics", "Antimicrobials", "Antimalarials", "Cardiovascular", "Diabetes", "Gastrointestinal", "Respiratory", "Emergency", "Dermatological"}),
}
SPECIALITY_BOOST = {("13076", "Mental health"): 1.8, ("13156", "Maternal and newborn"): 2.0, ("17411", "Maternal and newborn"): 1.5}
MODEL_DEFS = [
    (ForecastModelCode.MOVING_AVERAGE_7D, "7-Day Moving Average", "Moving Average", "1.0", {"window_days": 7}),
    (ForecastModelCode.RANDOM_FOREST, "Random Forest Demand Forecast", "RandomForestRegressor", "1.0", {"n_estimators": 200, "max_depth": 12, "min_samples_leaf": 2, "random_state": 42}),
]


def _rng(*parts: str) -> random.Random:
    digest = hashlib.sha256((str(SEED) + ":" + ":".join(parts)).encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _upsert(db, model, key: str, value: str, attrs: dict):
    entity = db.scalar(select(model).where(getattr(model, key) == value))
    if entity is None:
        entity = model(**attrs)
        db.add(entity)
    else:
        for name, field_value in attrs.items():
            setattr(entity, name, field_value)
    db.flush()
    return entity


def seed_reference(db):
    facilities = {}
    for row in REFERENCE["facilities"]:
        attrs = {**row, "retrieved_at": datetime.fromisoformat(row["retrieved_at"].replace("Z", "+00:00")), "is_active": True}
        facilities[row["code"]] = _upsert(db, Facility, "code", row["code"], attrs)
    medicines = {}
    for row in REFERENCE["medicines"]:
        attrs = {**row, "retrieved_at": datetime.fromisoformat(row["retrieved_at"].replace("Z", "+00:00")), "is_active": True}
        medicines[row["code"]] = _upsert(db, Medicine, "code", row["code"], attrs)
    # Legacy generic records may be referenced by old audit/transfer rows. Archive
    # rather than deleting them, then exclude inactive rows from directories.
    for old in db.scalars(select(Facility).where(Facility.code.like("FAC-%"))).all():
        old.is_active = False
    for old in db.scalars(select(Medicine).where(Medicine.code.like("MED-%"))).all():
        old.is_active = False
    return facilities, medicines


def seed_roles_users_models(db, facilities):
    roles = {}
    for code, (name, description) in ROLE_DEFS.items():
        roles[code] = _upsert(db, Role, "code", code, {"code": code, "name": name, "description": description})
    users = {}
    for email, name, title, role, facility_code in USERS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, full_name=name, title=title, role_id=roles[role].id,
                        facility_id=facilities[facility_code].id, password_hash=hash_password("ChangeMe123!"),
                        is_active=True, is_demo_user=True)
            db.add(user)
        else:
            user.full_name, user.title, user.role_id = name, title, roles[role].id
            user.facility_id, user.is_demo_user = facilities[facility_code].id, True
        db.flush()
        users[email] = user
    for code, name, algorithm, version, hyperparameters in MODEL_DEFS:
        _upsert(db, MLModelVersion, "code", code,
                {"code": code, "name": name, "algorithm": algorithm,
                 "version": version, "hyperparameters": hyperparameters, "is_active": True})
    return users


def applicable(facility_code: str, medicine: Medicine) -> bool:
    _, categories = PROFILES[facility_code]
    if medicine.category not in categories:
        return False
    if facility_code == "34027" and medicine.level_of_use and medicine.level_of_use > 4:
        return False
    if facility_code == "13156" and medicine.category == "Antimicrobials" and medicine.generic_name in {"Ceftriaxone", "Gentamicin"}:
        return False
    return True


def _tx(facility, medicine, kind, quantity, day, suffix, user_id):
    return {"id": uuid4(), "facility_id": facility.id, "medicine_id": medicine.id,
            "transaction_type": kind, "quantity": Decimal(quantity), "transaction_date": day,
            "reference_number": PREFIX + suffix, "notes": "Synthetic demonstration data; not live facility inventory.",
            "created_by": user_id}


def seed_operations(db, facilities, medicines, admin):
    exists = db.scalar(select(InventoryTransaction.id).where(InventoryTransaction.reference_number.like(PREFIX + "%")).limit(1))
    if exists:
        return False
    today = date.today()
    start = today - timedelta(days=DAYS - 1)
    tx_rows = []
    balances = {}
    base_by_pair = {}
    series = []
    for facility_code, (intensity, _) in PROFILES.items():
        facility = facilities[facility_code]
        for medicine in medicines.values():
            if not applicable(facility_code, medicine):
                continue
            series.append((facility_code, medicine.code))
            rng = _rng(facility_code, medicine.code)
            category_factor = {"Maternal and newborn": 0.8, "Mental health": 0.7,
                               "Emergency": 0.45, "Dermatological": 0.6}.get(medicine.category, 1.0)
            base = max(2, round((3 + medicine.level_of_use % 4) * intensity * category_factor * SPECIALITY_BOOST.get((facility_code, medicine.category), 1)))
            safety = Decimal(base * 12)
            base_by_pair[(facility_code, medicine.code)] = base
            policy = db.scalar(select(FacilityMedicinePolicy).where(
                FacilityMedicinePolicy.facility_id == facility.id,
                FacilityMedicinePolicy.medicine_id == medicine.id))
            if policy is None:
                db.add(FacilityMedicinePolicy(facility_id=facility.id, medicine_id=medicine.id,
                                              safety_stock=safety, reorder_point=safety + base * 7,
                                              lead_time_days=14))
            balance = Decimal(base * 25)
            tx_rows.append(_tx(facility, medicine, InventoryTransactionType.RECEIPT, balance, start,
                               f"OPEN-{facility_code}-{medicine.code}", admin.id))
            for offset in range(DAYS):
                day = start + timedelta(days=offset)
                # One deliberately simulated stockout interval per series. No real event implied.
                if offset == 150:
                    if balance > 0:
                        tx_rows.append(_tx(facility, medicine, InventoryTransactionType.ADJUSTMENT_OUT,
                                           balance, day, f"STOCKOUT-{facility_code}-{medicine.code}", admin.id))
                    balance = Decimal(0)
                if offset not in range(150, 155) and (offset % (19 + rng.randrange(5)) == 0 or balance < base * 6):
                    receipt = Decimal(base * rng.randint(16, 30))
                    tx_rows.append(_tx(facility, medicine, InventoryTransactionType.RECEIPT, receipt, day,
                                       f"RCPT-{facility_code}-{medicine.code}-{offset:03d}", admin.id))
                    balance += receipt
                weekday = [1.04, 1.12, 1.10, 1.06, 1.00, 0.80, 0.72][day.weekday()]
                seasonal = 1 + 0.12 * math.sin(2 * math.pi * day.timetuple().tm_yday / 365)
                trend = 1 + 0.08 * offset / DAYS
                event = 2.2 if offset % 97 in (42, 43) else (0.45 if offset % 83 == 20 else 1.0)
                demand = max(0, round(base * weekday * seasonal * trend * event * rng.uniform(0.72, 1.28)))
                used = Decimal(min(demand, int(balance)))
                tx_rows.append(_tx(facility, medicine, InventoryTransactionType.CONSUMPTION, used, day,
                                   f"CONS-{facility_code}-{medicine.code}-{offset:03d}", admin.id))
                balance -= used
            balances[(facility_code, medicine.code)] = balance
    # Deliberate current-state scenarios, all represented by ledger adjustments.
    by_name = {(m.generic_name, m.strength, m.dosage_form): m for m in medicines.values()}
    para = by_name[("Paracetamol", "500 mg", "Tablet")]
    high_base = base_by_pair[("13156", para.code)]
    epi = by_name[("Epinephrine (adrenaline)", "1 mg/1 mL ampoule", "Injection")]
    epi_base = base_by_pair[("13023", epi.code)]
    scenarios = [
        # Approximately eight demand days above safety stock.
        ("13156", "Paracetamol", "500 mg", "Tablet", high_base * 20),
        # Visible stock above safety, but no usable 14-day surplus.
        ("13023", "Epinephrine (adrenaline)", "1 mg/1 mL ampoule", "Injection", epi_base * 15),
        ("13023", "Paracetamol", "500 mg", "Tablet", 900),
        ("13080", "Paracetamol", "500 mg", "Tablet", 5),
        ("13023", "Amoxicillin", "500 mg", "Capsule", 700),
        ("13080", "Amoxicillin", "500 mg", "Capsule", 2),
        ("13156", "Oxytocin", "10 IU/1 mL ampoule", "Injection", 260),
        ("17411", "Oxytocin", "10 IU/1 mL ampoule", "Injection", 4),
        ("34027", "Epinephrine (adrenaline)", "1 mg/1 mL ampoule", "Injection", 0),
    ]
    # No feasible donor for epinephrine: all other network facilities retain no surplus.
    for code in PROFILES:
        if code not in {"34027", "13023"}:
            scenarios.append((code, "Epinephrine (adrenaline)", "1 mg/1 mL ampoule", "Injection", 8))
    for facility_code, name, strength, form, target in scenarios:
        medicine = by_name[(name, strength, form)]
        key = (facility_code, medicine.code)
        if key not in balances:
            continue
        delta = Decimal(target) - balances[key]
        if delta:
            kind = InventoryTransactionType.ADJUSTMENT_IN if delta > 0 else InventoryTransactionType.ADJUSTMENT_OUT
            tx_rows.append(_tx(facilities[facility_code], medicine, kind, abs(delta), today,
                               f"SCENARIO-{facility_code}-{medicine.code}", admin.id))
            balances[key] = Decimal(target)
    db.flush()
    for offset in range(0, len(tx_rows), 2000):
        db.execute(insert(InventoryTransaction), tx_rows[offset:offset + 2000])
    for (facility_code, medicine_code), balance in balances.items():
        facility, medicine = facilities[facility_code], medicines[medicine_code]
        current = db.scalar(select(InventoryBalance).where(
            InventoryBalance.facility_id == facility.id, InventoryBalance.medicine_id == medicine.id))
        if current is None:
            db.add(InventoryBalance(facility_id=facility.id, medicine_id=medicine.id, quantity_on_hand=balance))
        else:
            # The ledger includes only seed transactions for these new reference records.
            current.quantity_on_hand = balance
    return True


def seed_batches_procurement(db, facilities, medicines, admin):
    medicine = next(m for m in medicines.values() if m.generic_name == "Paracetamol" and m.strength == "500 mg")
    facility = facilities["13023"]
    if not db.scalar(select(Batch.id).where(Batch.batch_number == PREFIX + "BATCH-001")):
        db.add(Batch(facility_id=facility.id, medicine_id=medicine.id,
                     batch_number=PREFIX + "BATCH-001", expiry_date=date.today() + timedelta(days=540),
                     quantity=Decimal(300)))
    if not db.scalar(select(PurchaseOrder.id).where(PurchaseOrder.reference_number == PREFIX + "PO-001")):
        po = PurchaseOrder(facility_id=facilities["13080"].id,
                           supplier_name="Kenya Medical Supplies Authority (KEMSA) — synthetic order",
                           supplier_source_name="KEMSA official website",
                           supplier_source_url="https://kemsa.go.ke/", supplier_source_type="KEMSA",
                           expected_delivery_date=date.today() + timedelta(days=10),
                           status=PurchaseOrderStatus.CONFIRMED,
                           reference_number=PREFIX + "PO-001", created_by=admin.id)
        db.add(po)
        db.flush()
        db.add(PurchaseOrderItem(purchase_order_id=po.id, medicine_id=medicine.id,
                                 quantity_ordered=Decimal(50), quantity_received=Decimal(0)))


def seed_forecast_scenarios(db, facilities, medicines, admin):
    from fastapi import HTTPException

    from app.services.forecasting import generate_forecast
    from app.services.redistribution import generate_recommendation
    from app.services.risk import generate_risk_assessment
    by_name = {(m.generic_name, m.strength): m for m in medicines.values()}
    pairs = [("13156", "Paracetamol", "500 mg"), ("13023", "Paracetamol", "500 mg"), ("13080", "Paracetamol", "500 mg"),
             ("13023", "Amoxicillin", "500 mg"), ("13080", "Amoxicillin", "500 mg"),
             ("13156", "Oxytocin", "10 IU/1 mL ampoule"), ("17411", "Oxytocin", "10 IU/1 mL ampoule"),
             ("34027", "Epinephrine (adrenaline)", "1 mg/1 mL ampoule")]
    for code in PROFILES:
        if code != "34027":
            pairs.append((code, "Epinephrine (adrenaline)", "1 mg/1 mL ampoule"))
    for facility_code, name, strength in pairs:
        facility, medicine = facilities[facility_code], by_name[(name, strength)]
        run = generate_forecast(db, facility.id, medicine.id, ForecastModelCode.MOVING_AVERAGE_7D, 14, 90)
        generate_risk_assessment(db, facility.id, medicine.id, run.id)
    # Scenario A: the actor and approval are explicitly synthetic demonstrations.
    from app.schemas.transfers import TransferCreate
    from app.services.redistribution import decide_recommendation
    from app.services.transfer import complete_transfer, create_transfer, dispatch_transfer
    try:
        amoxicillin = by_name[("Amoxicillin", "500 mg")]
        completed = generate_recommendation(db, facilities["13080"].id, amoxicillin.id,
                                             14, admin.id)
        decide_recommendation(db, completed.id, True, admin.id,
                              "Synthetic demonstration approval; no real facility authorization.")
        transfer = create_transfer(db, TransferCreate(recommendation_id=completed.id,
                                                       quantity=min(completed.recommended_quantity, Decimal(25))), admin)
        dispatch_transfer(db, transfer.id, admin)
        complete_transfer(db, transfer.id, admin)
    except HTTPException as exc:
        print(f"Completed transfer scenario unavailable: {exc.detail}")
    # Recommendations remain pending human review; no authorization is implied.
    for facility_code, name, strength in [("13080", "Paracetamol", "500 mg"),
                                           ("17411", "Oxytocin", "10 IU/1 mL ampoule")]:
        try:
            generate_recommendation(db, facilities[facility_code].id, by_name[(name, strength)].id,
                                    14, admin.id)
        except HTTPException as exc:
            print(f"Scenario recommendation unavailable: {exc.detail}")


def main():
    with SessionLocal() as db:
        facilities, medicines = seed_reference(db)
        users = seed_roles_users_models(db, facilities)
        admin = users["grace.njeri.demo@medstock.example"]
        fresh = seed_operations(db, facilities, medicines, admin)
        seed_batches_procurement(db, facilities, medicines, admin)
        db.commit()
        if fresh:
            seed_forecast_scenarios(db, facilities, medicines, admin)
        print(f"Kenya/Nairobi reference seed: {len(facilities)} facilities, {len(medicines)} KEML formulations; "
              f"synthetic operations {'created' if fresh else 'already present'}. No live hospital data.")


if __name__ == "__main__":
    main()
