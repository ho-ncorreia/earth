from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.audit.service import record_event
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_csrf, require_permission
from app.models import ArchitectureRisk, ArchitectureStudy, RiskAssessment, RiskConfiguration, RiskHelpDefinition, RiskMitigation, RiskMitigationAttachment, RiskMitigationReview, RiskObject, RiskReferenceValue, RiskScope, RiskSource, RiskTaxonomyFamily, RiskTaxonomyType, User, utc_now
from app.schemas import ArdoqComponentOut, ArdoqSettingsUpdate, Page, RiskConfigurationOut, RiskConfigurationUpdate, RiskCreate, RiskHelpOut, RiskHelpUpdate, RiskMitigationInput, RiskMitigationOut, RiskMitigationReviewInput, RiskMitigationUpdate, RiskOut, RiskReferenceValueCreate, RiskReferenceValueOut, RiskReferenceValueUpdate, RiskTaxonomyFamilyUpdate, RiskTaxonomyTypeUpdate, RiskUpdate
from app.risks.catalog import ensure_risk_catalog, ensure_risk_reference_values

router = APIRouter(prefix="/risks", tags=["risks"])
risk_read = require_permission("risks.read")
risk_write = require_permission("risks.write")
risk_help_write = require_permission("admin.configure")
risk_mitigation_approve = require_permission("risks.approve")
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
ATTACHMENT_TYPES = {
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".txt": {"text/plain"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
}
TRANSITIONS = {
    "Open": {"In Progress", "Closed", "Archived"},
    "In Progress": {"Open", "Closed", "Archived"},
    "Closed": {"Reopened", "Archived"},
    "Archived": {"Reopened"},
    "Reopened": {"In Progress", "Closed", "Archived"},
}


def validate_taxonomy(db: Session, family_id: str | None, subfamily_id: str | None, definition_id: str | None) -> None:
    if (family_id is None) != (subfamily_id is None):
        raise HTTPException(status_code=422, detail="Choose both a family and a subfamily, or leave both unclassified")
    if family_id is None:
        if definition_id is not None:
            raise HTTPException(status_code=422, detail="An unclassified risk cannot reference a catalog definition")
        return
    child = db.get(RiskTaxonomyType, subfamily_id)
    if child is None or child.family_id != family_id or db.get(RiskTaxonomyFamily, family_id) is None:
        raise HTTPException(status_code=422, detail="The subfamily does not belong to the selected family")
    if definition_id is not None:
        definition = db.get(RiskHelpDefinition, definition_id)
        if definition is None or definition.subfamily_id != subfamily_id:
            raise HTTPException(status_code=422, detail="The help definition does not match the selected subfamily")


def validate_reference_selections(db: Session, payload) -> None:
    ensure_risk_reference_values(db)
    selected = {
        "object_type": {item.object_type for item in (getattr(payload, "objects", None) or [])},
        "source_type": {item.source_type for item in (getattr(payload, "sources", None) or [])},
        "scope_type": {item.scope_type for item in (getattr(payload, "scopes", None) or [])},
    }
    for category, values in selected.items():
        if not values:
            continue
        active = set(db.scalars(select(RiskReferenceValue.label_en).where(RiskReferenceValue.category == category, RiskReferenceValue.is_active.is_(True))).all())
        active.update(db.scalars(select(RiskReferenceValue.label_fr).where(RiskReferenceValue.category == category, RiskReferenceValue.is_active.is_(True))).all())
        if not values.issubset(active):
            raise HTTPException(status_code=422, detail=f"Choose an active configured value for {category.replace('_', ' ')}")


def sync_assessments(risk: ArchitectureRisk) -> None:
    inherent = next((item for item in risk.assessments if item.assessment_type == "Inherent"), None)
    if inherent is None:
        inherent = RiskAssessment(assessment_id=uuid4().hex, assessment_type="Inherent")
        risk.assessments.append(inherent)
    inherent.probability, inherent.impact = risk.probability, risk.impact
    residual = next((item for item in risk.assessments if item.assessment_type == "Residual"), None)
    if risk.residual_probability is None or risk.residual_impact is None:
        if residual is not None:
            risk.assessments.remove(residual)
    elif residual is None:
        risk.assessments.append(RiskAssessment(
            assessment_id=uuid4().hex, assessment_type="Residual",
            probability=risk.residual_probability, impact=risk.residual_impact,
        ))
    else:
        residual.probability, residual.impact = risk.residual_probability, risk.residual_impact


def sync_risk_mitigation(risk: ArchitectureRisk, mitigation: RiskMitigation) -> None:
    risk.residual_probability = mitigation.residual_probability
    risk.residual_impact = mitigation.residual_impact
    risk.treatment_strategy = mitigation.treatment_strategy
    risk.control_effectiveness = mitigation.control_effectiveness
    sync_assessments(risk)


def stale_after_days(db: Session) -> int:
    entry = db.get(RiskConfiguration, "mitigation_validation_stale_days")
    return max(1, min(int(entry.value), 3650)) if entry else 365


def risk_setting(db: Session, key: str, default: str = "") -> str:
    value = db.get(RiskConfiguration, key)
    return value.value if value else default


def mitigation_file_path(storage_name: str) -> Path:
    return Path(settings.attachment_storage_path).resolve() / storage_name


def invalidate_mitigation_validation(mitigation: RiskMitigation) -> None:
    if mitigation.status != "Draft":
        mitigation.status = "Draft"
        mitigation.validated_at = None
        mitigation.validated_by_id = None
        mitigation.validation_comment = ""


def association_snapshot(risk: ArchitectureRisk, name: str) -> list[dict]:
    records = getattr(risk, name)
    return [{column.name: getattr(record, column.name) for column in record.__table__.columns if column.name not in {"risk_id"}} for record in records]


@router.get("", response_model=Page[RiskOut])
def list_risks(limit: int = 25, offset: int = 0, db: Session = Depends(get_db), _: User = Depends(risk_read)) -> dict:
    limit, offset = min(max(limit, 1), 100), max(offset, 0)
    items = db.scalars(select(ArchitectureRisk).order_by(ArchitectureRisk.created_at.desc()).limit(limit).offset(offset)).all()
    total = db.scalar(select(func.count(ArchitectureRisk.id))) or 0
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/catalog")
def get_risk_catalog(db: Session = Depends(get_db), _: User = Depends(risk_read)) -> list[dict]:
    ensure_risk_catalog(db)
    ensure_risk_reference_values(db)
    db.commit()
    families = db.scalars(select(RiskTaxonomyFamily).order_by(RiskTaxonomyFamily.id)).all()
    return [{"id": family.id, "name_en": family.name_en, "name_fr": family.name_fr,
             "types": [{"id": item.id, "family_id": item.family_id, "label_en": item.label_en, "label_fr": item.label_fr}
                       for item in family.types]} for family in families]


@router.get("/catalog/help", response_model=list[RiskHelpOut])
def list_risk_help(db: Session = Depends(get_db), _: User = Depends(risk_read)) -> list[RiskHelpDefinition]:
    ensure_risk_catalog(db)
    db.commit()
    return list(db.scalars(select(RiskHelpDefinition).order_by(RiskHelpDefinition.risk_number)).all())


@router.get("/settings/references")
def get_risk_reference_settings(db: Session = Depends(get_db), _: User = Depends(risk_read)) -> dict:
    ensure_risk_catalog(db)
    ensure_risk_reference_values(db)
    db.commit()
    families = db.scalars(select(RiskTaxonomyFamily).order_by(RiskTaxonomyFamily.id)).all()
    subfamilies = db.scalars(select(RiskTaxonomyType).order_by(RiskTaxonomyType.id)).all()
    values = db.scalars(select(RiskReferenceValue).order_by(RiskReferenceValue.category, RiskReferenceValue.label_en)).all()
    return {
        "families": [{"id": item.id, "name_en": item.name_en, "name_fr": item.name_fr} for item in families],
        "subfamilies": [{"id": item.id, "family_id": item.family_id, "label_en": item.label_en, "label_fr": item.label_fr} for item in subfamilies],
        "values": [{"id": item.id, "category": item.category, "code": item.code, "label_en": item.label_en, "label_fr": item.label_fr, "is_active": item.is_active} for item in values],
    }


@router.get("/settings/ardoq")
def get_ardoq_settings(db: Session = Depends(get_db), _: User = Depends(risk_help_write)) -> dict:
    ensure_risk_reference_values(db)
    object_types = db.scalars(select(RiskReferenceValue).where(RiskReferenceValue.category == "object_type").order_by(RiskReferenceValue.label_en)).all()
    return {
        "api_host": settings.ardoq_api_host,
        "org_label": settings.ardoq_org_label,
        "token_configured": bool(settings.ardoq_api_token),
        "root_workspace_id": risk_setting(db, "ardoq_root_workspace_id"),
        "component_type_ids": {item.code: risk_setting(db, f"ardoq_type_id:{item.code}") for item in object_types},
        "object_types": [{"code": item.code, "label_en": item.label_en, "label_fr": item.label_fr, "is_active": item.is_active} for item in object_types],
    }


@router.put("/settings/ardoq", dependencies=[Depends(require_csrf)])
def update_ardoq_settings(payload: ArdoqSettingsUpdate, request: Request, db: Session = Depends(get_db), actor: User = Depends(risk_help_write)) -> dict:
    ensure_risk_reference_values(db)
    object_types = db.scalars(select(RiskReferenceValue).where(RiskReferenceValue.category == "object_type")).all()
    allowed_codes = {item.code for item in object_types}
    if set(payload.component_type_ids) - allowed_codes:
        raise HTTPException(status_code=422, detail="A component type mapping refers to an unknown object type")
    root_key = "ardoq_root_workspace_id"
    previous = {root_key: risk_setting(db, root_key)}
    root = db.get(RiskConfiguration, root_key)
    if root is None:
        db.add(RiskConfiguration(key=root_key, value=payload.root_workspace_id.strip()))
    else:
        root.value = payload.root_workspace_id.strip()
    for code in allowed_codes:
        key = f"ardoq_type_id:{code}"
        current = db.get(RiskConfiguration, key)
        next_value = (payload.component_type_ids.get(code) or "").strip()
        previous[key] = current.value if current else ""
        if next_value:
            if current is None:
                db.add(RiskConfiguration(key=key, value=next_value))
            else:
                current.value = next_value
        elif current is not None:
            db.delete(current)
    new_value = {root_key: payload.root_workspace_id.strip(), **{f"ardoq_type_id:{code}": value.strip() for code, value in payload.component_type_ids.items()}}
    record_event(db, actor=actor, action="ardoq_configuration.updated", object_type="risk_configuration", object_id="ardoq", previous_value=previous, new_value=new_value, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    return get_ardoq_settings(db, actor)


@router.get("/ardoq/components", response_model=list[ArdoqComponentOut])
async def search_ardoq_components(label: str, object_type_code: str, db: Session = Depends(get_db), _: User = Depends(risk_write)) -> list[dict]:
    query = label.strip()
    if len(query) < 2:
        raise HTTPException(status_code=422, detail="Enter at least two characters to search Ardoq")
    if not settings.ardoq_api_token or not settings.ardoq_org_label:
        raise HTTPException(status_code=503, detail="Configure EA_ARDOQ_API_TOKEN and EA_ARDOQ_ORG_LABEL on the backend")
    root_workspace = risk_setting(db, "ardoq_root_workspace_id")
    type_id = risk_setting(db, f"ardoq_type_id:{object_type_code}")
    if not root_workspace or not type_id:
        raise HTTPException(status_code=503, detail="Configure the Ardoq root workspace and component type mapping in Architecture settings")
    reference = db.scalar(select(RiskReferenceValue).where(RiskReferenceValue.category == "object_type", RiskReferenceValue.code == object_type_code, RiskReferenceValue.is_active.is_(True)))
    if reference is None:
        raise HTTPException(status_code=422, detail="Choose an active configured object type")
    headers = {"Authorization": f"Bearer {settings.ardoq_api_token}", "X-org": settings.ardoq_org_label}
    params = {"rootWorkspace": root_workspace, "name": query, "typeId": type_id}
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(f"{settings.ardoq_api_host.rstrip('/')}/api/v2/components", headers=headers, params=params)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Ardoq component search failed with HTTP {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Ardoq is unavailable; check the configured host and network access") from exc
    values = response.json().get("values", [])
    return [{"code": item.get("componentKey") or item.get("_id", ""), "name": item.get("name", ""), "component_type": item.get("type", ""), "type_id": str(item.get("typeId", ""))} for item in values[:50] if item.get("componentKey") or item.get("_id")]


@router.patch("/settings/families/{family_id}", dependencies=[Depends(require_csrf)])
def update_risk_family(family_id: str, payload: RiskTaxonomyFamilyUpdate, request: Request, db: Session = Depends(get_db), actor: User = Depends(risk_help_write)) -> dict:
    family = db.get(RiskTaxonomyFamily, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="Risk family not found")
    changes = payload.model_dump()
    previous = {key: getattr(family, key) for key in changes}
    for key, value in changes.items():
        setattr(family, key, value.strip())
    record_event(db, actor=actor, action="risk_family.updated", object_type="risk_taxonomy_family", object_id=family.id, previous_value=previous, new_value=changes, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    return {"id": family.id, "name_en": family.name_en, "name_fr": family.name_fr}


@router.patch("/settings/subfamilies/{subfamily_id:path}", dependencies=[Depends(require_csrf)])
def update_risk_subfamily(subfamily_id: str, payload: RiskTaxonomyTypeUpdate, request: Request, db: Session = Depends(get_db), actor: User = Depends(risk_help_write)) -> dict:
    subfamily = db.get(RiskTaxonomyType, subfamily_id)
    if subfamily is None:
        raise HTTPException(status_code=404, detail="Risk subfamily not found")
    changes = payload.model_dump()
    previous = {key: getattr(subfamily, key) for key in changes}
    for key, value in changes.items():
        setattr(subfamily, key, value.strip())
    record_event(db, actor=actor, action="risk_subfamily.updated", object_type="risk_taxonomy_type", object_id=subfamily.id, previous_value=previous, new_value=changes, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    return {"id": subfamily.id, "family_id": subfamily.family_id, "label_en": subfamily.label_en, "label_fr": subfamily.label_fr}


@router.post("/settings/references", response_model=RiskReferenceValueOut, status_code=201, dependencies=[Depends(require_csrf)])
def create_risk_reference_value(payload: RiskReferenceValueCreate, request: Request, db: Session = Depends(get_db), actor: User = Depends(risk_help_write)) -> RiskReferenceValue:
    ensure_risk_reference_values(db)
    if db.scalar(select(RiskReferenceValue.id).where(RiskReferenceValue.category == payload.category, func.lower(RiskReferenceValue.label_en) == payload.label_en.strip().lower())):
        raise HTTPException(status_code=409, detail="This reference value already exists")
    suffix = uuid4().hex[:12].upper()
    item = RiskReferenceValue(id=f"{payload.category.upper()}_{suffix}", category=payload.category, code=f"CUSTOM_{suffix}", label_en=payload.label_en.strip(), label_fr=payload.label_fr.strip(), is_active=True)
    db.add(item)
    record_event(db, actor=actor, action="risk_reference.created", object_type="risk_reference_value", object_id=item.id, new_value={"category": item.category, "label_en": item.label_en, "label_fr": item.label_fr}, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(item)
    return item


@router.patch("/settings/references/{reference_id}", response_model=RiskReferenceValueOut, dependencies=[Depends(require_csrf)])
def update_risk_reference_value(reference_id: str, payload: RiskReferenceValueUpdate, request: Request, db: Session = Depends(get_db), actor: User = Depends(risk_help_write)) -> RiskReferenceValue:
    item = db.get(RiskReferenceValue, reference_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Risk reference value not found")
    changes = payload.model_dump(exclude_unset=True)
    previous = {key: getattr(item, key) for key in changes}
    old_labels = {item.label_en, item.label_fr}
    for key, value in changes.items():
        setattr(item, key, value.strip() if isinstance(value, str) else value)
    for model, column in ((RiskObject, "object_type"), (RiskSource, "source_type"), (RiskScope, "scope_type")):
        if (item.category, column) in (("object_type", "object_type"), ("source_type", "source_type"), ("scope_type", "scope_type")) and "label_en" in changes:
            db.execute(update(model).where(getattr(model, column).in_(old_labels)).values({column: item.label_en}))
    record_event(db, actor=actor, action="risk_reference.updated", object_type="risk_reference_value", object_id=item.id, previous_value=previous, new_value=changes, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(item)
    return item


@router.patch("/catalog/help/{risk_code}", response_model=RiskHelpOut, dependencies=[Depends(require_csrf)])
def update_risk_help(risk_code: str, payload: RiskHelpUpdate, request: Request, db: Session = Depends(get_db), actor: User = Depends(risk_help_write)) -> RiskHelpDefinition:
    definition = db.scalar(select(RiskHelpDefinition).where(RiskHelpDefinition.risk_code == risk_code))
    if definition is None:
        raise HTTPException(status_code=404, detail="Risk help definition not found")
    changes = payload.model_dump()
    previous = {key: getattr(definition, key) for key in changes}
    for key, value in changes.items():
        setattr(definition, key, value)
    record_event(db, actor=actor, action="risk_help.updated", object_type="risk_help_definition", object_id=definition.id, previous_value=previous, new_value=changes, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(definition)
    return definition


@router.get("/settings/mitigations", response_model=RiskConfigurationOut)
def get_mitigation_settings(db: Session = Depends(get_db), _: User = Depends(risk_read)) -> dict[str, int]:
    return {"mitigation_validation_stale_days": stale_after_days(db)}


@router.put("/settings/mitigations", response_model=RiskConfigurationOut, dependencies=[Depends(require_csrf)])
def update_mitigation_settings(payload: RiskConfigurationUpdate, request: Request, db: Session = Depends(get_db), actor: User = Depends(risk_help_write)) -> dict[str, int]:
    key = "mitigation_validation_stale_days"
    entry = db.get(RiskConfiguration, key)
    previous_value = entry.value if entry else "365"
    if entry is None:
        entry = RiskConfiguration(key=key, value=str(payload.mitigation_validation_stale_days))
        db.add(entry)
    else:
        entry.value = str(payload.mitigation_validation_stale_days)
    record_event(db, actor=actor, action="risk_configuration.updated", object_type="risk_configuration", object_id=key, previous_value={key: previous_value}, new_value={key: entry.value}, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    return {key: int(entry.value)}


@router.get("/mitigations", response_model=list[RiskMitigationOut])
def list_mitigations(db: Session = Depends(get_db), _: User = Depends(risk_read)) -> list[RiskMitigation]:
    return list(db.scalars(select(RiskMitigation).order_by(RiskMitigation.updated_at.desc())).all())


@router.get("/{risk_id}/mitigations", response_model=list[RiskMitigationOut])
def list_risk_mitigations(risk_id: int, db: Session = Depends(get_db), _: User = Depends(risk_read)) -> list[RiskMitigation]:
    risk = db.get(ArchitectureRisk, risk_id)
    if risk is None:
        raise HTTPException(status_code=404, detail="Risk not found")
    return risk.mitigations


@router.post("/{risk_id}/mitigations", response_model=RiskMitigationOut, status_code=201, dependencies=[Depends(require_csrf)])
def create_mitigation(risk_id: int, payload: RiskMitigationInput, request: Request, db: Session = Depends(get_db), actor: User = Depends(risk_write)) -> RiskMitigation:
    risk = db.get(ArchitectureRisk, risk_id)
    if risk is None:
        raise HTTPException(status_code=404, detail="Risk not found")
    if not payload.title.strip():
        raise HTTPException(status_code=422, detail="A mitigation title is required")
    mitigation = RiskMitigation(mitigation_id=uuid4().hex, **payload.model_dump())
    risk.mitigations.append(mitigation)
    sync_risk_mitigation(risk, mitigation)
    db.flush()
    record_event(db, actor=actor, action="risk_mitigation.created", object_type="risk_mitigation", object_id=mitigation.mitigation_id, new_value={"risk_id": risk.id, "title": mitigation.title}, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(mitigation)
    return mitigation


@router.get("/mitigations/{mitigation_id}", response_model=RiskMitigationOut)
def get_mitigation(mitigation_id: str, db: Session = Depends(get_db), _: User = Depends(risk_read)) -> RiskMitigation:
    mitigation = db.get(RiskMitigation, mitigation_id)
    if mitigation is None:
        raise HTTPException(status_code=404, detail="Mitigation not found")
    return mitigation


@router.patch("/mitigations/{mitigation_id}", response_model=RiskMitigationOut, dependencies=[Depends(require_csrf)])
def update_mitigation(mitigation_id: str, payload: RiskMitigationUpdate, request: Request, db: Session = Depends(get_db), actor: User = Depends(risk_write)) -> RiskMitigation:
    mitigation = db.get(RiskMitigation, mitigation_id)
    if mitigation is None:
        raise HTTPException(status_code=404, detail="Mitigation not found")
    changes = payload.model_dump(exclude_unset=True)
    residual_probability = changes.get("residual_probability", mitigation.residual_probability)
    residual_impact = changes.get("residual_impact", mitigation.residual_impact)
    if (residual_probability is None) != (residual_impact is None):
        raise HTTPException(status_code=422, detail="Residual probability and impact must be provided together")
    previous = {key: getattr(mitigation, key) for key in changes}
    for key, value in changes.items():
        setattr(mitigation, key, value)
    invalidate_mitigation_validation(mitigation)
    sync_risk_mitigation(mitigation.risk, mitigation)
    record_event(db, actor=actor, action="risk_mitigation.updated", object_type="risk_mitigation", object_id=mitigation.mitigation_id, previous_value=previous, new_value=changes, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(mitigation)
    return mitigation


@router.post("/mitigations/{mitigation_id}/submit", response_model=RiskMitigationOut, dependencies=[Depends(require_csrf)])
def submit_mitigation(mitigation_id: str, request: Request, db: Session = Depends(get_db), actor: User = Depends(risk_write)) -> RiskMitigation:
    mitigation = db.get(RiskMitigation, mitigation_id)
    if mitigation is None:
        raise HTTPException(status_code=404, detail="Mitigation not found")
    if mitigation.status not in {"Draft", "Rejected"}:
        raise HTTPException(status_code=409, detail="Only a draft or rejected mitigation can be submitted")
    if not mitigation.description.strip():
        raise HTTPException(status_code=422, detail="A mitigation description is required before submission")
    if mitigation.residual_probability is None or mitigation.residual_impact is None:
        raise HTTPException(status_code=422, detail="Residual probability and impact are required before submission")
    mitigation.status = "Submitted"
    mitigation.submitted_at = utc_now()
    record_event(db, actor=actor, action="risk_mitigation.submitted", object_type="risk_mitigation", object_id=mitigation.mitigation_id, new_value={"status": mitigation.status}, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(mitigation)
    return mitigation


@router.post("/mitigations/{mitigation_id}/review", response_model=RiskMitigationOut, dependencies=[Depends(require_csrf)])
def review_mitigation(mitigation_id: str, payload: RiskMitigationReviewInput, request: Request, db: Session = Depends(get_db), actor: User = Depends(risk_mitigation_approve)) -> RiskMitigation:
    mitigation = db.get(RiskMitigation, mitigation_id)
    if mitigation is None:
        raise HTTPException(status_code=404, detail="Mitigation not found")
    if mitigation.status != "Submitted":
        raise HTTPException(status_code=409, detail="Only a submitted mitigation can be reviewed")
    if payload.decision == "Rejected" and not payload.comment.strip():
        raise HTTPException(status_code=422, detail="A rejection comment is required")
    mitigation.status = payload.decision
    mitigation.validated_at = utc_now() if payload.decision == "Approved" else None
    mitigation.validated_by_id = actor.id if payload.decision == "Approved" else None
    mitigation.validation_comment = payload.comment.strip()
    mitigation.reviews.append(RiskMitigationReview(id=uuid4().hex, reviewer_id=actor.id, decision=payload.decision, comment=payload.comment.strip()))
    sync_risk_mitigation(mitigation.risk, mitigation)
    record_event(db, actor=actor, action=f"risk_mitigation.{payload.decision.lower()}", object_type="risk_mitigation", object_id=mitigation.mitigation_id, new_value={"status": mitigation.status, "comment": mitigation.validation_comment}, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(mitigation)
    return mitigation


@router.post("/mitigations/{mitigation_id}/attachments", response_model=RiskMitigationOut, dependencies=[Depends(require_csrf)])
async def upload_mitigation_attachment(mitigation_id: str, request: Request, file: UploadFile = File(...), db: Session = Depends(get_db), actor: User = Depends(risk_write)) -> RiskMitigation:
    mitigation = db.get(RiskMitigation, mitigation_id)
    if mitigation is None:
        raise HTTPException(status_code=404, detail="Mitigation not found")
    file_name = (file.filename or "").replace("\\", "/").split("/")[-1].strip()
    extension = Path(file_name).suffix.lower()
    if not file_name or extension not in ATTACHMENT_TYPES or file.content_type not in ATTACHMENT_TYPES[extension]:
        raise HTTPException(status_code=415, detail="Unsupported attachment type")
    content = await file.read(MAX_ATTACHMENT_BYTES + 1)
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail="Attachment exceeds the 10 MB limit")
    storage_name = f"{uuid4().hex}{extension}"
    file_path = mitigation_file_path(storage_name)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(content)
    attachment = RiskMitigationAttachment(id=uuid4().hex, mitigation_id=mitigation.mitigation_id, file_name=file_name[:255], storage_name=storage_name, content_type=file.content_type or "application/octet-stream", file_size=len(content), uploaded_by_id=actor.id)
    mitigation.attachments.append(attachment)
    invalidate_mitigation_validation(mitigation)
    record_event(db, actor=actor, action="risk_mitigation.attachment_added", object_type="risk_mitigation", object_id=mitigation.mitigation_id, new_value={"file_name": attachment.file_name, "file_size": attachment.file_size}, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(mitigation)
    return mitigation


@router.get("/mitigations/{mitigation_id}/attachments/{attachment_id}")
def download_mitigation_attachment(mitigation_id: str, attachment_id: str, db: Session = Depends(get_db), _: User = Depends(risk_read)) -> FileResponse:
    attachment = db.get(RiskMitigationAttachment, attachment_id)
    if attachment is None or attachment.mitigation_id != mitigation_id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    path = mitigation_file_path(attachment.storage_name)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Attachment file not found")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.file_name)


@router.post("", response_model=RiskOut, status_code=201, dependencies=[Depends(require_csrf)])
def create_risk(payload: RiskCreate, request: Request, response: Response, db: Session = Depends(get_db), actor: User = Depends(risk_write)) -> ArchitectureRisk:
    validate_taxonomy(db, payload.family_id, payload.subfamily_id, payload.risk_definition_id)
    validate_reference_selections(db, payload)
    if payload.study_id and db.get(ArchitectureStudy, payload.study_id) is None:
        raise HTTPException(status_code=422, detail="Unknown architecture study")
    association_fields = {"objects", "sources", "scopes", "mitigations"}
    values = payload.model_dump(exclude=association_fields)
    risk = ArchitectureRisk(**values, identifier=f"RSK-{uuid4().hex[:8].upper()}", owner_id=actor.id)
    risk.objects = [RiskObject(risk_object_id=uuid4().hex, **item.model_dump()) for item in payload.objects]
    risk.sources = [RiskSource(risk_source_id=uuid4().hex, **item.model_dump()) for item in payload.sources]
    risk.scopes = [RiskScope(risk_scope_id=uuid4().hex, **item.model_dump()) for item in payload.scopes]
    mitigation_inputs = payload.mitigations or [RiskMitigationInput()]
    risk.mitigations = [RiskMitigation(mitigation_id=uuid4().hex, **item.model_dump()) for item in mitigation_inputs]
    first_mitigation = risk.mitigations[0]
    risk.residual_probability = first_mitigation.residual_probability
    risk.residual_impact = first_mitigation.residual_impact
    risk.treatment_strategy = first_mitigation.treatment_strategy
    risk.control_effectiveness = first_mitigation.control_effectiveness
    sync_assessments(risk)
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
    validate_reference_selections(db, payload)
    validate_taxonomy(db, changes.get("family_id", risk.family_id), changes.get("subfamily_id", risk.subfamily_id), changes.get("risk_definition_id", risk.risk_definition_id))
    target_status = changes.get("status")
    if target_status and target_status != risk.status and target_status not in TRANSITIONS[risk.status]:
        raise HTTPException(status_code=409, detail=f"Invalid risk transition: {risk.status} to {target_status}")
    if "study_id" in changes and changes["study_id"] and db.get(ArchitectureStudy, changes["study_id"]) is None:
        raise HTTPException(status_code=422, detail="Unknown architecture study")
    residual_probability = changes.get("residual_probability", risk.residual_probability)
    residual_impact = changes.get("residual_impact", risk.residual_impact)
    if (residual_probability is None) != (residual_impact is None):
        raise HTTPException(status_code=422, detail="Residual probability and impact must be provided together")
    association_models = {
        "objects": (RiskObject, "risk_object_id"), "sources": (RiskSource, "risk_source_id"),
        "scopes": (RiskScope, "risk_scope_id"), "mitigations": (RiskMitigation, "mitigation_id"),
    }
    previous = {
        key: association_snapshot(risk, key) if key in association_models else getattr(risk, key)
        for key in changes
    }
    for key, (model, id_field) in association_models.items():
        if key in changes:
            setattr(risk, key, [model(**{id_field: uuid4().hex, **item}) for item in changes.pop(key)])
    for key, value in changes.items():
        setattr(risk, key, value)
    sync_assessments(risk)
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