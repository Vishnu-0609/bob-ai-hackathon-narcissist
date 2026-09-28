import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.seed import seed_database

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_database(db)
    db.close()


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"


def test_auth_login_and_me():
    # Login as coordinator
    login_res = client.post("/api/auth/login", json={"username": "coordinator", "password": "coordpassword123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    assert token is not None

    # Call /api/auth/me
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "coordinator"


def test_unauthorized_access():
    # Without token -> 401
    res = client.get("/api/incidents")
    assert res.status_code == 401


def test_top_candidates_pm017():
    login_res = client.post("/api/auth/login", json={"username": "coordinator", "password": "coordpassword123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/matching/PM-017/candidates?limit=3", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["pm_body_number"] == "PM-017"
    assert len(data["candidates"]) == 3
    # First candidate should be AM-042
    assert data["candidates"][0]["am_case_number"] == "AM-042"
    assert data["candidates"][0]["match_score"] >= 80.0
    assert data["candidates"][0]["bob_rationale"] is not None


def test_audit_verify_api():
    login_res = client.post("/api/auth/login", json={"username": "auditor", "password": "auditpassword123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/audit/verify", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["events_checked"] >= 1
