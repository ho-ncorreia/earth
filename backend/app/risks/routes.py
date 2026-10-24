from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_event
from app.core.database import get_db
from app.core.dependencies import require_csrf, require_permission
from app.models import ArchitectureRisk, ArchitectureStudy, User
from app.schemas import Page, RiskCreate, RiskOut, RiskUpdate

router = APIRouter(prefix="/risks", tags=["risks"])
risk_read = require_permission("risks.read")
risk_write = require_permission("risks.write")
TRANSITIONS = {
    "Identified": {"Assessed"},
    "Assessed": {"Treatment Defined"},
    "Treatment Defined": {"Mitigation in Progress", "Monitoring"},
    "Mitigation in Progress": {"Monitoring", "Treatment Defined"},
    "Monitoring": {"Accepted", "Mitigation in Progress", "Closed"},
    "Accepted": {"Monitoring", "Closed"},
    "Closed": set(),
}


@router.get("", response_model=Page[RiskOut])
def list_risks(limit: int = 25, offset: int = 0, db: Session = Depends(get_db), _: User = Depends(risk_read)) -> dict:
    limit, offset = min(max(limit, 1), 100), max(offset, 0)
    items = db.scalars(select(ArchitectureRisk).order_by(ArchitectureRisk.created_at.desc()).limit(limit).offset(offset)).all()
    total = db.scalar(select(func.count(ArchitectureRisk.id))) or 0
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=RiskOut, status_code=201, dependencies=[Depends(require_csrf)])
def create_risk(payload: RiskCreate, request: Request, response: Response, db: Session = Depends(get_db), actor: User = Depends(risk_write)) -> ArchitectureRisk:
    if payload.study_id and db.get(ArchitectureStudy, payload.study_id) is None:
        raise HTTPException(status_code=422, detail="Unknown architecture study")
    risk = ArchitectureRisk(**payload.model_dump(), identifier=f"RSK-{uuid4().hex[:8].upper()}", owner_id=actor.id)
    db.add(risk)
    db.flush()
    record_event(db, actor=actor, action="risk.created", object_type="risk", object_id=str(risk.id), new_value={"identifier": risk.identifier, "title": risk.title, "inherent_score": risk.inherent_score}, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(risk)
    response.headers["ETag"] = f'"{risk.row_version}"'
    return risk


@router.get("/{risk_id}", response_model=RiskOut)
def get_risk(risk_id: int, db: Session = Depends(get_db), _: User = Depends(risk_read)) -> ArchitectureRisk:
    risk = db.get(ArchitectureRisk, risk_id)
    if risk is None:
        raise HTTPException(status_code=404, detail="Risk not found")
    return risk


@router.patch("/{risk_id}", response_model=RiskOut, dependencies=[Depends(require_csrf)])
def update_risk(risk_id: int, payload: RiskUpdate, request: Request, response: Response, db: Session = Depends(get_db), actor: User = Depends(risk_write)) -> ArchitectureRisk:
    risk = db.get(ArchitectureRisk, risk_id)
    if risk is None:
        raise HTTPException(status_code=404, detail="Risk not found")
    changes = payload.model_dump(exclude_unset=True)
    target_status = changes.get("status")
    if target_status and target_status != risk.status and target_status not in TRANSITIONS[risk.status]:
        raise HTTPException(status_code=409, detail=f"Invalid risk transition: {risk.status} to {target_status}")
    if "study_id" in changes and changes["study_id"] and db.get(ArchitectureStudy, changes["study_id"]) is None:
        raise HTTPException(status_code=422, detail="Unknown architecture study")
    residual_probability = changes.get("residual_probability", risk.residual_probability)
    residual_impact = changes.get("residual_impact", risk.residual_impact)
    if (residual_probability is None) != (residual_impact is None):
        raise HTTPException(status_code=422, detail="Residual probability and impact must be provided together")
    previous = {key: getattr(risk, key) for key in changes}
    for key, value in changes.items():
        setattr(risk, key, value)
    record_event(db, actor=actor, action="risk.updated", object_type="risk", object_id=str(risk.id), previous_value=previous, new_value=changes, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(risk)
    response.headers["ETag"] = f'"{risk.row_version}"'
    return risk


@router.delete("/{risk_id}", status_code=204, dependencies=[Depends(require_csrf)])
def delete_risk(risk_id: int, request: Request, db: Session = Depends(get_db), actor: User = Depends(risk_write)) -> Response:
    risk = db.get(ArchitectureRisk, risk_id)
    if risk is None:
        raise HTTPException(status_code=404, detail="Risk not found")
    if risk.status != "Identified":
        raise HTTPException(status_code=409, detail="Only identified risks can be deleted")
    record_event(db, actor=actor, action="risk.deleted", object_type="risk", object_id=str(risk.id), previous_value={"identifier": risk.identifier, "title": risk.title}, correlation_id=request.headers.get("x-correlation-id", ""))
    db.delete(risk)
    db.commit()
    return Response(status_code=204)