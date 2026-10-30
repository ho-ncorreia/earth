from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import ArchitectureRisk, ArchitectureStudy, ArchitectureDomain, AuditEvent, RiskConfiguration, RiskMitigation, RiskTaxonomyFamily, Role, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    db.execute(text("SELECT 1"))
    open_statuses = ("Open", "In Progress", "Reopened")
    risk_count = func.count(ArchitectureRisk.id)
    average_open_score = db.scalar(select(func.avg(ArchitectureRisk.probability * ArchitectureRisk.impact)).where(ArchitectureRisk.status.in_(open_statuses))) or 0
    stale_config = db.get(RiskConfiguration, "mitigation_validation_stale_days")
    stale_days = max(1, min(int(stale_config.value), 3650)) if stale_config else 365
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
    mitigation_status_counts = {status: count for status, count in db.execute(select(RiskMitigation.status, func.count(RiskMitigation.mitigation_id)).group_by(RiskMitigation.status)).all()}
    family_rows = db.execute(select(ArchitectureRisk.family_id, func.count(ArchitectureRisk.id)).where(ArchitectureRisk.status.in_(open_statuses)).group_by(ArchitectureRisk.family_id)).all()
    family_names = {item.id: item.name_fr for item in db.scalars(select(RiskTaxonomyFamily)).all()}
    open_family_counts: list[dict] = []
    for family_id, count in family_rows:
        open_family_counts.append({"family_id": family_id, "family": family_names.get(family_id, "À qualifier"), "count": count})
    risk_status_counts = {status: count for status, count in db.execute(select(ArchitectureRisk.status, risk_count).group_by(ArchitectureRisk.status)).all()}
    study_status_counts = {status: count for status, count in db.execute(select(ArchitectureStudy.status, func.count(ArchitectureStudy.id)).group_by(ArchitectureStudy.status)).all()}
    return {
        "database": "ready",
        "users": db.scalar(select(func.count(User.id))) or 0,
        "roles": db.scalar(select(func.count(Role.id))) or 0,
        "audit_events": db.scalar(select(func.count(AuditEvent.id))) or 0,
        "studies": db.scalar(select(func.count(ArchitectureStudy.id))) or 0,
        "open_risks": db.scalar(select(risk_count).where(ArchitectureRisk.status.in_(open_statuses))) or 0,
        "critical_risks": db.scalar(select(risk_count).where(ArchitectureRisk.probability * ArchitectureRisk.impact >= 12, ArchitectureRisk.status.in_(open_statuses))) or 0,
        "average_open_risk_score": round(float(average_open_score), 1),
        "mitigations_not_validated": sum(count for status, count in mitigation_status_counts.items() if status != "Approved"),
        "mitigations_stale": db.scalar(select(func.count(RiskMitigation.mitigation_id)).where(RiskMitigation.status == "Approved", RiskMitigation.validated_at < stale_cutoff)) or 0,
        "mitigations_in_review": mitigation_status_counts.get("Submitted", 0),
        "risk_status_counts": risk_status_counts,
        "study_status_counts": study_status_counts,
        "open_risk_family_counts": open_family_counts,
        "architecture_domains": db.scalar(select(func.count(ArchitectureDomain.id)).where(ArchitectureDomain.is_active.is_(True))) or 0,
    }