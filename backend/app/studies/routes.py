from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_event
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_csrf, require_permission
from app.models import ArchitectureDomain, ArchitectureStudy, User, utc_now
from app.schemas import ArchitectureDomainCreate, ArchitectureDomainOut, ArchitectureDomainUpdate, Page, StudyCreate, StudyOut, StudyUpdate

router = APIRouter(prefix="/studies", tags=["architecture studies"])
study_read = require_permission("studies.read")
study_write = require_permission("studies.write")
risk_settings_write = require_permission("admin.configure")
TRANSITIONS = {
    "Draft": {"In Progress"},
    "In Progress": {"Draft", "Ready for Review"},
    "Ready for Review": {"In Progress", "Under Review"},
    "Under Review": {"In Progress", "Approved"},
    "Approved": {"Closed", "Archived"},
    "Closed": {"Archived"},
    "Archived": {"In Progress"},
}


def ensure_architecture_domains(db: Session) -> None:
    values = db.scalars(select(ArchitectureStudy.architecture_domain).where(ArchitectureStudy.architecture_domain != "").distinct()).all()
    existing = {domain.name.casefold(): domain for domain in db.scalars(select(ArchitectureDomain)).all()}
    for value in values:
        normalized = value.strip()
        if normalized and normalized.casefold() not in existing:
            domain = ArchitectureDomain(name=normalized, is_active=True)
            db.add(domain)
            existing[normalized.casefold()] = domain
    db.flush()
    for study in db.scalars(select(ArchitectureStudy).where(ArchitectureStudy.architecture_domain_id.is_(None), ArchitectureStudy.architecture_domain != "")).all():
        domain = existing.get(study.architecture_domain.strip().casefold())
        if domain:
            study.architecture_domain_id = domain.id


def assign_study_domain(db: Session, study: ArchitectureStudy, domain_id: int | None, legacy_name: str | None = None) -> None:
    if domain_id is None and not (legacy_name or "").strip():
        study.architecture_domain_id = None
        study.architecture_domain = ""
        return
    domain = db.get(ArchitectureDomain, domain_id) if domain_id is not None else db.scalar(
        select(ArchitectureDomain).where(func.lower(ArchitectureDomain.name) == (legacy_name or "").strip().lower())
    )
    if domain is None or not domain.is_active:
        raise HTTPException(status_code=422, detail="Choose an active architecture domain from settings")
    study.architecture_domain_id = domain.id
    study.architecture_domain = domain.name


@router.get("/domains", response_model=list[ArchitectureDomainOut])
def list_domains(include_inactive: bool = False, db: Session = Depends(get_db), _: User = Depends(study_read)) -> list[ArchitectureDomain]:
    ensure_architecture_domains(db)
    statement = select(ArchitectureDomain).order_by(ArchitectureDomain.name)
    if not include_inactive:
        statement = statement.where(ArchitectureDomain.is_active.is_(True))
    db.commit()
    return list(db.scalars(statement).all())


@router.post("/domains", response_model=ArchitectureDomainOut, status_code=201, dependencies=[Depends(require_csrf)])
def create_domain(payload: ArchitectureDomainCreate, request: Request, db: Session = Depends(get_db), actor: User = Depends(risk_settings_write)) -> ArchitectureDomain:
    ensure_architecture_domains(db)
    name = payload.name.strip()
    existing = db.scalar(select(ArchitectureDomain).where(func.lower(ArchitectureDomain.name) == name.lower()))
    if existing:
        raise HTTPException(status_code=409, detail="This architecture domain already exists")
    domain = ArchitectureDomain(name=name, is_active=True)
    db.add(domain)
    db.flush()
    record_event(db, actor=actor, action="architecture_domain.created", object_type="architecture_domain", object_id=str(domain.id), new_value={"name": domain.name}, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(domain)
    return domain


@router.patch("/domains/{domain_id}", response_model=ArchitectureDomainOut, dependencies=[Depends(require_csrf)])
def update_domain(domain_id: int, payload: ArchitectureDomainUpdate, request: Request, db: Session = Depends(get_db), actor: User = Depends(risk_settings_write)) -> ArchitectureDomain:
    domain = db.get(ArchitectureDomain, domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Architecture domain not found")
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        changes["name"] = changes["name"].strip()
        duplicate = db.scalar(select(ArchitectureDomain).where(func.lower(ArchitectureDomain.name) == changes["name"].lower(), ArchitectureDomain.id != domain.id))
        if duplicate:
            raise HTTPException(status_code=409, detail="This architecture domain already exists")
    previous = {key: getattr(domain, key) for key in changes}
    for key, value in changes.items():
        setattr(domain, key, value)
    if "name" in changes:
        for study in db.scalars(select(ArchitectureStudy).where(ArchitectureStudy.architecture_domain_id == domain.id)).all():
            study.architecture_domain = domain.name
    record_event(db, actor=actor, action="architecture_domain.updated", object_type="architecture_domain", object_id=str(domain.id), previous_value=previous, new_value=changes, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(domain)
    return domain


@router.get("", response_model=Page[StudyOut])
def list_studies(limit: int = 25, offset: int = 0, db: Session = Depends(get_db), _: User = Depends(study_read)) -> dict:
    limit, offset = min(max(limit, 1), 100), max(offset, 0)
    items = db.scalars(select(ArchitectureStudy).order_by(ArchitectureStudy.updated_at.desc()).limit(limit).offset(offset)).all()
    total = db.scalar(select(func.count(ArchitectureStudy.id))) or 0
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=StudyOut, status_code=201, dependencies=[Depends(require_csrf)])
def create_study(payload: StudyCreate, request: Request, response: Response, db: Session = Depends(get_db), actor: User = Depends(study_write)) -> ArchitectureStudy:
    ensure_architecture_domains(db)
    values = payload.model_dump(exclude={"architecture_domain", "architecture_domain_id"})
    study = ArchitectureStudy(**values, identifier=f"STU-{uuid4().hex[:8].upper()}", lead_architect_id=actor.id)
    assign_study_domain(db, study, payload.architecture_domain_id, payload.architecture_domain)
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
def update_study(study_id: int, payload: StudyUpdate, request: Request, response: Response, db: Session = Depends(get_db), actor: User = Depends(get_current_user)) -> ArchitectureStudy:
    study = db.get(ArchitectureStudy, study_id)
    if study is None:
        raise HTTPException(status_code=404, detail="Study not found")
    changes = payload.model_dump(exclude_unset=True)
    granted = {permission.code for permission in actor.role.permissions}
    if changes.get("status") == "Approved":
        if "studies.approve" not in granted:
            raise HTTPException(status_code=403, detail="Study approval permission is required")
    elif "studies.write" not in granted:
        raise HTTPException(status_code=403, detail="Study write permission is required")
    if "architecture_domain_id" in changes or "architecture_domain" in changes:
        ensure_architecture_domains(db)
        assign_study_domain(db, study, changes.pop("architecture_domain_id", None), changes.pop("architecture_domain", None))
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