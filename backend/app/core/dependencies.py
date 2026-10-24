import secrets

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("ea_access")
    subject = decode_access_token(token) if token else None
    user = db.scalar(select(User).where(User.id == int(subject))) if subject and subject.isdigit() else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def require_csrf(request: Request) -> None:
    cookie = request.cookies.get("ea_csrf", "")
    header = request.headers.get("x-csrf-token", "")
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


def require_permission(permission_code: str):
    def check(user: User = Depends(get_current_user)) -> User:
        granted = {permission.code for permission in user.role.permissions}
        if permission_code not in granted:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission")
        return user

    return check