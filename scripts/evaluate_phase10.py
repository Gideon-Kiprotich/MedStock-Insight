"""Measure all synthetic series and demonstrate isolated, replayable scenarios."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.core import Facility, InventoryTransaction, InventoryTransactionType, Medicine
from app.services.analytics import evaluate_network, operational_summary
from app.services.experiments import ScenarioParameters, create_scenario


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/medstock-phase10-report.json"))
    args = parser.parse_args()
    with SessionLocal() as db:
        print("Evaluating all recorded series (MA7 and Random Forest)...", flush=True)
        evaluation = evaluate_network(db)
        print(f"Measured {evaluation['series_count']} series.", flush=True)
        facilities = {f.code: f for f in db.scalars(select(Facility))}
        medicines = {(m.generic_name, m.strength): m for m in db.scalars(select(Medicine))}
        scenarios = []
        for code, name, strength, demand, inventory, delay in [
            ("13156", "Paracetamol", "500 mg", 30, -30, 0),
            ("13080", "Paracetamol", "500 mg", 20, 0, 7),
            ("34027", "Epinephrine (adrenaline)", "1 mg/1 mL ampoule", 30, -20, 3),
        ]:
            scenarios.append(
                create_scenario(
                    db,
                    ScenarioParameters(
                        facility_id=facilities[code].id,
                        medicine_id=medicines[name, strength].id,
                        demand_adjustment_pct=demand,
                        inventory_adjustment_pct=inventory,
                        lead_time_adjustment_days=delay,
                    ),
                )
            )
        query = select(
            func.min(InventoryTransaction.transaction_date),
            func.max(InventoryTransaction.transaction_date),
            func.count(),
        ).where(InventoryTransaction.transaction_type == InventoryTransactionType.CONSUMPTION)
        first, last, count = db.execute(query).one()
        events = db.scalar(
            select(func.count())
            .select_from(InventoryTransaction)
            .where(
                InventoryTransaction.reference_number.like("SYN-KENYA-ADJUSTMENT_OUT-%"),
                (
                    InventoryTransaction.reference_number.like("%-150")
                    | InventoryTransaction.reference_number.like("%-515")
                ),
            )
        )
        summary = operational_summary(db)
        report = {
            "data": {
                "start_date": first,
                "end_date": last,
                "observations": count,
                "series": evaluation["series_count"],
                "deliberate_stockout_events": events,
                "current_shortage_scenarios": summary["inventory"]["projected_shortage_items"],
                "current_surplus_scenarios": summary["inventory"]["surplus_items"],
                "forecast_position_coverage": summary["inventory"]["position_coverage"],
            },
            "evaluation": {k: v for k, v in evaluation.items() if k != "context"},
            "scenarios": scenarios,
            "analytics": summary,
        }
        args.output.write_text(json.dumps(jsonable_encoder(report), indent=2))
        print(
            json.dumps(
                jsonable_encoder({"data": report["data"], "overall": evaluation["overall"]}),
                indent=2,
            ),
            flush=True,
        )
        print(f"Report: {args.output}", flush=True)


if __name__ == "__main__":
    main()
