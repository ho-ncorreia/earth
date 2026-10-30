import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models import Permission, Role, User


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    test_sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with test_sessions.begin() as db:
        permissions = {code: Permission(code=code) for code in (
            "users.read", "users.write", "audit.read", "admin.configure", "studies.read", "studies.write", "studies.approve", "risks.read", "risks.write", "risks.approve",
            "decisions.read", "decisions.write", "decisions.review", "assistant.use",
        )}
        admin_role = Role(name="Administrator", permissions=list(permissions.values()))
        read_role = Role(name="Read-only User", permissions=[permissions["studies.read"], permissions["risks.read"], permissions["decisions.read"], permissions["assistant.use"]])
        db.add_all([admin_role, read_role])
        db.flush()
        db.add_all([
            User(email="admin@example.com", display_name="Test Admin", password_hash=hash_password("correct-test-password"), role=admin_role),
            User(email="reader@example.com", display_name="Test Reader", password_hash=hash_password("correct-test-password"), role=read_role),
        ])

    def override_get_db():
        with test_sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
def test_health_liveness_is_available_without_authentication() -> None:
    response = TestClient(app).get("/health/live")
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "alive"}


def test_ardoq_settings_and_component_lookup(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.risks import routes

    monkeypatch.setattr(routes.settings, "ardoq_api_token", "test-ardoq-token")
    monkeypatch.setattr(routes.settings, "ardoq_org_label", "test-org")
    monkeypatch.setattr(routes.settings, "ardoq_api_host", "https://ardoq.example.test")
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    headers = {"X-CSRF-Token": csrf}
    client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "correct-test-password"}, headers=headers).raise_for_status()
    configuration = client.get("/api/v1/risks/settings/ardoq")
    configuration.raise_for_status()
    assert configuration.json()["token_configured"] is True
    assert "test-ardoq-token" not in configuration.text
    assert {"APPLICATION", "TECHNOLOGY_COMPONENT", "DATA_ENTITY", "ARCHITECTURE_AREA", "BUSINESS_CAPABILITY", "BUSINESS_UNIT", "PROVIDER_THIRD_PARTY"} <= {item["code"] for item in configuration.json()["object_types"]}
    object_code = configuration.json()["object_types"][0]["code"]
    payload = {"root_workspace_id": "workspace-test", "component_type_ids": {object_code: "type-test"}}
    assert client.put("/api/v1/risks/settings/ardoq", json=payload).status_code == 403
    saved = client.put("/api/v1/risks/settings/ardoq", json=payload, headers=headers)
    saved.raise_for_status()
    assert saved.json()["component_type_ids"][object_code] == "type-test"
    assert client.put("/api/v1/risks/settings/ardoq", json={**payload, "component_type_ids": {"unknown": "type-test"}}, headers=headers).status_code == 422

    def handle_request(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith("https://ardoq.example.test/api/v2/components?")
        assert request.headers["Authorization"] == "Bearer test-ardoq-token"
        assert request.headers["X-org"] == "test-org"
        assert dict(request.url.params) == {"rootWorkspace": "workspace-test", "name": "Cargo", "typeId": "type-test"}
        return httpx.Response(200, json={"values": [
            {"_id": "component-id", "componentKey": "APP-123", "name": "Cargo", "type": "Application", "typeId": "type-test"},
            {"_id": "fallback-id", "name": "Cargo data", "typeId": "type-test"},
        ]})

    async_client = httpx.AsyncClient
    monkeypatch.setattr(routes.httpx, "AsyncClient", lambda **kwargs: async_client(**kwargs, transport=httpx.MockTransport(handle_request)))
    query = {"object_type_code": object_code, "label": " Cargo "}
    result = client.get("/api/v1/risks/ardoq/components", params=query)
    result.raise_for_status()
    assert [item["code"] for item in result.json()] == ["APP-123", "fallback-id"]
    assert result.json()[0]["name"] == "Cargo"
    assert client.get("/api/v1/risks/ardoq/components", params={**query, "label": "a"}).status_code == 422
    client.put("/api/v1/risks/settings/ardoq", json={**payload, "component_type_ids": {}}, headers=headers).raise_for_status()
    assert client.get("/api/v1/risks/settings/ardoq").json()["component_type_ids"][object_code] == ""
    assert client.get("/api/v1/risks/ardoq/components", params=query).status_code == 503
    monkeypatch.setattr(routes.settings, "ardoq_api_token", "")
    assert client.get("/api/v1/risks/ardoq/components", params=query).status_code == 503
    client.post("/api/v1/auth/logout", headers=headers)
    client.post("/api/v1/auth/login", json={"email": "reader@example.com", "password": "correct-test-password"}, headers=headers).raise_for_status()
    assert client.get("/api/v1/risks/settings/ardoq").status_code == 403
    assert client.put("/api/v1/risks/settings/ardoq", json=payload, headers=headers).status_code == 403
    assert client.get("/api/v1/risks/ardoq/components", params=query).status_code == 403


@pytest.mark.parametrize("failure", ["unauthorized", "timeout"])
def test_ardoq_upstream_failures_are_reported(client: TestClient, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    from app.risks import routes

    monkeypatch.setattr(routes.settings, "ardoq_api_token", "test-token")
    monkeypatch.setattr(routes.settings, "ardoq_org_label", "test-org")
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    headers = {"X-CSRF-Token": csrf}
    client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "correct-test-password"}, headers=headers).raise_for_status()
    object_code = client.get("/api/v1/risks/settings/ardoq").json()["object_types"][0]["code"]
    client.put("/api/v1/risks/settings/ardoq", json={"root_workspace_id": "workspace", "component_type_ids": {object_code: "type"}}, headers=headers).raise_for_status()

    def handle_request(request: httpx.Request) -> httpx.Response:
        if failure == "timeout":
            raise httpx.ReadTimeout("upstream timeout", request=request)
        return httpx.Response(401, text="private upstream error")

    async_client = httpx.AsyncClient
    monkeypatch.setattr(routes.httpx, "AsyncClient", lambda **kwargs: async_client(**kwargs, transport=httpx.MockTransport(handle_request)))
    response = client.get("/api/v1/risks/ardoq/components", params={"object_type_code": object_code, "label": "Cargo"})
    assert response.status_code == 502
    assert "test-token" not in response.text
    assert "private upstream error" not in response.text


