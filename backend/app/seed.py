import sys

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Permission, Role, User

ROLE_PERMISSIONS = {
    "Administrator": ["users.read", "users.write", "audit.read", "admin.configure", "studies.read", "studies.write", "risks.read", "risks.write", "decisions.read", "decisions.write", "decisions.review", "assistant.use"],
    "Enterprise Architect": ["architecture.read", "architecture.write", "audit.read", "studies.read", "studies.write", "risks.read", "risks.write", "decisions.read", "decisions.write", "assistant.use"],
    "Solution Architect": ["architecture.read", "architecture.contribute", "studies.read", "risks.read", "risks.write", "decisions.read", "decisions.write", "assistant.use"],
    "Technical Architect": ["architecture.read", "architecture.contribute", "technical.review", "studies.read", "risks.read", "risks.write", "decisions.read", "decisions.write", "decisions.review", "assistant.use"],
    "Reviewer / ARB Member": ["architecture.read", "architecture.review", "studies.read", "risks.read", "decisions.read", "decisions.review", "assistant.use"],
    "Read-only User": ["architecture.read", "studies.read", "risks.read", "decisions.read", "assistant.use"],
}


def main() -> None:
    email = settings.bootstrap_admin_email.strip().lower()
    password = settings.bootstrap_admin_password
    try:
        TypeAdapter(EmailStr).validate_python(email)
    except ValidationError:
        print("Set EA_BOOTSTRAP_ADMIN_EMAIL to a valid, non-placeholder email address.", file=sys.stderr)
        raise SystemExit(2)
    if len(password) < 16 or password.lower().startswith("replace-") or settings.secret_key.lower().startswith("replace-"):
        print("Set EA_SECRET_KEY and a unique EA_BOOTSTRAP_ADMIN_PASSWORD (at least 16 characters); example placeholders are rejected.", file=sys.stderr)
        raise SystemExit(2)
    with SessionLocal.begin() as db:
        permissions = {}
        for code in sorted({item for values in ROLE_PERMISSIONS.values() for item in values}):
            permission = db.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(code=code, description=code.replace(".", " ").title())
                db.add(permission)
            permissions[code] = permission
        for name, codes in ROLE_PERMISSIONS.items():
            role = db.scalar(select(Role).where(Role.name == name))
            if role is None:
                role = Role(name=name, description=f"{name} access profile")
                db.add(role)
            role.permissions = [permissions[code] for code in codes]
        db.flush()
        admin_role = db.scalar(select(Role).where(Role.name == "Administrator"))
        admin = db.scalar(select(User).where(User.email == email))
        if admin is None:
            db.add(User(email=email, display_name="Workbench Administrator", password_hash=hash_password(settings.bootstrap_admin_password), role=admin_role))
        else:
            admin.role = admin_role
    print("Roles and bootstrap administrator are ready.")


if __name__ == "__main__":
    main()