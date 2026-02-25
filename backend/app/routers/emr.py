"""EMR (HL7 FHIR) integration endpoints."""

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional

from app.models.db_factory import db
from app.services.emr_integration import fhir_client, FHIRClient

router = APIRouter()


def _verify_login(user_id: str = Header(None, alias="X-User-Id")):
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class FHIRImportRequest(BaseModel):
    fhir_url: Optional[str] = None
    patient_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
async def emr_status(user_id: str = Header(None, alias="X-User-Id")):
    """Check FHIR server connection status."""
    _verify_login(user_id)
    return fhir_client.check_connection()


@router.get("/search")
async def emr_search(
    name: str = Query(..., min_length=1),
    user_id: str = Header(None, alias="X-User-Id"),
):
    """Search FHIR server for patients by name."""
    _verify_login(user_id)
    results = fhir_client.search_fhir_patients(name)
    if results is None:
        return {"patients": [], "message": "FHIR server not configured"}
    return {"patients": results}


@router.post("/patients/{patient_id}/export")
async def emr_export_patient(
    patient_id: str,
    user_id: str = Header(None, alias="X-User-Id"),
):
    """Export a patient and their tests to the FHIR server."""
    _verify_login(user_id)

    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_result = fhir_client.export_patient_to_fhir(patient)
    if patient_result is None:
        raise HTTPException(
            status_code=503,
            detail="FHIR server not configured or unreachable",
        )

    # Export all tests for this patient
    tests = db.get_patient_tests(patient_id)
    exported_tests = 0
    for test in tests:
        obs = fhir_client.export_test_to_fhir(test, patient)
        if obs is not None:
            exported_tests += 1

    return {
        "message": "Patient exported to FHIR server",
        "patient_fhir_id": patient_result.get("id"),
        "tests_exported": exported_tests,
    }


@router.post("/import")
async def emr_import_patient(
    body: FHIRImportRequest,
    user_id: str = Header(None, alias="X-User-Id"),
):
    """Import a patient from a FHIR server."""
    _verify_login(user_id)

    # If a custom FHIR URL is provided, create a temporary client
    client = fhir_client
    if body.fhir_url:
        client = FHIRClient(base_url=body.fhir_url)

    fhir_patient = client._request("GET", f"Patient/{body.patient_id}")
    if fhir_patient is None:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve patient from FHIR server",
        )

    local_data = FHIRClient.import_patient_from_fhir(fhir_patient)
    if local_data is None:
        raise HTTPException(
            status_code=400, detail="Invalid FHIR Patient resource"
        )

    # Check if patient already exists by patient_number
    existing = db.search_patients(local_data["patient_number"])
    for p in existing:
        if p["patient_number"] == local_data["patient_number"]:
            return {
                "message": "Patient already exists locally",
                "patient": p,
                "imported": False,
            }

    patient = db.create_patient(local_data)
    return {
        "message": "Patient imported from FHIR server",
        "patient": patient,
        "imported": True,
    }