def test_mutation_rejects_missing_csrf_token() -> None:
    response = TestClient(app).post("/api/v1/auth/login", json={"email": "a@example.test", "password": "not-a-password"})
    assert response.status_code == 403


def test_login_sets_http_only_cookie_and_openapi_lists_versioned_routes(client: TestClient) -> None:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "correct-test-password"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200, response.text
    assert "httponly" in response.headers["set-cookie"].lower()
    assert client.get("/api/v1/auth/me").json()["role"]["name"] == "Administrator"
    specification = client.get("/api/v1/openapi.json").json()
    assert "/api/v1/users" in specification["paths"]


def test_authenticated_read_only_role_cannot_access_user_admin(client: TestClient) -> None:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "reader@example.com", "password": "correct-test-password"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert client.get("/api/v1/users").status_code == 403


def test_risk_catalog_is_idempotent_and_risk_associations_are_validated(client: TestClient) -> None:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})

    taxonomy = client.get("/api/v1/risks/catalog").json()
    definitions = client.get("/api/v1/risks/catalog/help").json()
    client.get("/api/v1/risks/catalog").raise_for_status()
    assert len(taxonomy) == 8
    assert sum(len(family["types"]) for family in taxonomy) == 28
    assert [item["risk_code"] for item in definitions] == [f"RISK_{number:03d}" for number in range(1, 29)]
    assert client.get("/api/v1/risks?limit=100").json()["total"] == 0
    assert definitions[11]["data_quality_notes"] == ["Incomplete"]
    assert "à confirmer" in definitions[13]["data_quality_notes"][0]
    assert client.get("/api/v1/risks/settings/mitigations").json() == {"mitigation_validation_stale_days": 365}
    setting_update = client.put("/api/v1/risks/settings/mitigations", json={"mitigation_validation_stale_days": 180}, headers={"X-CSRF-Token": csrf})
    assert setting_update.status_code == 200
    assert setting_update.json()["mitigation_validation_stale_days"] == 180

    help_update = {
        "title_en": definitions[0]["title_en"], "title_fr": definitions[0]["title_fr"],
        "description_en": definitions[0]["description_en"], "description_fr": "Description française de test.",
        "causes": definitions[0]["causes"], "causes_fr": ["Cause française de test."],
        "impacts": definitions[0]["impacts"], "impacts_fr": ["Impact français de test."],
        "data_quality_notes": definitions[0]["data_quality_notes"],
    }
    edited_help = client.patch("/api/v1/risks/catalog/help/RISK_001", json=help_update, headers={"X-CSRF-Token": csrf})
    assert edited_help.status_code == 200, edited_help.text
    assert edited_help.json()["description_fr"] == "Description française de test."

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    client.post("/api/v1/auth/login", json={"email": "reader@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    denied_help_edit = client.patch("/api/v1/risks/catalog/help/RISK_001", json=help_update, headers={"X-CSRF-Token": csrf})
    assert denied_help_edit.status_code == 403
    denied_setting_edit = client.put("/api/v1/risks/settings/mitigations", json={"mitigation_validation_stale_days": 90}, headers={"X-CSRF-Token": csrf})
    assert denied_setting_edit.status_code == 403
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})

    invalid = client.post("/api/v1/risks", json={
        "title": "Invalid taxonomy", "description": "Family and subfamily do not match.", "probability": 2, "impact": 2,
        "family_id": "F01", "subfamily_id": "F02.01", "risk_definition_id": "RDEF_004",
    }, headers={"X-CSRF-Token": csrf})
    assert invalid.status_code == 422

    created = client.post("/api/v1/risks", json={
        "title": "Provider outage", "description": "A provider outage may interrupt services.", "probability": 4, "impact": 3,
        "family_id": "F01", "subfamily_id": "F01.01", "risk_definition_id": "RDEF_001",
        "objects": [{"object_type": "Application", "object_ref": "APP-1"}],
        "sources": [{"source_type": "Project", "source_ref": "PRJ-1"}],
        "scopes": [{"scope_type": "Domain", "scope_ref": "Payments"}],
        "mitigations": [{"title": "Provider fallback", "description": "Deploy a fallback.", "residual_probability": 2, "residual_impact": 2}],
    }, headers={"X-CSRF-Token": csrf})
    assert created.status_code == 201, created.text
    risk = created.json()
    assert risk["family_label"] == "Gouvernance & Décisions d’architecture"
    assert risk["subfamily_id"] == "F01.01"
    assert risk["objects"][0]["risk_id"] == risk["id"]
    assert risk["sources"][0]["risk_id"] == risk["id"]
    assert risk["scopes"][0]["risk_id"] == risk["id"]
    mitigation = risk["mitigations"][0]
    assert mitigation["status"] == "Draft"
    assert mitigation["risk_id"] == risk["id"]
    assert mitigation["residual_score"] == 4
    assert {item["assessment_type"]: item["criticality"] for item in risk["assessments"]} == {"Inherent": 12, "Residual": 4}

    mitigation_update = client.patch(f"/api/v1/risks/mitigations/{mitigation['mitigation_id']}", json={
        "description": "Deploy and test a fallback.", "residual_probability": 1, "residual_impact": 2,
    }, headers={"X-CSRF-Token": csrf})
    assert mitigation_update.status_code == 200, mitigation_update.text
    assert mitigation_update.json()["risk_id"] == risk["id"]
    assert mitigation_update.json()["status"] == "Draft"
    assert mitigation_update.json()["residual_score"] == 2

    submitted = client.post(f"/api/v1/risks/mitigations/{mitigation['mitigation_id']}/submit", headers={"X-CSRF-Token": csrf})
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "Submitted"
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    client.post("/api/v1/auth/login", json={"email": "reader@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    denied_review = client.post(f"/api/v1/risks/mitigations/{mitigation['mitigation_id']}/review", json={"decision": "Approved"}, headers={"X-CSRF-Token": csrf})
    assert denied_review.status_code == 403
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    approved = client.post(f"/api/v1/risks/mitigations/{mitigation['mitigation_id']}/review", json={"decision": "Approved", "comment": "Reviewed."}, headers={"X-CSRF-Token": csrf})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "Approved"
    assert approved.json()["validated_at"]
    assert approved.json()["reviews"][-1]["reviewer_name"] == "Test Admin"
    edited_after_approval = client.patch(f"/api/v1/risks/mitigations/{mitigation['mitigation_id']}", json={"description": "Revised and ready for another review."}, headers={"X-CSRF-Token": csrf})
    assert edited_after_approval.status_code == 200
    assert edited_after_approval.json()["status"] == "Draft"
    assert edited_after_approval.json()["validated_at"] is None

    incompatible_update = client.patch(f"/api/v1/risks/{risk['id']}", json={"family_id": "F02"}, headers={"X-CSRF-Token": csrf})
    assert incompatible_update.status_code == 422


def test_administrator_creates_user_and_audits_without_password(client: TestClient) -> None:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "correct-test-password"},
        headers={"X-CSRF-Token": csrf},
    )
    role_id = next(role["id"] for role in client.get("/api/v1/users/roles").json() if role["name"] == "Read-only User")
    response = client.post(
        "/api/v1/users",
        json={"email": "new-user@example.com", "display_name": "New User", "role_id": role_id, "temporary_password": "temporary-password-123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201
    assert response.json()["role"]["name"] == "Read-only User"
    assert client.get("/api/v1/users").json()["total"] == 3
    events = client.get("/api/v1/audit-events").json()["items"]
    created_event = next(event for event in events if event["action"] == "user.created")
    assert created_event["new_value"] == {"email": "new-user@example.com", "role": "Read-only User"}
    assert "temporary-password-123" not in response.text


def test_administrator_edits_user_and_resets_password_without_auditing_secret(client: TestClient) -> None:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    reader = next(item for item in client.get("/api/v1/users").json()["items"] if item["email"] == "reader@example.com")
    changed = client.patch(f"/api/v1/users/{reader['id']}", json={"display_name": "Updated Reader", "is_active": True}, headers={"X-CSRF-Token": csrf})
    assert changed.status_code == 200
    assert changed.json()["display_name"] == "Updated Reader"
    replacement_password = "new-temporary-password-456"
    reset = client.post(f"/api/v1/users/{reader['id']}/password", json={"temporary_password": replacement_password}, headers={"X-CSRF-Token": csrf})
    assert reset.status_code == 204
    events = client.get("/api/v1/audit-events").json()["items"]
    reset_event = next(item for item in events if item["action"] == "user.password_reset")
    assert reset_event["new_value"] == {"password_reset": True}
    assert replacement_password not in reset_event.__str__()
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    login = client.post("/api/v1/auth/login", json={"email": "reader@example.com", "password": replacement_password}, headers={"X-CSRF-Token": csrf})
    assert login.status_code == 200


def test_database_schema_view_is_admin_only_and_contains_structure_not_rows(client: TestClient) -> None:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    schema = client.get("/api/v1/admin/database/schema")
    assert schema.status_code == 200, schema.text
    tables = {item["name"]: item for item in schema.json()["tables"]}
    assert "architecture_risks" in tables
    assert "risk_mitigations" in tables
    assert any(column["name"] == "risk_id" and column["foreign_key"] for column in tables["risk_mitigations"]["columns"])
    mitigation_relation = next(item for item in tables["risk_mitigations"]["foreign_keys"] if item["references_table"] == "architecture_risks")
    assert mitigation_relation["from_cardinality"] == "1,1"
    assert mitigation_relation["to_cardinality"] == "0,n"
    assert "items" not in schema.json()
    user_rows = client.get("/api/v1/admin/database/tables/users/rows?limit=1").json()
    assert user_rows["total"] == 2
    assert len(user_rows["items"]) == 1
    assert user_rows["items"][0]["password_hash"] == "[REDACTED]"

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    client.post("/api/v1/auth/login", json={"email": "reader@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    assert client.get("/api/v1/admin/database/schema").status_code == 403


def test_study_and_risk_workflow_persists_backend_scores(client: TestClient) -> None:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "correct-test-password"},
        headers={"X-CSRF-Token": csrf},
    )
    domain_response = client.post("/api/v1/studies/domains", json={"name": "Infrastructure"}, headers={"X-CSRF-Token": csrf})
    assert domain_response.status_code == 201, domain_response.text
    study_response = client.post(
        "/api/v1/studies",
        json={"title": "Cloud transition", "architecture_domain_id": domain_response.json()["id"], "jira_jpd_url": "https://jira.example/browse/EA-42", "confluence_url": "https://confluence.example/pages/architecture"},
        headers={"X-CSRF-Token": csrf},
    )
    assert study_response.status_code == 201, study_response.text
    study = study_response.json()
    assert study["identifier"].startswith("STU-")
    assert study["jira_jpd_url"].endswith("EA-42")
    assert study["confluence_url"].endswith("architecture")
    update = client.patch(
        f"/api/v1/studies/{study['id']}",
        json={"status": "In Progress", "target_review_date": "2026-11-15"},
        headers={"X-CSRF-Token": csrf},
    )
    assert update.status_code == 200, update.text
    assert update.json()["row_version"] == 2
    ready = client.patch(f"/api/v1/studies/{study['id']}", json={"status": "Ready for Review"}, headers={"X-CSRF-Token": csrf})
    assert ready.status_code == 200
    under_review = client.patch(f"/api/v1/studies/{study['id']}", json={"status": "Under Review"}, headers={"X-CSRF-Token": csrf})
    assert under_review.status_code == 200
    approved_study = client.patch(f"/api/v1/studies/{study['id']}", json={"status": "Approved"}, headers={"X-CSRF-Token": csrf})
    assert approved_study.status_code == 200
    archived_study = client.patch(f"/api/v1/studies/{study['id']}", json={"status": "Archived"}, headers={"X-CSRF-Token": csrf})
    assert archived_study.status_code == 200
    reactivated = client.patch(f"/api/v1/studies/{study['id']}", json={"status": "In Progress"}, headers={"X-CSRF-Token": csrf})
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "In Progress"
    risk_response = client.post(
        "/api/v1/risks",
        json={"title": "Provider outage", "description": "A cloud provider outage may interrupt critical services.", "probability": 4, "impact": 3, "study_id": study["id"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert risk_response.status_code == 201, risk_response.text
    risk = risk_response.json()
    assert risk["inherent_score"] == 12
    assert risk["criticality"] == "Critical"
    assert risk["residual_score"] is None
    assert len(risk["mitigations"]) == 1
    assert risk["mitigations"][0]["title"] == ""
    assert risk["mitigations"][0]["status"] == "Draft"
    assert risk["mitigations"][0]["risk_id"] == risk["id"]
    incomplete_submission = client.post(f"/api/v1/risks/mitigations/{risk['mitigations'][0]['mitigation_id']}/submit", headers={"X-CSRF-Token": csrf})
    assert incomplete_submission.status_code == 422
    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["studies"] == 1
    assert dashboard["open_risks"] == 1
    assert dashboard["critical_risks"] == 1
    assert dashboard["average_open_risk_score"] == 12
    assert dashboard["mitigations_not_validated"] == 1
    assert dashboard["mitigations_stale"] == 0
    assert client.patch(f"/api/v1/risks/{risk['id']}", json={"status": "Reopened"}, headers={"X-CSRF-Token": csrf}).status_code == 409
    in_progress = client.patch(f"/api/v1/risks/{risk['id']}", json={"status": "In Progress"}, headers={"X-CSRF-Token": csrf})
    assert in_progress.status_code == 200
    closed = client.patch(f"/api/v1/risks/{risk['id']}", json={"status": "Closed"}, headers={"X-CSRF-Token": csrf})
    assert closed.status_code == 200
    reopened = client.patch(f"/api/v1/risks/{risk['id']}", json={"status": "Reopened"}, headers={"X-CSRF-Token": csrf})
    assert reopened.status_code == 200
    assert client.get(f"/api/v1/risks/{risk['id']}").json()["inherent_score"] == 12


def test_risk_score_inputs_are_bounded_and_read_only_can_view_studies(client: TestClient) -> None:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post(
        "/api/v1/auth/login",
        json={"email": "reader@example.com", "password": "correct-test-password"},
        headers={"X-CSRF-Token": csrf},
    )
    assert client.get("/api/v1/studies").status_code == 200
    assert client.post(
        "/api/v1/risks",
        json={"title": "Invalid score", "description": "Out of bounds", "probability": 5, "impact": 2},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 403


def test_mitigation_attachment_is_stored_and_downloaded_through_parent_link(client: TestClient, tmp_path, monkeypatch) -> None:
    from app.risks import routes as risk_routes

    monkeypatch.setattr(risk_routes.settings, "attachment_storage_path", str(tmp_path))
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    created = client.post("/api/v1/risks", json={
        "title": "Attachment test risk", "description": "Test attachment routing.", "probability": 1, "impact": 1,
    }, headers={"X-CSRF-Token": csrf})
    assert created.status_code == 201, created.text
    risk = created.json()
    mitigation_id = risk["mitigations"][0]["mitigation_id"]

    upload = client.post(
        f"/api/v1/risks/mitigations/{mitigation_id}/attachments",
        files={"file": ("evidence.pdf", b"%PDF-1.4 test", "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    assert upload.status_code == 200, upload.text
    attachment = upload.json()["attachments"][0]
    assert attachment["file_name"] == "evidence.pdf"
    download = client.get(f"/api/v1/risks/mitigations/{mitigation_id}/attachments/{attachment['id']}")
    assert download.status_code == 200
    assert download.content == b"%PDF-1.4 test"

    unsupported = client.post(
        f"/api/v1/risks/mitigations/{mitigation_id}/attachments",
        files={"file": ("payload.exe", b"not allowed", "application/octet-stream")},
        headers={"X-CSRF-Token": csrf},
    )
    assert unsupported.status_code == 415


def test_study_external_links_reject_non_http_schemes(client: TestClient) -> None:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    invalid = client.post("/api/v1/studies", json={
        "title": "Unsafe external link", "jira_jpd_url": "javascript:alert(1)",
    }, headers={"X-CSRF-Token": csrf})
    assert invalid.status_code == 422


def test_architecture_domain_reference_is_admin_configurable(client: TestClient) -> None:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    created = client.post("/api/v1/studies/domains", json={"name": "Data Platforms"}, headers={"X-CSRF-Token": csrf})
    assert created.status_code == 201
    edited = client.patch(f"/api/v1/studies/domains/{created.json()['id']}", json={"name": "Data & Platforms", "is_active": False}, headers={"X-CSRF-Token": csrf})
    assert edited.status_code == 200
    assert edited.json()["name"] == "Data & Platforms"
    assert edited.json()["is_active"] is False

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    client.post("/api/v1/auth/login", json={"email": "reader@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    denied = client.post("/api/v1/studies/domains", json={"name": "Unauthorized"}, headers={"X-CSRF-Token": csrf})
    assert denied.status_code == 403


def test_risk_reference_settings_drive_form_validation(client: TestClient) -> None:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    settings = client.get("/api/v1/risks/settings/references")
    assert settings.status_code == 200, settings.text
    assert len(settings.json()["families"]) == 8
    assert len(settings.json()["subfamilies"]) == 28
    assert {item["category"] for item in settings.json()["values"]} == {"object_type", "source_type", "scope_type"}

    object_type = next(item for item in settings.json()["values"] if item["category"] == "object_type" and item["code"] == "APPLICATION")
    renamed = client.patch(f"/api/v1/risks/settings/references/{object_type['id']}", json={"label_en": "Application system", "label_fr": "Application système"}, headers={"X-CSRF-Token": csrf})
    assert renamed.status_code == 200, renamed.text

    custom_scope = client.post("/api/v1/risks/settings/references", json={"category": "scope_type", "label_en": "Portfolio", "label_fr": "Portefeuille"}, headers={"X-CSRF-Token": csrf})
    assert custom_scope.status_code == 201, custom_scope.text
    created = client.post("/api/v1/risks", json={
        "title": "Configured reference risk", "description": "Uses settings values.", "probability": 2, "impact": 2,
        "objects": [{"object_type": "Application system", "object_ref": "ARDOQ-42"}],
        "sources": [{"source_type": "Project", "source_ref": "PRJ-42"}],
        "scopes": [{"scope_type": "Portfolio", "scope_ref": "Payments"}],
    }, headers={"X-CSRF-Token": csrf})
    assert created.status_code == 201, created.text
    assert created.json()["objects"][0]["object_type"] == "Application system"
    assert created.json()["scopes"][0]["scope_type"] == "Portfolio"

    invalid = client.post("/api/v1/risks", json={
        "title": "Unconfigured reference risk", "description": "Uses a value absent from settings.", "probability": 2, "impact": 2,
        "sources": [{"source_type": "Unconfigured source"}],
    }, headers={"X-CSRF-Token": csrf})
    assert invalid.status_code == 422


def test_adr_approval_requires_rationale_and_versions_accepted_edits(client: TestClient) -> None:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    created = client.post(
        "/api/v1/decisions",
        json={
            "title": "Select messaging platform",
            "context": "Several systems need reliable asynchronous integration.",
            "problem_statement": "Choose a supported messaging platform.",
            "options": [
                {"title": "Managed queue", "advantages": "Low operational effort"},
                {"title": "Self-managed broker", "advantages": "More deployment control"},
            ],
            "selected_option": "Managed queue",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201, created.text
    decision = created.json()
    assert decision["number"].startswith("ADR-")
    assert client.patch(
        f"/api/v1/decisions/{decision['id']}", json={"status": "Accepted"}, headers={"X-CSRF-Token": csrf, "If-Match": '"1"'}
    ).status_code == 409
    proposed = client.patch(
        f"/api/v1/decisions/{decision['id']}", json={"status": "Proposed"}, headers={"X-CSRF-Token": csrf, "If-Match": '"1"'}
    )
    assert proposed.status_code == 200, proposed.text
    review = client.patch(
        f"/api/v1/decisions/{decision['id']}", json={"status": "Under Review"}, headers={"X-CSRF-Token": csrf, "If-Match": '"2"'}
    )
    assert review.status_code == 200, review.text
    accepted = client.patch(
        f"/api/v1/decisions/{decision['id']}",
        json={"status": "Accepted", "decision_authority": "Architecture Review Board", "decision_date": "2026-10-06"},
        headers={"X-CSRF-Token": csrf, "If-Match": '"3"'},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["version"] == 2
    assert client.patch(
        f"/api/v1/decisions/{decision['id']}", json={"title": "Updated ADR title"}, headers={"X-CSRF-Token": csrf}
    ).status_code == 428
    edited = client.patch(
        f"/api/v1/decisions/{decision['id']}", json={"title": "Updated ADR title"}, headers={"X-CSRF-Token": csrf, "If-Match": '"4"'}
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["version"] == 3
    versions = client.get(f"/api/v1/decisions/{decision['id']}/versions").json()
    assert [item["version"] for item in versions] == [1, 2, 3]
    diff = client.get(f"/api/v1/decisions/{decision['id']}/compare?from_version=2&to_version=3").json()
    assert diff["changes"]["title"] == {"from": "Select messaging platform", "to": "Updated ADR title"}


def test_assistant_returns_no_source_and_conversations_are_user_scoped(client: TestClient) -> None:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    answer = client.post(
        "/api/v1/ai/ask", json={"question": "unknown foobar source"}, headers={"X-CSRF-Token": csrf}
    )
    assert answer.status_code == 200, answer.text
    result = answer.json()
    assert result["assistant_message"]["content"] == "No reliable source was found in the authorised knowledge base."
    assert result["assistant_message"]["sources"] == []
    conversation_id = result["conversation"]["id"]
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    client.post("/api/v1/auth/login", json={"email": "reader@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    assert client.get(f"/api/v1/ai/conversations/{conversation_id}").status_code == 404


def test_assistant_cites_permitted_records_and_never_retrieves_restricted_studies(client: TestClient, monkeypatch) -> None:
    from app.ai_assistant.provider import MistralProvider

    async def grounded_answer(self, question, sources, history=None):
        assert sources
        return "Verified information: the authorised risk describes a provider outage."

    monkeypatch.setattr(MistralProvider, "answer", grounded_answer)
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    restricted = client.post(
        "/api/v1/studies", json={"title": "Restricted Apollo migration", "confidentiality": "Restricted"}, headers={"X-CSRF-Token": csrf}
    ).json()
    public = client.post(
        "/api/v1/studies", json={"title": "Payments platform study", "confidentiality": "Internal"}, headers={"X-CSRF-Token": csrf}
    ).json()
    for title, study_id in (("Provider outage", public["id"]), ("Restricted vault access", restricted["id"])):
        client.post(
            "/api/v1/risks",
            json={"title": title, "description": f"{title} may interrupt payments services.", "probability": 3, "impact": 3, "study_id": study_id},
            headers={"X-CSRF-Token": csrf},
        )
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    client.post("/api/v1/auth/login", json={"email": "reader@example.com", "password": "correct-test-password"}, headers={"X-CSRF-Token": csrf})
    answer = client.post("/api/v1/ai/ask", json={"question": "provider outage payments"}, headers={"X-CSRF-Token": csrf})
    assert answer.status_code == 200, answer.text
    assistant = answer.json()["assistant_message"]
    assert any(source["source_type"] == "risk" for source in assistant["sources"])
    assert all("Restricted" not in source["title"] for source in assistant["sources"])
    assert "[R1]" in assistant["content"]

    no_answer = client.post("/api/v1/ai/ask", json={"question": "Apollo vault migration"}, headers={"X-CSRF-Token": csrf})
    assert no_answer.status_code == 200
    assert no_answer.json()["assistant_message"]["content"] == "No reliable source was found in the authorised knowledge base."