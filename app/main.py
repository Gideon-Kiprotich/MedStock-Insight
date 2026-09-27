from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth,
    facilities,
    forecasts,
    inventory,
    medicines,
    models,
    redistributions,
    risk,
)
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0", debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(facilities.router, prefix="/api/v1")
app.include_router(medicines.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(forecasts.router, prefix="/api/v1")
app.include_router(risk.router, prefix="/api/v1")
app.include_router(redistributions.router, prefix="/api/v1")


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "medstock-insight-api"}
