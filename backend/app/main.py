from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.audit.routes import router as audit_router
from app.ai_assistant.routes import router as ai_router
from app.core.config import settings
from app.core.database import engine
from app.dashboard.routes import router as dashboard_router
from app.decisions.routes import router as decisions_router
from app.identity.routes import router as identity_router
from app.risks.routes import router as risks_router
from app.studies.routes import router as studies_router
from app.users.routes import router as users_router

app = FastAPI(title="EA Workbench API", version="1.0.0", description="Versioned Enterprise Architecture workbench API.", openapi_url="/api/v1/openapi.json", docs_url="/docs")
origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"], allow_headers=["Content-Type", "X-CSRF-Token", "X-Correlation-ID"])

app.include_router(identity_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(studies_router, prefix="/api/v1")
app.include_router(risks_router, prefix="/api/v1")
app.include_router(decisions_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")


@app.get("/health/live", tags=["health"])
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
def ready() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ready", "database": "ready"}