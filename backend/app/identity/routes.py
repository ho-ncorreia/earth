import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_event
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_csrf
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas import LoginRequest, UserOut

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/csrf")
def issue_csrf(response: Response) -> dict[str, str]:
    token = secrets.token_urlsafe(32)
    response.set_cookie("ea_csrf", token, httponly=False, secure=settings.cookie_secure, samesite="strict", path="/")
    return {"csrf_token": token}


@router.post("/login", response_model=UserOut, dependencies=[Depends(require_csrf)])
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> User:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    response.set_cookie(
        "ea_access", create_access_token(str(user.id)), httponly=True,
        secure=settings.cookie_secure, samesite="strict",
        max_age=settings.access_token_minutes * 60, path="/",
    )
    record_event(db, actor=user, action="user.login", object_type="user", object_id=str(user.id), origin="local-auth")
    db.commit()
    return user


@router.post("/logout", dependencies=[Depends(require_csrf)])
def logout(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    record_event(db, actor=user, action="user.logout", object_type="user", object_id=str(user.id))
    db.commit()
    response.delete_cookie("ea_access", path="/", secure=settings.cookie_secure, httponly=True, samesite="strict")
    return {"status": "signed_out"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user