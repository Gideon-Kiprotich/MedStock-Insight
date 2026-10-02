"""Integration checks for a disposable seeded Kenya demonstration database."""
from __future__ import annotations

import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from app.db.session import SessionLocal
from app.main import app
from app.models.core import (
    AuditLog,
    Facility,
    ForecastRun,
    InventoryBalance,
    InventoryTransaction,
    InventoryTransactionType,
    Medicine,
    RedistributionRecommendation,
    RedistributionTransfer,
    RedistributionTransferStatus,
    RiskAssessment,
    User,
)
from app.services.redistribution import generate_recommendation


def main():
    with SessionLocal() as db:
        assert not any("patient" in table for table in inspect(db.bind).get_table_names())
        facilities = {f.code: f for f in db.scalars(select(Facility).where(Facility.source_type == "KMHFR"))}
        medicines = db.scalars(select(Medicine).where(Medicine.source_type == "KEML")).all()
        assert len(facilities) == 9 and len(medicines) == 51
        assert all(f.source_url and f.source_record_id for f in facilities.values())
        assert all(m.source_url and m.keml_section and m.strength and m.dosage_form for m in medicines)
        assert sum(f.transfer_eligible for f in facilities.values()) == 6
        assert all(not f.transfer_eligible for f in facilities.values() if f.ownership_category == "Private Practice")
        assert db.scalars(select(User).where(User.is_demo_user.is_(True))).all()
        assert db.scalar(select(ForecastRun.id).limit(1))
        assert db.scalar(select(RiskAssessment.id).limit(1))
        transfer = db.scalar(select(RedistributionTransfer).where(
            RedistributionTransfer.status == RedistributionTransferStatus.COMPLETED))
        assert transfer is not None
        actions = {a.action for a in db.scalars(select(AuditLog).where(AuditLog.entity_id == transfer.id))}
        assert {"TRANSFER_CREATED", "TRANSFER_DISPATCHED", "TRANSFER_COMPLETED"}.issubset(actions)
        deltas = defaultdict(Decimal)
        for tx in db.scalars(select(InventoryTransaction).where(
            InventoryTransaction.reference_number.like("SYN-KENYA-%"))):
            assert tx.quantity >= 0
            sign = 1 if tx.transaction_type in (InventoryTransactionType.RECEIPT,
                InventoryTransactionType.ADJUSTMENT_IN, InventoryTransactionType.TRANSFER_IN) else -1
            deltas[(tx.facility_id, tx.medicine_id)] += sign * tx.quantity
        # Completed transfer movements use their own reference prefix.
        for tx in db.scalars(select(InventoryTransaction).where(
            InventoryTransaction.reference_number.like("TRANSFER-%"))):
            sign = 1 if tx.transaction_type == InventoryTransactionType.TRANSFER_IN else -1
            deltas[(tx.facility_id, tx.medicine_id)] += sign * tx.quantity
        for balance in db.scalars(select(InventoryBalance)):
            if (balance.facility_id, balance.medicine_id) in deltas:
                assert balance.quantity_on_hand == deltas[(balance.facility_id, balance.medicine_id)]
        epi = next(m for m in medicines if m.generic_name == "Epinephrine (adrenaline)")
        manager = db.scalar(select(User).where(User.email == "daniel.otieno.demo@medstock.example"))
        try:
            generate_recommendation(db, facilities["34027"].id, epi.id, 14, manager.id)
        except HTTPException as exc:
            assert exc.status_code == 422 and "NO_FEASIBLE_DONOR" in str(exc.detail)
        else:
            raise AssertionError("No-donor scenario unexpectedly created a recommendation")
        oxytocin = next(m for m in medicines if m.generic_name == "Oxytocin")
        oxytocin_rec = db.scalar(select(RedistributionRecommendation).where(
            RedistributionRecommendation.medicine_id == oxytocin.id))
        assert oxytocin_rec and oxytocin_rec.recommended_quantity <= oxytocin_rec.source_surplus_units
        assert oxytocin_rec.source_projected_end_inventory - oxytocin_rec.recommended_quantity >= oxytocin_rec.source_safety_stock
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/login", json={
            "email": "grace.njeri.demo@medstock.example", "password": "ChangeMe123!"})
        assert response.status_code == 200, response.text
        headers = {"Authorization": "Bearer " + response.json()["access_token"]}
        facility_response = client.get("/api/v1/facilities?page_size=100", headers=headers)
        medicine_response = client.get("/api/v1/medicines?page_size=100", headers=headers)
        dashboard_response = client.get("/api/v1/dashboard", headers=headers)
        users_response = client.get("/api/v1/users/demo", headers=headers)
        assert facility_response.status_code == medicine_response.status_code == dashboard_response.status_code == 200
        assert len(facility_response.json()["data"]) == 9
        assert len(medicine_response.json()["data"]) == 51
        assert all(not f["code"].startswith("FAC-") for f in facility_response.json()["data"])
        assert all(not m["code"].startswith("MED-") for m in medicine_response.json()["data"])
        assert dashboard_response.json()["summary"]["facilities_count"] == 9
        assert users_response.status_code == 200 and len(users_response.json()) == 6
        assert all(person["is_demo_user"] and person["facility_name"] and "password" not in person for person in users_response.json())
        officer_login = client.post("/api/v1/auth/login", json={"email": "miriam.wanjiku.demo@medstock.example", "password": "ChangeMe123!"})
        assert officer_login.status_code == 200
        officer_headers = {"Authorization": "Bearer " + officer_login.json()["access_token"]}
        assert client.get("/api/v1/users/demo", headers=officer_headers).status_code == 403
    print("Kenya integration checks passed: provenance, ledger, no-donor, safety cap, transfer/audit, auth and API.")


if __name__ == "__main__":
    main()
