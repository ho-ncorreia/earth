from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_event
from app.core.database import get_db
from app.core.dependencies import require_csrf, require_permission
from app.core.security import hash_password
from app.models import Role, User
from app.schemas import Page, RoleOut, UserCreate, UserOut, UserPasswordReset, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])
admin_user_read = require_permission("users.read")
admin_user_write = require_permission("users.write")


@router.get("", response_model=Page[UserOut])
def list_users(limit: int = 25, offset: int = 0, db: Session = Depends(get_db), _: User = Depends(admin_user_read)) -> dict:
    limit, offset = min(max(limit, 1), 100), max(offset, 0)
    users = db.scalars(select(User).order_by(User.email).limit(limit).offset(offset)).all()
    return {"items": users, "total": db.scalar(select(func.count(User.id))) or 0, "limit": limit, "offset": offset}


@router.get("/roles", response_model=list[RoleOut])
def list_roles(db: Session = Depends(get_db), _: User = Depends(admin_user_read)) -> list[Role]:
    return list(db.scalars(select(Role).order_by(Role.name)).all())


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
def create_user(payload: UserCreate, request: Request, db: Session = Depends(get_db), actor: User = Depends(admin_user_write)) -> User:
    email = str(payload.email).lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="A user with this email already exists")
    role = db.get(Role, payload.role_id)
    if role is None:
        raise HTTPException(status_code=422, detail="Unknown role")
    user = User(email=email, display_name=payload.display_name.strip(), password_hash=hash_password(payload.temporary_password), role=role)
    db.add(user)
    db.flush()
    record_event(
        db, actor=actor, action="user.created", object_type="user", object_id=str(user.id),
        new_value={"email": user.email, "role": role.name},
        correlation_id=request.headers.get("x-correlation-id", ""),
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut, dependencies=[Depends(require_csrf)])
def update_user(user_id: int, payload: UserUpdate, request: Request, db: Session = Depends(get_db), actor: User = Depends(admin_user_write)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("role_id") is not None:
        role = db.get(Role, changes["role_id"])
        if role is None:
            raise HTTPException(status_code=422, detail="Unknown role")
        changes["role_id"] = role.id
    if actor.id == user.id and changes.get("is_active") is False:
        raise HTTPException(status_code=409, detail="You cannot deactivate your own account")
    previous = {key: getattr(user, key) for key in changes}
    for key, value in changes.items():
        setattr(user, key, value.strip() if key == "display_name" and value is not None else value)
    record_event(db, actor=actor, action="user.updated", object_type="user", object_id=str(user.id), previous_value=previous, new_value=changes, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/password", status_code=204, dependencies=[Depends(require_csrf)])
def reset_user_password(user_id: int, payload: UserPasswordReset, request: Request, db: Session = Depends(get_db), actor: User = Depends(admin_user_write)) -> Response:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(payload.temporary_password)
    record_event(db, actor=actor, action="user.password_reset", object_type="user", object_id=str(user.id), new_value={"password_reset": True}, correlation_id=request.headers.get("x-correlation-id", ""))
    db.commit()
    return Response(status_code=204)