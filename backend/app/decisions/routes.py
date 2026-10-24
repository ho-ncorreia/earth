from datetime import date
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.audit.service import record_event
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_csrf
from app.models import ArchitectureDecision, ArchitectureRisk, ArchitectureStudy, DecisionOption, DecisionVersion, User
from app.schemas import DecisionCreate, DecisionOut, DecisionUpdate, DecisionVersionOut, Page

router = APIRouter(prefix="/decisions", tags=["architecture decisions"])
TRANSITIONS = {
    "Draft": {"Proposed", "Deprecated"},
    "Proposed": {"Draft", "Under Review", "Deprecated"},
    "Under Review": {"Proposed", "Accepted", "Rejected"},
    "Accepted": {"Superseded", "Deprecated"},
    "Rejected": {"Draft", "Deprecated"},
    "Superseded": {"Deprecated"},
    "Deprecated": set(),
}
CONTENT_FIELDS = (
    "title", "context", "problem_statement", "decision_drivers", "selected_option", "decision_rationale",
    "positive_consequences", "negative_consequences", "assumptions", "constraints", "principles",
    "patterns_and_standards", "decision_authority", "rejection_rationale", "decision_date", "review_date",
)


def require_decision_permission(user: User, code: str) -> None:
    if code not in {permission.code for permission in user.role.permissions}:
        raise HTTPException(status_code=403, detail="Insufficient permission")


def can_read_decision(decision: ArchitectureDecision, user: User) -> bool:
    if user.role.name == "Administrator" or decision.owner_id == user.id:
        return True
    return all(study.confidentiality != "Restricted" or study.lead_architect_id == user.id for study in decision.related_studies)


def decision_snapshot(decision: ArchitectureDecision) -> dict:
    return {
        "number": decision.number,
        "title": decision.title,
        **{field: getattr(decision, field).isoformat() if isinstance(getattr(decision, field), date) else getattr(decision, field) for field in CONTENT_FIELDS},
        "status": decision.status,
        "selected_option": decision.selected_option,
        "options": [
            {"title": option.title, "description": option.description, "advantages": option.advantages, "disadvantages": option.disadvantages}
            for option in decision.options
        ],
        "related_study_ids": [study.id for study in decision.related_studies],
        "related_risk_ids": [risk.id for risk in decision.related_risks],
        "superseded_by_id": decision.superseded_by_id,
        "version": decision.version,
    }


def validate_related_ids(db: Session, user: User, study_ids: list[int] | None, risk_ids: list[int] | None) -> tuple[list[ArchitectureStudy], list[ArchitectureRisk]]:
    studies = list(db.scalars(select(ArchitectureStudy).where(ArchitectureStudy.id.in_(set(study_ids or [])))).all()) if study_ids else []
    risks = list(db.scalars(select(ArchitectureRisk).where(ArchitectureRisk.id.in_(set(risk_ids or [])))).all()) if risk_ids else []
    if len(studies) != len(set(study_ids or [])) or len(risks) != len(set(risk_ids or [])):
        raise HTTPException(status_code=422, detail="One or more related study/risk IDs do not exist")
    if user.role.name != "Administrator" and any(study.confidentiality == "Restricted" and study.lead_architect_id != user.id for study in studies):
        raise HTTPException(status_code=404, detail="Related architecture object not found")
    return studies, risks


def validate_decision_state(decision: ArchitectureDecision, target_status: str) -> None:
    if target_status in {"Proposed", "Under Review"} and len(decision.options) < 2:
        raise HTTPException(status_code=422, detail="A proposed ADR must contain at least two options")
    if target_status == "Accepted":
        if not decision.decision_authority.strip() or decision.decision_date is None:
            raise HTTPException(status_code=422, detail="An accepted ADR requires a decision authority and decision date")
        if not decision.selected_option or decision.selected_option not in {option.title for option in decision.options}:
            raise HTTPException(status_code=422, detail="The selected option must match a considered option")
    if target_status == "Rejected" and not decision.rejection_rationale.strip():
        raise HTTPException(status_code=422, detail="A rejected ADR requires a rejection rationale")
    if target_status == "Superseded":
        if decision.superseded_by_id is None or decision.superseded_by_id == decision.id:
            raise HTTPException(status_code=422, detail="A superseded ADR must reference its replacing ADR")


