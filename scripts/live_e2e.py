"""Live regression against an explicitly supplied, disposable local demo API."""

import argparse
import json
import os
from datetime import date
from decimal import Decimal
from urllib.parse import urlparse
from uuid import uuid4

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    if urlparse(args.base_url).hostname not in {"127.0.0.1", "localhost"}:
        parser.error("Use a disposable local demonstration API")
    admin_password = os.environ.get("MEDSTOCK_E2E_ADMIN_PASSWORD")
    officer_password = os.environ.get("MEDSTOCK_E2E_OFFICER_PASSWORD")
    if not admin_password or not officer_password:
        parser.error("Set MEDSTOCK_E2E_ADMIN_PASSWORD and MEDSTOCK_E2E_OFFICER_PASSWORD")
    with httpx.Client(base_url=args.base_url.rstrip("/") + "/api/v1", timeout=120) as client:

        def call(method, path, payload=None, expected=200, headers=None):
            response = client.request(method, path, json=payload, headers=headers)
            assert response.status_code == expected, (path, response.status_code, response.text)
            return response.json()

        token = call(
            "POST",
            "/auth/login",
            {"email": "grace.njeri.demo@medstock.example", "password": admin_password},
        )["access_token"]
        client.headers["Authorization"] = "Bearer " + token
        assert call("GET", "/auth/me")["role"]["code"] == "ADMINISTRATOR"
        facilities = {f["code"]: f for f in call("GET", "/facilities?page_size=100")["data"]}
        medicines = call("GET", "/medicines?page_size=100")["data"]
        medicine = next(
            m
            for m in medicines
            if m["generic_name"] == "Paracetamol"
            and m["strength"] == "500 mg"
            and m["dosage_form"] == "Tablet"
        )
        donor, dest = facilities["13023"]["id"], facilities["13080"]["id"]
        mid = medicine["id"]

        def balance(facility):
            rows = call("GET", f"/inventory?facility_id={facility}&medicine_id={mid}")["data"]
            return Decimal(rows[0]["quantity_on_hand"])

        before_donor, before_dest = balance(donor), balance(dest)
        forecast = call(
            "POST",
            "/forecasts/generate",
            {
                "facility_id": dest,
                "medicine_id": mid,
                "model_code": "MOVING_AVERAGE_7D",
                "horizon_days": 14,
                "lookback_days": 730,
            },
            201,
        )
        assert len(forecast["points"]) == 14 and forecast["run"]["data_points_used"] == 730
        call("GET", f"/forecasts/{forecast['run']['id']}/explanation")
        risk = call(
            "POST",
            "/risk-assessments/generate",
            {"facility_id": dest, "medicine_id": mid, "forecast_run_id": forecast["run"]["id"]},
            201,
        )
        call("GET", f"/risk-assessments/{risk['id']}/explanation")
        payload = {
            "destination_facility_id": dest,
            "source_facility_id": donor,
            "medicine_id": mid,
            "planning_horizon_days": 14,
        }
        rec = call("POST", "/redistributions/recommendations/generate", payload, 201)
        call("GET", f"/redistributions/recommendations/{rec['id']}/explanation")
        officer = call(
            "POST",
            "/auth/login",
            {"email": "miriam.wanjiku.demo@medstock.example", "password": officer_password},
        )["access_token"]
        call(
            "POST",
            f"/redistributions/recommendations/{rec['id']}/approve",
            {},
            403,
            {"Authorization": "Bearer " + officer},
        )
        approved = call(
            "POST",
            f"/redistributions/recommendations/{rec['id']}/approve",
            {"note": "Disposable synthetic E2E approval"},
        )
        assert approved["status"] == "APPROVED"
        transfer = call("POST", "/transfers", {"recommendation_id": rec["id"], "quantity": 5}, 201)
        assert transfer["status"] == "APPROVED"
        dispatched = call("POST", f"/transfers/{transfer['id']}/dispatch")
        assert dispatched["status"] == "IN_TRANSIT"
        assert balance(donor) == before_donor - 5 and balance(dest) == before_dest
        completed = call("POST", f"/transfers/{transfer['id']}/complete")
        assert completed["status"] == "COMPLETED"
        assert balance(donor) == before_donor - 5 and balance(dest) == before_dest + 5
        assert call("POST", f"/transfers/{transfer['id']}/complete")["status"] == "COMPLETED"
        assert balance(donor) == before_donor - 5 and balance(dest) == before_dest + 5
        cancellation_rec = call("POST", "/redistributions/recommendations/generate", payload, 201)
        call("POST", f"/redistributions/recommendations/{cancellation_rec['id']}/approve", {})
        cancelled = call(
            "POST", "/transfers", {"recommendation_id": cancellation_rec["id"], "quantity": 1}, 201
        )
        assert (
            call(
                "POST",
                f"/transfers/{cancelled['id']}/cancel",
                {"reason": "Disposable E2E cancellation"},
            )["status"]
            == "CANCELLED"
        )
        rejected = call("POST", "/redistributions/recommendations/generate", payload, 201)
        assert (
            call(
                "POST",
                f"/redistributions/recommendations/{rejected['id']}/reject",
                {"note": "Synthetic rejection"},
            )["status"]
            == "REJECTED"
        )
        # Existing transaction workflow and conservation after a receipt/consumption pair.
        for kind in ["RECEIPT", "CONSUMPTION"]:
            call(
                "POST",
                "/inventory/transactions",
                {
                    "facility_id": dest,
                    "medicine_id": mid,
                    "transaction_type": kind,
                    "quantity": 1,
                    "transaction_date": str(date.today()),
                    "reference_number": "SYN-E2E-" + str(uuid4()),
                },
                201,
            )
        assert balance(dest) == before_dest + 5
        audit = call("GET", "/audit?page_size=200")["data"]
        assert any(a["entity_id"] == transfer["id"] for a in audit)
        call("GET", "/dashboard")
        call("GET", "/decision-analytics")
        print(
            json.dumps(
                {
                    "passed": True,
                    "workflow": [
                        "login",
                        "730-day forecast",
                        "risk/explanations",
                        "RBAC rejection",
                        "recommendation approval",
                        "transfer dispatch/receipt",
                        "idempotent completion without duplicate receipt",
                        "transfer cancellation",
                        "recommendation rejection",
                        "inventory receipt/consumption",
                        "audit",
                        "dashboard",
                        "analytics",
                    ],
                    "donor_change": str(balance(donor) - before_donor),
                    "destination_change": str(balance(dest) - before_dest),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
