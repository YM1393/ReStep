"""EMR Integration service using HL7 FHIR R4.

Provides bidirectional data exchange between the local SQLite database and
external FHIR-compliant Electronic Medical Records systems.

All methods degrade gracefully: when FHIR is not configured, they return None
without raising exceptions.
"""

import os
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FHIR configuration from environment
# ---------------------------------------------------------------------------
FHIR_BASE_URL: Optional[str] = os.getenv("FHIR_BASE_URL")
FHIR_AUTH_TOKEN: Optional[str] = os.getenv("FHIR_AUTH_TOKEN")


class FHIRClient:
    """Thin wrapper around a FHIR R4 server."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_token: Optional[str] = None,
    ):
        self.base_url = (base_url or FHIR_BASE_URL or "").rstrip("/")
        self.auth_token = auth_token or FHIR_AUTH_TOKEN
        self._configured = bool(self.base_url)

    # -- helpers -------------------------------------------------------------

    def _headers(self) -> dict:
        h = {
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json",
        }
        if self.auth_token:
            h["Authorization"] = f"Bearer {self.auth_token}"
        return h

    def _request(self, method: str, path: str, **kwargs) -> Optional[dict]:
        """Make an HTTP request to the FHIR server.  Returns parsed JSON or
        None on any failure."""
        if not self._configured:
            return None
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            resp = requests.request(
                method, url, headers=self._headers(), timeout=15, **kwargs
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except Exception as exc:
            logger.warning("FHIR request %s %s failed: %s", method, url, exc)
            return None

    # -- status --------------------------------------------------------------

    def check_connection(self) -> dict:
        """Return FHIR server status.  Always returns a dict."""
        if not self._configured:
            return {"connected": False, "message": "FHIR server not configured"}
        try:
            resp = requests.get(
                f"{self.base_url}/metadata",
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                return {"connected": True, "message": "Connected to FHIR server"}
            return {
                "connected": False,
                "message": f"FHIR server returned status {resp.status_code}",
            }
        except Exception as exc:
            return {"connected": False, "message": str(exc)}

    # -- export --------------------------------------------------------------

    @staticmethod
    def _map_gender(local_gender: str) -> str:
        mapping = {"M": "male", "F": "female"}
        return mapping.get(local_gender, "unknown")

    def export_patient_to_fhir(self, patient: dict) -> Optional[dict]:
        """Convert a local patient dict to a FHIR Patient resource and POST it."""
        if not self._configured:
            return None

        name_parts = (patient.get("name") or "").split()
        given = name_parts[:-1] if len(name_parts) > 1 else name_parts
        family = name_parts[-1] if len(name_parts) > 1 else ""

        resource = {
            "resourceType": "Patient",
            "identifier": [
                {
                    "system": "urn:10mwt:patient-number",
                    "value": patient.get("patient_number", ""),
                }
            ],
            "name": [
                {
                    "use": "official",
                    "family": family,
                    "given": given,
                }
            ],
            "gender": self._map_gender(patient.get("gender", "")),
            "birthDate": patient.get("birth_date", ""),
        }

        if patient.get("diagnosis"):
            resource["extension"] = [
                {
                    "url": "urn:10mwt:diagnosis",
                    "valueString": patient["diagnosis"],
                }
            ]

        return self._request("POST", "Patient", json=resource)

    def export_test_to_fhir(self, test: dict, patient: dict) -> Optional[dict]:
        """Convert a local walk-test to a FHIR Observation and POST it."""
        if not self._configured:
            return None

        components = []

        if test.get("walk_speed_mps") is not None:
            components.append(
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "41909-3",
                                "display": "Walking speed",
                            }
                        ]
                    },
                    "valueQuantity": {
                        "value": test["walk_speed_mps"],
                        "unit": "m/s",
                        "system": "http://unitsofmeasure.org",
                        "code": "m/s",
                    },
                }
            )

        if test.get("walk_time_seconds") is not None:
            components.append(
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "54801-0",
                                "display": "Walking time",
                            }
                        ]
                    },
                    "valueQuantity": {
                        "value": test["walk_time_seconds"],
                        "unit": "s",
                        "system": "http://unitsofmeasure.org",
                        "code": "s",
                    },
                }
            )

        resource = {
            "resourceType": "Observation",
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "exam",
                            "display": "Exam",
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "41909-3",
                        "display": "10-Meter Walk Test",
                    }
                ]
            },
            "subject": {
                "reference": f"Patient/{patient.get('id', '')}",
                "display": patient.get("name", ""),
            },
            "effectiveDateTime": test.get("test_date", ""),
            "component": components,
        }

        if test.get("notes"):
            resource["note"] = [{"text": test["notes"]}]

        return self._request("POST", "Observation", json=resource)

    # -- import --------------------------------------------------------------

    @staticmethod
    def import_patient_from_fhir(fhir_patient: dict) -> Optional[dict]:
        """Convert a FHIR Patient resource dict to a local patient dict."""
        if not fhir_patient or fhir_patient.get("resourceType") != "Patient":
            return None

        # name
        name_entry = {}
        names = fhir_patient.get("name", [])
        if names:
            name_entry = names[0]
        given = " ".join(name_entry.get("given", []))
        family = name_entry.get("family", "")
        full_name = f"{given} {family}".strip() or "Unknown"

        # gender mapping
        gender_map = {"male": "M", "female": "F"}
        gender = gender_map.get(fhir_patient.get("gender", ""), "M")

        # identifier
        patient_number = ""
        for ident in fhir_patient.get("identifier", []):
            patient_number = ident.get("value", "")
            if patient_number:
                break

        # diagnosis from extension
        diagnosis = None
        for ext in fhir_patient.get("extension", []):
            if ext.get("url") == "urn:10mwt:diagnosis":
                diagnosis = ext.get("valueString")

        return {
            "patient_number": patient_number or f"FHIR-{fhir_patient.get('id', 'unknown')}",
            "name": full_name,
            "gender": gender,
            "birth_date": fhir_patient.get("birthDate", "1900-01-01"),
            "height_cm": 170.0,  # FHIR Patient doesn't carry height; use default
            "diagnosis": diagnosis,
        }

    # -- search --------------------------------------------------------------

    def search_fhir_patients(self, name: str) -> Optional[list]:
        """Search for patients on the FHIR server by name."""
        if not self._configured:
            return None

        result = self._request("GET", f"Patient?name={name}")
        if result is None:
            return None

        patients = []
        for entry in result.get("entry", []):
            resource = entry.get("resource", {})
            if resource.get("resourceType") == "Patient":
                patients.append(resource)
        return patients


# Singleton instance
fhir_client = FHIRClient()
