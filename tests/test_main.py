"""
pytest test suite for Student Management System
Run with: pytest tests -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

if os.path.exists("test.db"):
    os.remove("test.db")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

test_engine = create_engine(
    SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

from database import Base, get_db
from main import app

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create all tables in the test DB
Base.metadata.create_all(bind=test_engine)

client = TestClient(app)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def admin_token():
    """Register an admin user and return a valid JWT token."""
    client.post("/auth/register", json={
        "username": "test_admin",
        "password": "adminpass",
        "role": "admin"
    })
    resp = client.post("/auth/login", data={
        "username": "test_admin",
        "password": "adminpass"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def student_token():
    """Register a student user and return a valid JWT token."""
    client.post("/auth/register", json={
        "username": "test_student",
        "password": "studentpass",
        "role": "student"
    })
    resp = client.post("/auth/login", data={
        "username": "test_student",
        "password": "studentpass"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def created_student_id(admin_token):
    """Create a student via the API and return its ID."""
    # First get the student user's id
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Register student user to link
    reg = client.post("/auth/register", json={
        "username": "linked_student",
        "password": "linked123",
        "role": "student"
    })
    user_id = reg.json().get("id")

    resp = client.post("/students/", json={
        "name": "Alice",
        "department": "CS",
        "gpa": 3.8,
        "email": "alice@test.com",
        "user_id": user_id
    }, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


# ── Authentication Tests ──────────────────────────────────────────────────────

class TestAuth:

    def test_register_success(self):
        resp = client.post("/auth/register", json={
            "username": "newuser_unique",
            "password": "securepass",
            "role": "student"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser_unique"
        assert data["role"] == "student"
        assert "id" in data

    def test_register_duplicate_username(self):
        client.post("/auth/register", json={
            "username": "dup_user",
            "password": "pass1234",
            "role": "student"
        })
        resp = client.post("/auth/register", json={
            "username": "dup_user",
            "password": "pass1234",
            "role": "student"
        })
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]

    def test_register_password_too_short(self):
        resp = client.post("/auth/register", json={
            "username": "shortpass_user",
            "password": "123",
            "role": "student"
        })
        assert resp.status_code == 422  # Pydantic validation error

    def test_login_success(self):
        client.post("/auth/register", json={
            "username": "login_user",
            "password": "loginpass",
            "role": "student"
        })
        resp = client.post("/auth/login", data={
            "username": "login_user",
            "password": "loginpass"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self):
        resp = client.post("/auth/login", data={
            "username": "login_user",
            "password": "wrongpass"
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self):
        resp = client.post("/auth/login", data={
            "username": "ghost_user",
            "password": "ghostpass"
        })
        assert resp.status_code == 401


# ── Protected Endpoint Tests ──────────────────────────────────────────────────

class TestProtectedEndpoints:

    def test_get_students_without_token(self):
        resp = client.get("/students/")
        assert resp.status_code == 401

    def test_get_students_with_student_token_forbidden(self, student_token):
        headers = {"Authorization": f"Bearer {student_token}"}
        resp = client.get("/students/", headers=headers)
        assert resp.status_code == 403

    def test_get_students_with_admin_token(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = client.get("/students/", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_invalid_token_rejected(self):
        headers = {"Authorization": "Bearer fake.token.here"}
        resp = client.get("/students/", headers=headers)
        assert resp.status_code == 401

    def test_audit_logs_admin_only(self, admin_token, student_token):
        # Admin can access
        resp = client.get("/monitoring/audit-logs",
                          headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200

        # Student cannot access
        resp = client.get("/monitoring/audit-logs",
                          headers={"Authorization": f"Bearer {student_token}"})
        assert resp.status_code == 403


# ── Student CRUD Tests ────────────────────────────────────────────────────────

class TestStudentCRUD:

    def test_create_student_as_admin(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = client.post("/students/", json={
            "name": "Bob",
            "department": "Math",
            "gpa": 3.2,
            "email": "bob@test.com",
            "user_id": None
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Bob"
        assert data["department"] == "Math"

    def test_create_student_duplicate_email(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        client.post("/students/", json={
            "name": "Charlie",
            "department": "Physics",
            "gpa": 3.0,
            "email": "unique_charlie@test.com",
            "user_id": None
        }, headers=headers)
        resp = client.post("/students/", json={
            "name": "Charlie2",
            "department": "Physics",
            "gpa": 3.0,
            "email": "unique_charlie@test.com",
            "user_id": None
        }, headers=headers)
        assert resp.status_code == 400

    def test_get_student_by_id_as_admin(self, admin_token, created_student_id):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = client.get(f"/students/{created_student_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == created_student_id

    def test_get_nonexistent_student(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = client.get("/students/99999", headers=headers)
        assert resp.status_code == 404

    def test_update_student_as_admin(self, admin_token, created_student_id):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = client.put(f"/students/{created_student_id}",
                          json={"name": "Alice Updated", "gpa": 3.9},
                          headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Alice Updated"
        assert resp.json()["gpa"] == 3.9

    def test_delete_student_as_admin(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Create a student to delete
        resp = client.post("/students/", json={
            "name": "To Delete",
            "department": "Law",
            "gpa": 2.5,
            "email": "todelete@test.com",
            "user_id": None
        }, headers=headers)
        sid = resp.json()["id"]

        del_resp = client.delete(f"/students/{sid}", headers=headers)
        assert del_resp.status_code == 204

        # Confirm gone
        get_resp = client.get(f"/students/{sid}", headers=headers)
        assert get_resp.status_code == 404

    def test_delete_student_as_student_forbidden(self, student_token, created_student_id):
        headers = {"Authorization": f"Bearer {student_token}"}
        resp = client.delete(f"/students/{created_student_id}", headers=headers)
        assert resp.status_code == 403


# ── Filtering & Pagination Tests ──────────────────────────────────────────────

class TestFiltering:

    def test_filter_by_department(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = client.get("/students/?department=CS", headers=headers)
        assert resp.status_code == 200
        for s in resp.json():
            assert s["department"] == "CS"

    def test_filter_by_gpa_range(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = client.get("/students/?gpa_min=3.0&gpa_max=4.0", headers=headers)
        assert resp.status_code == 200
        for s in resp.json():
            assert 3.0 <= s["gpa"] <= 4.0

    def test_pagination(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = client.get("/students/?skip=0&limit=2", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) <= 2


# ── Business Logic Tests ──────────────────────────────────────────────────────

class TestBusinessLogic:

    def test_student_cannot_view_other_profile(self, student_token, created_student_id):
        """A student should not be able to view another student's profile."""
        headers = {"Authorization": f"Bearer {student_token}"}
        resp = client.get(f"/students/{created_student_id}", headers=headers)
        # test_student is not linked to created_student_id → 403
        assert resp.status_code == 403

    def test_audit_log_created_on_update(self, admin_token, created_student_id):
        """An audit log entry should exist after updating a student."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        client.put(f"/students/{created_student_id}",
                   json={"gpa": 3.5},
                   headers=headers)
        logs_resp = client.get("/monitoring/audit-logs", headers=headers)
        assert logs_resp.status_code == 200
        logs = logs_resp.json()
        matching = [l for l in logs if l["student_id"] == created_student_id]
        assert len(matching) >= 1
