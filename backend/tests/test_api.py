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
            "users.read", "users.write", "audit.read", "studies.read", "studies.write", "risks.read", "risks.write",
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


def test_study_and_risk_workflow_persists_backend_scores(client: TestClient) -> None:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "correct-test-password"},
        headers={"X-CSRF-Token": csrf},
    )
    study_response = client.post(
        "/api/v1/studies",
        json={"title": "Cloud transition", "architecture_domain": "Infrastructure"},
        headers={"X-CSRF-Token": csrf},
    )
    assert study_response.status_code == 201, study_response.text
    study = study_response.json()
    assert study["identifier"].startswith("STU-")
    update = client.patch(
        f"/api/v1/studies/{study['id']}",
        json={"status": "In Progress", "target_review_date": "2026-11-15"},
        headers={"X-CSRF-Token": csrf},
    )
    assert update.status_code == 200, update.text
    assert update.json()["row_version"] == 2
    risk_response = client.post(
        "/api/v1/risks",
        json={"title": "Provider outage", "description": "A cloud provider outage may interrupt critical services.", "probability": 4, "impact": 3, "residual_probability": 2, "residual_impact": 3, "study_id": study["id"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert risk_response.status_code == 201, risk_response.text
    risk = risk_response.json()
    assert risk["inherent_score"] == 12
    assert risk["criticality"] == "Critical"
    assert risk["residual_score"] == 6
    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["studies"] == 1
    assert dashboard["open_risks"] == 1
    assert dashboard["critical_risks"] == 1
    assert client.patch(f"/api/v1/risks/{risk['id']}", json={"status": "Accepted"}, headers={"X-CSRF-Token": csrf}).status_code == 409
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