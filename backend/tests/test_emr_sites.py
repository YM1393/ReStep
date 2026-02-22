"""Tests for EMR integration and multi-site support."""

import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport


# ------------------------------------------------------------------
# EMR integration tests
# ------------------------------------------------------------------


class TestFHIRClient:
    """Unit tests for FHIRClient without a live FHIR server."""

    def test_unconfigured_client_returns_none(self):
        from app.services.emr_integration import FHIRClient

        client = FHIRClient(base_url="", auth_token="")
        assert client.export_patient_to_fhir({"name": "Test"}) is None
        assert client.export_test_to_fhir({}, {}) is None
        assert client.search_fhir_patients("Kim") is None

    def test_check_connection_unconfigured(self):
        from app.services.emr_integration import FHIRClient

        client = FHIRClient(base_url="", auth_token="")
        status = client.check_connection()
        assert status["connected"] is False
        assert "not configured" in status["message"]

    def test_import_patient_from_fhir_valid(self):
        from app.services.emr_integration import FHIRClient

        fhir_patient = {
            "resourceType": "Patient",
            "id": "123",
            "identifier": [{"system": "urn:test", "value": "PT-999"}],
            "name": [{"family": "Kim", "given": ["MinSu"]}],
            "gender": "male",
            "birthDate": "1985-03-15",
            "extension": [
                {
                    "url": "urn:10mwt:diagnosis",
                    "valueString": "Stroke",
                }
            ],
        }

        result = FHIRClient.import_patient_from_fhir(fhir_patient)
        assert result is not None
        assert result["patient_number"] == "PT-999"
        assert result["name"] == "MinSu Kim"
        assert result["gender"] == "M"
        assert result["birth_date"] == "1985-03-15"
        assert result["diagnosis"] == "Stroke"

    def test_import_patient_from_fhir_invalid(self):
        from app.services.emr_integration import FHIRClient

        assert FHIRClient.import_patient_from_fhir(None) is None
        assert FHIRClient.import_patient_from_fhir({}) is None
        assert FHIRClient.import_patient_from_fhir({"resourceType": "Observation"}) is None

    def test_import_patient_from_fhir_minimal(self):
        from app.services.emr_integration import FHIRClient

        fhir_patient = {
            "resourceType": "Patient",
            "id": "abc",
            "gender": "female",
        }
        result = FHIRClient.import_patient_from_fhir(fhir_patient)
        assert result is not None
        assert result["patient_number"] == "FHIR-abc"
        assert result["name"] == "Unknown"
        assert result["gender"] == "F"

    def test_gender_mapping(self):
        from app.services.emr_integration import FHIRClient

        assert FHIRClient._map_gender("M") == "male"
        assert FHIRClient._map_gender("F") == "female"
        assert FHIRClient._map_gender("X") == "unknown"

    @patch("app.services.emr_integration.requests.request")
    def test_export_patient_configured(self, mock_req):
        from app.services.emr_integration import FHIRClient

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.content = b'{"id":"fhir-1"}'
        mock_resp.json.return_value = {"id": "fhir-1"}
        mock_resp.raise_for_status = MagicMock()
        mock_req.return_value = mock_resp

        client = FHIRClient(base_url="http://fhir.example.com", auth_token="tok")
        result = client.export_patient_to_fhir(
            {
                "id": "local-1",
                "patient_number": "PT-001",
                "name": "Test Patient",
                "gender": "M",
                "birth_date": "1990-01-01",
            }
        )
        assert result is not None
        assert result["id"] == "fhir-1"
        mock_req.assert_called_once()

    @patch("app.services.emr_integration.requests.request")
    def test_export_test_configured(self, mock_req):
        from app.services.emr_integration import FHIRClient

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.content = b'{"id":"obs-1"}'
        mock_resp.json.return_value = {"id": "obs-1"}
        mock_resp.raise_for_status = MagicMock()
        mock_req.return_value = mock_resp

        client = FHIRClient(base_url="http://fhir.example.com", auth_token="tok")
        result = client.export_test_to_fhir(
            {
                "walk_speed_mps": 1.2,
                "walk_time_seconds": 8.3,
                "test_date": "2025-01-01",
                "notes": "Good walk",
            },
            {"id": "p-1", "name": "Kim"},
        )
        assert result is not None
        assert result["id"] == "obs-1"


# ------------------------------------------------------------------
# EMR API endpoint tests
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_emr_status_endpoint(async_client: AsyncClient, admin_headers):
    resp = await async_client.get("/api/emr/status", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "connected" in data
    # By default FHIR is not configured
    assert data["connected"] is False


@pytest.mark.anyio
async def test_emr_search_no_config(async_client: AsyncClient, admin_headers):
    resp = await async_client.get(
        "/api/emr/search?name=Kim", headers=admin_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["patients"] == []


@pytest.mark.anyio
async def test_emr_status_requires_login(async_client: AsyncClient):
    resp = await async_client.get("/api/emr/status")
    assert resp.status_code == 401


# ------------------------------------------------------------------
# Multi-site tests
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_and_list_sites(async_client: AsyncClient, admin_headers):
    # Create a site
    resp = await async_client.post(
        "/api/admin/sites",
        json={"name": "Seoul Branch", "address": "123 Gangnam"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    site = resp.json()
    assert site["name"] == "Seoul Branch"
    assert site["address"] == "123 Gangnam"
    site_id = site["id"]

    # List sites
    resp = await async_client.get("/api/admin/sites", headers=admin_headers)
    assert resp.status_code == 200
    sites = resp.json()
    assert len(sites) >= 1
    assert any(s["id"] == site_id for s in sites)


@pytest.mark.anyio
async def test_update_site(async_client: AsyncClient, admin_headers):
    # Create
    resp = await async_client.post(
        "/api/admin/sites",
        json={"name": "Busan Branch"},
        headers=admin_headers,
    )
    site_id = resp.json()["id"]

    # Update
    resp = await async_client.put(
        f"/api/admin/sites/{site_id}",
        json={"name": "Busan Main Branch", "phone": "051-1234"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["name"] == "Busan Main Branch"
    assert updated["phone"] == "051-1234"


@pytest.mark.anyio
async def test_site_stats(async_client: AsyncClient, admin_headers):
    # Create site
    resp = await async_client.post(
        "/api/admin/sites",
        json={"name": "Test Site"},
        headers=admin_headers,
    )
    site_id = resp.json()["id"]

    # Get stats (empty site)
    resp = await async_client.get(
        f"/api/admin/sites/{site_id}/stats", headers=admin_headers
    )
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_patients"] == 0
    assert stats["total_tests"] == 0
    assert stats["site_name"] == "Test Site"


@pytest.mark.anyio
async def test_site_not_found(async_client: AsyncClient, admin_headers):
    resp = await async_client.get(
        "/api/admin/sites/nonexistent/stats", headers=admin_headers
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_sites_require_admin(async_client: AsyncClient, approved_therapist_headers):
    resp = await async_client.get(
        "/api/admin/sites", headers=approved_therapist_headers
    )
    assert resp.status_code == 403


# ------------------------------------------------------------------
# Database migration test: site_id columns exist
# ------------------------------------------------------------------


def test_site_id_columns_exist(db):
    """Verify that the site_id migration ran on users, patients, walk_tests."""
    from app.models.database import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()

    for table in ("users", "patients", "walk_tests"):
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [col[1] for col in cursor.fetchall()]
        assert "site_id" in cols, f"site_id missing from {table}"

    conn.close()


def test_sites_table_exists(db):
    """Verify the sites table was created."""
    from app.models.database import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='sites'"
    )
    assert cursor.fetchone() is not None
    conn.close()
