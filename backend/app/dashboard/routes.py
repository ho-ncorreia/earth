from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import ArchitectureRisk, ArchitectureStudy, AuditEvent, Role, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    db.execute(text("SELECT 1"))
    return {
        "database": "ready",
        "users": db.scalar(select(func.count(User.id))) or 0,
        "roles": db.scalar(select(func.count(Role.id))) or 0,
        "audit_events": db.scalar(select(func.count(AuditEvent.id))) or 0,
        "studies": db.scalar(select(func.count(ArchitectureStudy.id))) or 0,
        "open_risks": db.scalar(select(func.count(ArchitectureRisk.id)).where(ArchitectureRisk.status != "Closed")) or 0,
        "critical_risks": db.scalar(select(func.count(ArchitectureRisk.id)).where(ArchitectureRisk.probability * ArchitectureRisk.impact >= 12, ArchitectureRisk.status != "Closed")) or 0,
    }