def set_etag(response: Response, decision: ArchitectureDecision) -> None:
    response.headers["ETag"] = f'"{decision.row_version}"'


@router.get("", response_model=Page[DecisionOut])
def list_decisions(
    limit: int = 25,
    offset: int = 0,
    status_filter: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    require_decision_permission(user, "decisions.read")
    limit, offset = min(max(limit, 1), 100), max(offset, 0)
    statement = select(ArchitectureDecision).order_by(ArchitectureDecision.updated_at.desc())
    if status_filter:
        statement = statement.where(ArchitectureDecision.status == status_filter)
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(or_(ArchitectureDecision.number.ilike(pattern), ArchitectureDecision.title.ilike(pattern), ArchitectureDecision.context.ilike(pattern)))
    decisions = [decision for decision in db.scalars(statement).all() if can_read_decision(decision, user)]
    total = len(decisions)
    return {"items": decisions[offset:offset + limit], "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=DecisionOut, status_code=201, dependencies=[Depends(require_csrf)])
def create_decision(payload: DecisionCreate, request: Request, response: Response, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ArchitectureDecision:
    require_decision_permission(user, "decisions.write")
    studies, risks = validate_related_ids(db, user, payload.related_study_ids, payload.related_risk_ids)
    values = payload.model_dump(exclude={"options", "related_study_ids", "related_risk_ids"})
    decision = ArchitectureDecision(number=f"ADR-{date.today().year}-{uuid4().hex[:6].upper()}", owner_id=user.id, **values)
    decision.options = [DecisionOption(position=index, **option.model_dump()) for index, option in enumerate(payload.options)]
    decision.related_studies = studies
    decision.related_risks = risks
    db.add(decision)
    db.flush()
    db.add(DecisionVersion(decision_id=decision.id, version=1, snapshot=decision_snapshot(decision), created_by_id=user.id))
    record_event(db, actor=user, action="decision.created", object_type="decision", object_id=str(decision.id), new_value={"number": decision.number, "title": decision.title}, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(decision)
    set_etag(response, decision)
    return decision


@router.get("/{decision_id}", response_model=DecisionOut)
def get_decision(decision_id: int, response: Response, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ArchitectureDecision:
    require_decision_permission(user, "decisions.read")
    decision = db.get(ArchitectureDecision, decision_id)
    if decision is None or not can_read_decision(decision, user):
        raise HTTPException(status_code=404, detail="ADR not found")
    set_etag(response, decision)
    return decision


@router.patch("/{decision_id}", response_model=DecisionOut, dependencies=[Depends(require_csrf)])
def update_decision(
    decision_id: int,
    payload: DecisionUpdate,
    request: Request,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ArchitectureDecision:
    decision = db.get(ArchitectureDecision, decision_id)
    if decision is None or not can_read_decision(decision, user):
        raise HTTPException(status_code=404, detail="ADR not found")
    changes = payload.model_dump(exclude_unset=True)
    requires_review = changes.get("status") in {"Under Review", "Accepted", "Rejected"}
    require_decision_permission(user, "decisions.review" if requires_review else "decisions.write")
    if if_match is None:
        raise HTTPException(status_code=428, detail="If-Match with the current ETag is required")
    if if_match.strip('"') != str(decision.row_version):
        raise HTTPException(status_code=412, detail="ADR was modified; reload before updating")
    old_status = decision.status
    target_status = changes.get("status", old_status)
    if target_status != old_status and target_status not in TRANSITIONS[old_status]:
        raise HTTPException(status_code=409, detail=f"Invalid ADR transition: {old_status} to {target_status}")
    related_studies = related_risks = None
    if "related_study_ids" in changes or "related_risk_ids" in changes:
        related_studies, related_risks = validate_related_ids(
            db, user,
            changes.pop("related_study_ids", [study.id for study in decision.related_studies]),
            changes.pop("related_risk_ids", [risk.id for risk in decision.related_risks]),
        )
    options = changes.pop("options", None)
    previous = decision_snapshot(decision)
    for key, value in changes.items():
        setattr(decision, key, value)
    if options is not None:
        decision.options.clear()
        decision.options.extend(DecisionOption(position=index, **option.model_dump()) for index, option in enumerate(options))
    if related_studies is not None:
        decision.related_studies = related_studies
        decision.related_risks = related_risks or []
    if decision.superseded_by_id is not None:
        replacing = db.get(ArchitectureDecision, decision.superseded_by_id)
        if replacing is None or replacing.id == decision.id:
            raise HTTPException(status_code=422, detail="The replacing ADR does not exist")
    validate_decision_state(decision, target_status)
    decision.status = target_status
    should_version = target_status == "Accepted" and (old_status != "Accepted" or bool(changes or options is not None or related_studies is not None))
    if should_version:
        decision.version += 1
        db.add(DecisionVersion(decision_id=decision.id, version=decision.version, snapshot=decision_snapshot(decision), created_by_id=user.id))
    record_event(db, actor=user, action="decision.updated", object_type="decision", object_id=str(decision.id), previous_value=previous, new_value=decision_snapshot(decision), correlation_id=request.headers.get("x-correlation-id", ""))
    try:
        db.commit()
    except StaleDataError as exc:
        db.rollback()
        raise HTTPException(status_code=412, detail="ADR was modified; reload before updating") from exc
    db.refresh(decision)
    set_etag(response, decision)
    return decision


@router.delete("/{decision_id}", status_code=204, dependencies=[Depends(require_csrf)])
def delete_decision(decision_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    require_decision_permission(user, "decisions.write")
    decision = db.get(ArchitectureDecision, decision_id)
    if decision is None or decision.owner_id != user.id and user.role.name != "Administrator":
        raise HTTPException(status_code=404, detail="ADR not found")
    if decision.status != "Draft":
        raise HTTPException(status_code=409, detail="Only draft ADRs can be deleted")
    record_event(db, actor=user, action="decision.deleted", object_type="decision", object_id=str(decision.id), previous_value={"number": decision.number, "title": decision.title})
    db.delete(decision)
    db.commit()
    return Response(status_code=204)


@router.get("/{decision_id}/versions", response_model=list[DecisionVersionOut])
def list_versions(decision_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[DecisionVersion]:
    require_decision_permission(user, "decisions.read")
    decision = db.get(ArchitectureDecision, decision_id)
    if decision is None or not can_read_decision(decision, user):
        raise HTTPException(status_code=404, detail="ADR not found")
    return list(decision.versions)


@router.get("/{decision_id}/compare")
def compare_versions(decision_id: int, from_version: int, to_version: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    require_decision_permission(user, "decisions.read")
    decision = db.get(ArchitectureDecision, decision_id)
    if decision is None or not can_read_decision(decision, user):
        raise HTTPException(status_code=404, detail="ADR not found")
    versions = db.scalars(select(DecisionVersion).where(DecisionVersion.decision_id == decision_id, DecisionVersion.version.in_([from_version, to_version]))).all()
    snapshots = {item.version: item.snapshot for item in versions}
    if from_version not in snapshots or to_version not in snapshots:
        raise HTTPException(status_code=404, detail="ADR version not found")
    before, after = snapshots[from_version], snapshots[to_version]
    diff = {key: {"from": before.get(key), "to": after.get(key)} for key in before.keys() | after.keys() if before.get(key) != after.get(key)}
    return {"decision_id": decision_id, "from_version": from_version, "to_version": to_version, "changes": diff}