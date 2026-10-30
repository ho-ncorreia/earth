from fastapi import APIRouter, Depends
from fastapi import HTTPException
from sqlalchemy import MetaData, Table, func, inspect, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models import User

router = APIRouter(prefix="/admin", tags=["administration"])
admin_configure = require_permission("admin.configure")
SENSITIVE_COLUMN_MARKERS = ("password", "secret", "token", "api_key", "storage_name")


def redact_value(value):
    if isinstance(value, dict):
        return {key: "[REDACTED]" if any(marker in key.lower() for marker in SENSITIVE_COLUMN_MARKERS) else redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value


@router.get("/database/schema")
def database_schema(db: Session = Depends(get_db), _: User = Depends(admin_configure)) -> dict:
    inspector = inspect(db.get_bind())
    tables = []
    for table_name in sorted(inspector.get_table_names()):
        if table_name == "alembic_version":
            continue
        columns = inspector.get_columns(table_name)
        primary_keys = set(inspector.get_pk_constraint(table_name).get("constrained_columns") or [])
        foreign_keys = inspector.get_foreign_keys(table_name)
        foreign_key_columns = {column for key in foreign_keys for column in key.get("constrained_columns", [])}
        unique_columns = [set(item.get("column_names") or []) for item in inspector.get_unique_constraints(table_name)]
        unique_columns.extend(set(item.get("column_names") or []) for item in inspector.get_indexes(table_name) if item.get("unique"))
        metadata = MetaData()
        reflected_table = Table(table_name, metadata, autoload_with=db.get_bind())
        row_count = db.scalar(select(func.count()).select_from(reflected_table)) or 0
        tables.append({
            "name": table_name,
            "row_count": row_count,
            "columns": [{
                "name": column["name"],
                "type": str(column["type"]),
                "nullable": column["nullable"],
                "primary_key": column["name"] in primary_keys,
                "foreign_key": column["name"] in foreign_key_columns,
            } for column in columns],
            "foreign_keys": [{
                "columns": key.get("constrained_columns", []),
                "references_table": key.get("referred_table"),
                "references_columns": key.get("referred_columns", []),
                "from_cardinality": "1,1" if all(not next(column["nullable"] for column in columns if column["name"] == name) for name in key.get("constrained_columns", [])) else "0,1",
                "to_cardinality": "0,1" if set(key.get("constrained_columns", [])) == primary_keys or set(key.get("constrained_columns", [])) in unique_columns else "0,n",
            } for key in foreign_keys],
        })
    return {"database": inspector.dialect.name, "tables": tables}


@router.get("/database/tables/{table_name}/rows")
def database_table_rows(table_name: str, limit: int = 50, offset: int = 0, db: Session = Depends(get_db), _: User = Depends(admin_configure)) -> dict:
    if table_name == "alembic_version" or table_name not in inspect(db.get_bind()).get_table_names():
        raise HTTPException(status_code=404, detail="Table not found")
    limit, offset = min(max(limit, 1), 200), max(offset, 0)
    table = Table(table_name, MetaData(), autoload_with=db.get_bind())
    primary_key = list(table.primary_key.columns)
    statement = select(table).order_by(*primary_key) if primary_key else select(table)
    rows = db.execute(statement.limit(limit).offset(offset)).mappings().all()
    total = db.scalar(select(func.count()).select_from(table)) or 0
    sanitized = []
    for row in rows:
        sanitized.append({column: "[REDACTED]" if any(marker in column.lower() for marker in SENSITIVE_COLUMN_MARKERS) else redact_value(value) for column, value in row.items()})
    return {"table": table_name, "columns": [column.name for column in table.columns], "items": sanitized, "total": total, "limit": limit, "offset": offset}
