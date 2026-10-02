from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.core import AnalyticalExperiment, User
from app.services.analytics import evaluate_network, latest_evaluation, operational_summary
from app.services.experiments import ScenarioParameters, create_scenario, serialize, simulate

router = APIRouter(tags=["Decision Analytics"])
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(get_current_user)]


class EvaluationParameters(BaseModel):
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def valid_range(self):
        if self.end_date and self.end_date > date.today():
            raise ValueError("Evaluation cannot include future dates")
        if (
            self.start_date
            and self.end_date
            and not 0 <= (self.end_date - self.start_date).days <= 730
        ):
            raise ValueError("Evaluation range must be 1–731 days")
        return self


@router.post("/scenarios")
def scenario_create(params: ScenarioParameters, db: DB, actor: Actor):
    return create_scenario(db, params, actor.id)


@router.get("/scenarios/{scenario_id}")
def scenario_replay(scenario_id: UUID, db: DB, _: Actor):
    record = db.get(AnalyticalExperiment, scenario_id)
    if not record or record.kind != "SCENARIO":
        raise HTTPException(404, "Scenario not found")
    return {**serialize(record), **simulate(record.context, record.parameters)}


@router.post("/forecast-evaluation/experiments")
def evaluation_create(params: EvaluationParameters, db: DB, actor: Actor):
    end = params.end_date or date.today()
    if params.start_date and not 0 <= (end - params.start_date).days <= 730:
        raise HTTPException(422, "Evaluation range must be 1–731 days")
    return evaluate_network(db, actor.id, params.start_date, end)


@router.get("/forecast-evaluation/aggregate")
def evaluation_latest(db: DB, _: Actor):
    return latest_evaluation(db)


@router.get("/decision-analytics")
def analytics(db: DB, _: Actor):
    return operational_summary(db)
