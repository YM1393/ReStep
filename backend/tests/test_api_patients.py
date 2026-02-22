"""Tests for patients API endpoints."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.database import db


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


THERAPIST_HEADERS = {
    "X-User-Id": "fake-therapist-id",
    "X-User-Role": "therapist",
    "X-User-Approved": "true",
}

ADMIN_HEADERS = {
    "X-User-Id": "fake-admin-id",
    "X-User-Role": "admin",
}

PATIENT_PAYLOAD = {
    "patient_number": "PT-100",
    "name": "API Patient",
    "gender": "M",
    "birth_date": "1985-06-20",
    "height_cm": 170.0,
    "diagnosis": "Stroke",
}


@pytest.mark.asyncio
class TestCreatePatient:
    async def test_create_patient_success(self, client):
        resp = await client.post(
            "/api/patients/",
            json=PATIENT_PAYLOAD,
            headers=THERAPIST_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "API Patient"
        assert data["patient_number"] == "PT-100"

    async def test_create_patient_duplicate_number(self, client):
        await client.post(
            "/api/patients/",
            json=PATIENT_PAYLOAD,
            headers=THERAPIST_HEADERS,
        )
        resp = await client.post(
            "/api/patients/",
            json=PATIENT_PAYLOAD,
            headers=THERAPIST_HEADERS,
        )
        assert resp.status_code == 400

    async def test_create_patient_no_auth(self, client):
        resp = await client.post("/api/patients/", json=PATIENT_PAYLOAD)
        assert resp.status_code == 401

    async def test_create_patient_admin_forbidden(self, client):
        resp = await client.post(
            "/api/patients/",
            json=PATIENT_PAYLOAD,
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 403

    async def test_create_patient_unapproved_therapist(self, client):
        headers = {**THERAPIST_HEADERS, "X-User-Approved": "false"}
        resp = await client.post(
            "/api/patients/",
            json=PATIENT_PAYLOAD,
            headers=headers,
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestGetPatients:
    async def test_get_patients_empty(self, client):
        resp = await client.get("/api/patients/")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_patients_with_data(self, client):
        await client.post(
            "/api/patients/",
            json=PATIENT_PAYLOAD,
            headers=THERAPIST_HEADERS,
        )
        resp = await client.get("/api/patients/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_search_patients(self, client):
        await client.post(
            "/api/patients/",
            json=PATIENT_PAYLOAD,
            headers=THERAPIST_HEADERS,
        )
        resp = await client.get("/api/patients/search", params={"q": "API"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_search_patients_no_match(self, client):
        resp = await client.get("/api/patients/search", params={"q": "ZZZZZ"})
        assert resp.status_code == 200
        assert len(resp.json()) == 0


@pytest.mark.asyncio
class TestGetPatientById:
    async def test_get_patient_success(self, client):
        create_resp = await client.post(
            "/api/patients/",
            json=PATIENT_PAYLOAD,
            headers=THERAPIST_HEADERS,
        )
        patient_id = create_resp.json()["id"]
        resp = await client.get(f"/api/patients/{patient_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "API Patient"

    async def test_get_patient_not_found(self, client):
        resp = await client.get("/api/patients/nonexistent-id")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestUpdatePatient:
    async def test_update_patient_success(self, client):
        create_resp = await client.post(
            "/api/patients/",
            json=PATIENT_PAYLOAD,
            headers=THERAPIST_HEADERS,
        )
        patient_id = create_resp.json()["id"]
        resp = await client.put(
            f"/api/patients/{patient_id}",
            json={"name": "Updated Name"},
            headers=THERAPIST_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    async def test_update_patient_not_found(self, client):
        resp = await client.put(
            "/api/patients/nonexistent-id",
            json={"name": "X"},
            headers=THERAPIST_HEADERS,
        )
        assert resp.status_code == 404

    async def test_update_patient_empty_body(self, client):
        create_resp = await client.post(
            "/api/patients/",
            json=PATIENT_PAYLOAD,
            headers=THERAPIST_HEADERS,
        )
        patient_id = create_resp.json()["id"]
        resp = await client.put(
            f"/api/patients/{patient_id}",
            json={},
            headers=THERAPIST_HEADERS,
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestDeletePatient:
    async def test_delete_patient_success(self, client):
        create_resp = await client.post(
            "/api/patients/",
            json=PATIENT_PAYLOAD,
            headers=THERAPIST_HEADERS,
        )
        patient_id = create_resp.json()["id"]
        resp = await client.delete(
            f"/api/patients/{patient_id}",
            headers=THERAPIST_HEADERS,
        )
        assert resp.status_code == 200

    async def test_delete_patient_not_found(self, client):
        resp = await client.delete(
            "/api/patients/nonexistent-id",
            headers=THERAPIST_HEADERS,
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestPatientTags:
    async def test_create_and_list_tags(self, client):
        resp = await client.post("/api/patients/tags", json={"name": "Stroke", "color": "#FF0000"})
        assert resp.status_code == 200
        resp = await client.get("/api/patients/tags/all")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_assign_tag_to_patient(self, client):
        # Create patient
        create_resp = await client.post(
            "/api/patients/",
            json=PATIENT_PAYLOAD,
            headers=THERAPIST_HEADERS,
        )
        patient_id = create_resp.json()["id"]
        # Create tag
        tag_resp = await client.post("/api/patients/tags", json={"name": "Stroke"})
        tag_id = tag_resp.json()["id"]
        # Assign
        resp = await client.post(f"/api/patients/{patient_id}/tags/{tag_id}")
        assert resp.status_code == 200
        # Verify
        resp = await client.get(f"/api/patients/{patient_id}/tags")
        assert len(resp.json()) == 1

    async def test_remove_tag_from_patient(self, client):
        create_resp = await client.post(
            "/api/patients/",
            json=PATIENT_PAYLOAD,
            headers=THERAPIST_HEADERS,
        )
        patient_id = create_resp.json()["id"]
        tag_resp = await client.post("/api/patients/tags", json={"name": "Stroke"})
        tag_id = tag_resp.json()["id"]
        await client.post(f"/api/patients/{patient_id}/tags/{tag_id}")
        resp = await client.delete(f"/api/patients/{patient_id}/tags/{tag_id}")
        assert resp.status_code == 200
        resp = await client.get(f"/api/patients/{patient_id}/tags")
        assert len(resp.json()) == 0


@pytest.mark.asyncio
class TestHealthAndRoot:
    async def test_root(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.json()["version"] == "1.0.0"

    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
