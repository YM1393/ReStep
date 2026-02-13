"""
Test fixtures for the 10MWT backend test suite.
"""
import os
import sys
import pytest

# Disable rate limiting during tests
os.environ["TESTING"] = "true"

# Ensure the backend directory is on sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Override DB_PATH BEFORE importing any app modules so that init_db()
# and all subsequent imports use a separate test database.
import app.models.database as _db_mod

_TEST_DB_PATH = os.path.join(BACKEND_DIR, "test_database.db")
_db_mod.DB_PATH = _TEST_DB_PATH


def _reset_test_db():
    """Drop and recreate all tables in the test database."""
    if os.path.exists(_TEST_DB_PATH):
        os.remove(_TEST_DB_PATH)
    _db_mod.init_db()


# Reset the DB once at import time so the tables exist for the app import.
_reset_test_db()

from httpx import AsyncClient, ASGITransport  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    """Reset the test database before each test."""
    _reset_test_db()
    yield
    if os.path.exists(_TEST_DB_PATH):
        os.remove(_TEST_DB_PATH)


@pytest.fixture
def db():
    """Return the SimpleDB helper bound to the test database."""
    from app.models.database import db
    return db


@pytest.fixture
def test_patient_data():
    return {
        "patient_number": "PT-001",
        "name": "Test Patient",
        "gender": "M",
        "birth_date": "1990-01-15",
        "height_cm": 175.0,
        "diagnosis": "Stroke",
    }


@pytest.fixture
def test_user_data():
    return {
        "username": "testtherapist",
        "password": "testpass123",
        "name": "Test Therapist",
        "role": "therapist",
        "is_approved": 0,
    }


@pytest.fixture
def approved_therapist_headers():
    """Headers that simulate an approved therapist."""
    return {
        "X-User-Id": "fake-therapist-id",
        "X-User-Role": "therapist",
        "X-User-Approved": "true",
    }


@pytest.fixture
def admin_headers():
    """Headers that simulate an admin user."""
    return {
        "X-User-Id": "fake-admin-id",
        "X-User-Role": "admin",
    }


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
