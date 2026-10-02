"""Read-only full-network temporal comparison for a seeded demo database.

Example: DEBUG=false DATABASE_URL=sqlite:////tmp/medstock-phase9.sqlite
         uv run python scripts/evaluate_phase9.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.api.routes.decision_support import forecast_evaluation
from app.db.session import SessionLocal


def main():
    rows = []
    evaluated_series = 0
    with SessionLocal() as db:
        for offset in range(0, 10000, 100):
            page = forecast_evaluation(db, None, limit=100, offset=offset)
            rows.extend(page["results"])
            evaluated_series += page["evaluated_series"]
            print(f"Processed {offset + len(page['results']) // 2} series", file=sys.stderr)
            if len(page["results"]) < 200:
                break
    print(json.dumps({
        "window": [str(page["start_date"]), str(page["end_date"])],
        "evaluated_series": evaluated_series,
        "measured_model_rows": sum(row["status"] == "MEASURED" for row in rows),
        "insufficient_model_rows": sum(row["status"] != "MEASURED" for row in rows),
        "methodology": page["methodology"],
        "note": page["data_note"],
    }, indent=2))


if __name__ == "__main__":
    main()
