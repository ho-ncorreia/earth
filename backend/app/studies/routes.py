from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_event
from app.core.database import get_db
from app.core.dependencies import require_csrf, require_permission
from app.models import ArchitectureStudy, User
from app.schemas import Page, StudyCreate, StudyOut, StudyUpdate

router = APIRouter(prefix="/studies", tags=["architecture studies"])
study_read = require_permission("studies.read")
study_write = require_permission("studies.write")
TRANSITIONS = {
    "Draft": {"In Progress"},
    "In Progress": {"Draft", "Ready for Review"},
    "Ready for Review": {"In Progress", "Under Review"},
    "Under Review": {"In Progress", "Approved"},
    "Approved": {"Closed", "Archived"},
    "Closed": {"Archived"},
    "Archived": set(),
}


@router.get("", response_model=Page[StudyOut])
def list_studies(limit: int = 25, offset: int = 0, db: Session = Depends(get_db), _: User = Depends(study_read)) -> dict:
    limit, offset = min(max(limit, 1), 100), max(offset, 0)
    items = db.scalars(select(ArchitectureStudy).order_by(ArchitectureStudy.updated_at.desc()).limit(limit).offset(offset)).all()
    total = db.scalar(select(func.count(ArchitectureStudy.id))) or 0
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=StudyOut, status_code=201, dependencies=[Depends(require_csrf)])
def create_study(payload: StudyCreate, request: Request, response: Response, db: Session = Depends(get_db), actor: User = Depends(study_write)) -> ArchitectureStudy:
    study = ArchitectureStudy(**payload.model_dump(), identifier=f"STU-{uuid4().hex[:8].upper()}", lead_architect_id=actor.id)
    db.add(study)
    db.flush()
    record_event(db, actor=actor, action="study.created", object_type="study", object_id=str(study.id), new_value={"identifier": study.identifier, "title": study.title}, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(study)
    response.headers["ETag"] = f'"{study.row_version}"'
    return study


@router.get("/{study_id}", response_model=StudyOut)
def get_study(study_id: int, db: Session = Depends(get_db), _: User = Depends(study_read)) -> ArchitectureStudy:
    study = db.get(ArchitectureStudy, study_id)
    if study is None:
        raise HTTPException(status_code=404, detail="Study not found")
    return study


@router.patch("/{study_id}", response_model=StudyOut, dependencies=[Depends(require_csrf)])
def update_study(study_id: int, payload: StudyUpdate, request: Request, response: Response, db: Session = Depends(get_db), actor: User = Depends(study_write)) -> ArchitectureStudy:
    study = db.get(ArchitectureStudy, study_id)
    if study is None:
        raise HTTPException(status_code=404, detail="Study not found")
    changes = payload.model_dump(exclude_unset=True)
    target_status = changes.get("status")
    if target_status and target_status != study.status and target_status not in TRANSITIONS[study.status]:
        raise HTTPException(status_code=409, detail=f"Invalid study transition: {study.status} to {target_status}")
    previous = {key: getattr(study, key) for key in changes}
    for key, value in changes.items():
        setattr(study, key, value)
    record_event(db, actor=actor, action="study.updated", object_type="study", object_id=str(study.id), previous_value=previous, new_value=changes, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(study)
    response.headers["ETag"] = f'"{study.row_version}"'
    return study


@router.delete("/{study_id}", status_code=204, dependencies=[Depends(require_csrf)])
def delete_study(study_id: int, request: Request, db: Session = Depends(get_db), actor: User = Depends(study_write)) -> Response:
    study = db.get(ArchitectureStudy, study_id)
    if study is None:
        raise HTTPException(status_code=404, detail="Study not found")
    if study.status != "Draft":
        raise HTTPException(status_code=409, detail="Only draft studies can be deleted")
    record_event(db, actor=actor, action="study.deleted", object_type="study", object_id=str(study.id), previous_value={"identifier": study.identifier, "title": study.title}, correlation_id=request.headers.get("x-correlation-id", ""))
    db.delete(study)
    db.commit()
    return Response(status_code=204)