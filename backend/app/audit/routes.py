from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models import AuditEvent, User
from app.schemas import AuditEventOut, Page

router = APIRouter(prefix="/audit-events", tags=["audit"])


@router.get("", response_model=Page[AuditEventOut])
def list_events(limit: int = 25, offset: int = 0, db: Session = Depends(get_db), _: User = Depends(require_permission("audit.read"))) -> dict:
    limit, offset = min(max(limit, 1), 100), max(offset, 0)
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit).offset(offset)).all()
    return {"items": events, "total": db.scalar(select(func.count(AuditEvent.id))) or 0, "limit": limit, "offset": offset}