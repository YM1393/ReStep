"""Tests for database CRUD operations via SimpleDB."""
import pytest
from app.models.database import db, verify_password


class TestUserCRUD:
    def test_create_user(self, test_user_data):
        user = db.create_user(test_user_data)
        assert user["username"] == "testtherapist"
        assert user["name"] == "Test Therapist"
        assert user["role"] == "therapist"
        assert user["is_approved"] == 0
        assert "password_hash" not in user
        assert "id" in user

    def test_get_user_by_username(self, test_user_data):
        db.create_user(test_user_data)
        user = db.get_user_by_username("testtherapist")
        assert user is not None
        assert user["username"] == "testtherapist"
        assert "password_hash" in user

    def test_get_user_by_username_not_found(self):
        assert db.get_user_by_username("nonexistent") is None

    def test_get_user_by_id(self, test_user_data):
        created = db.create_user(test_user_data)
        user = db.get_user(created["id"])
        assert user is not None
        assert user["username"] == "testtherapist"
        assert "password_hash" not in user

    def test_get_user_by_id_not_found(self):
        assert db.get_user("nonexistent-id") is None

    def test_approve_therapist(self, test_user_data):
        created = db.create_user(test_user_data)
        approved = db.approve_therapist(created["id"])
        assert approved is not None
        assert approved["is_approved"] == 1

    def test_approve_nonexistent_therapist(self):
        assert db.approve_therapist("nonexistent-id") is None

    def test_delete_user(self, test_user_data):
        created = db.create_user(test_user_data)
        assert db.delete_user(created["id"]) is True
        assert db.get_user_by_username("testtherapist") is None

    def test_delete_nonexistent_user(self):
        assert db.delete_user("nonexistent-id") is False

    def test_get_pending_therapists(self, test_user_data):
        db.create_user(test_user_data)
        pending = db.get_pending_therapists()
        assert len(pending) == 1
        assert pending[0]["username"] == "testtherapist"

    def test_get_all_therapists(self, test_user_data):
        db.create_user(test_user_data)
        therapists = db.get_all_therapists()
        assert len(therapists) == 1

    def test_default_admin_exists(self):
        admin = db.get_user_by_username("admin")
        assert admin is not None
        assert admin["role"] == "admin"


class TestPasswordHashing:
    def test_verify_correct_password(self, test_user_data):
        db.create_user(test_user_data)
        user = db.get_user_by_username("testtherapist")
        assert verify_password("testpass123", user["password_hash"]) is True

    def test_verify_wrong_password(self, test_user_data):
        db.create_user(test_user_data)
        user = db.get_user_by_username("testtherapist")
        assert verify_password("wrongpassword", user["password_hash"]) is False


class TestPatientCRUD:
    def test_create_patient(self, test_patient_data):
        patient = db.create_patient(test_patient_data)
        assert patient["name"] == "Test Patient"
        assert patient["patient_number"] == "PT-001"
        assert patient["gender"] == "M"
        assert patient["height_cm"] == 175.0
        assert "id" in patient

    def test_get_patients(self, test_patient_data):
        db.create_patient(test_patient_data)
        patients = db.get_patients()
        assert len(patients) == 1

    def test_get_patient_by_id(self, test_patient_data):
        created = db.create_patient(test_patient_data)
        patient = db.get_patient(created["id"])
        assert patient is not None
        assert patient["name"] == "Test Patient"

    def test_get_patient_not_found(self):
        assert db.get_patient("nonexistent-id") is None

    def test_search_patients_by_name(self, test_patient_data):
        db.create_patient(test_patient_data)
        results = db.search_patients("Test")
        assert len(results) == 1

    def test_search_patients_by_number(self, test_patient_data):
        db.create_patient(test_patient_data)
        results = db.search_patients("PT-001")
        assert len(results) == 1

    def test_search_patients_no_match(self, test_patient_data):
        db.create_patient(test_patient_data)
        results = db.search_patients("ZZZZZ")
        assert len(results) == 0

    def test_update_patient(self, test_patient_data):
        created = db.create_patient(test_patient_data)
        updated = db.update_patient(created["id"], {"name": "Updated Name"})
        assert updated is not None
        assert updated["name"] == "Updated Name"

    def test_update_nonexistent_patient(self):
        assert db.update_patient("nonexistent-id", {"name": "X"}) is None

    def test_delete_patient(self, test_patient_data):
        created = db.create_patient(test_patient_data)
        assert db.delete_patient(created["id"]) is True
        assert db.get_patient(created["id"]) is None

    def test_delete_nonexistent_patient(self):
        assert db.delete_patient("nonexistent-id") is False


class TestWalkTestCRUD:
    def _create_patient_and_test(self, test_patient_data):
        patient = db.create_patient(test_patient_data)
        test_data = {
            "patient_id": patient["id"],
            "walk_time_seconds": 8.5,
            "walk_speed_mps": 1.18,
            "test_type": "10MWT",
        }
        test = db.create_test(test_data)
        return patient, test

    def test_create_test(self, test_patient_data):
        patient, test = self._create_patient_and_test(test_patient_data)
        assert test["patient_id"] == patient["id"]
        assert test["walk_time_seconds"] == 8.5
        assert test["walk_speed_mps"] == 1.18

    def test_get_patient_tests(self, test_patient_data):
        patient, _ = self._create_patient_and_test(test_patient_data)
        tests = db.get_patient_tests(patient["id"])
        assert len(tests) == 1

    def test_get_patient_tests_by_type(self, test_patient_data):
        patient = db.create_patient(test_patient_data)
        db.create_test({
            "patient_id": patient["id"],
            "walk_time_seconds": 8.5,
            "walk_speed_mps": 1.18,
            "test_type": "10MWT",
        })
        db.create_test({
            "patient_id": patient["id"],
            "walk_time_seconds": 12.0,
            "walk_speed_mps": 0.83,
            "test_type": "TUG",
        })
        assert len(db.get_patient_tests(patient["id"], test_type="10MWT")) == 1
        assert len(db.get_patient_tests(patient["id"], test_type="TUG")) == 1
        assert len(db.get_patient_tests(patient["id"])) == 2

    def test_get_test_by_id(self, test_patient_data):
        _, test = self._create_patient_and_test(test_patient_data)
        result = db.get_test(test["id"])
        assert result is not None
        assert result["walk_time_seconds"] == 8.5

    def test_get_test_not_found(self):
        assert db.get_test("nonexistent-id") is None

    def test_update_test_date(self, test_patient_data):
        _, test = self._create_patient_and_test(test_patient_data)
        updated = db.update_test_date(test["id"], "2025-01-01T10:00:00")
        assert updated is not None
        assert updated["test_date"] == "2025-01-01T10:00:00"

    def test_update_test_notes(self, test_patient_data):
        _, test = self._create_patient_and_test(test_patient_data)
        updated = db.update_test_notes(test["id"], "Patient used walker")
        assert updated is not None
        assert updated["notes"] == "Patient used walker"

    def test_delete_test(self, test_patient_data):
        _, test = self._create_patient_and_test(test_patient_data)
        assert db.delete_test(test["id"]) is True
        assert db.get_test(test["id"]) is None

    def test_delete_nonexistent_test(self):
        assert db.delete_test("nonexistent-id") is False


class TestTagCRUD:
    def test_create_tag(self):
        tag = db.create_tag("Stroke", "#FF0000")
        assert tag["name"] == "Stroke"
        assert tag["color"] == "#FF0000"

    def test_get_all_tags(self):
        db.create_tag("Stroke")
        db.create_tag("Parkinson")
        tags = db.get_all_tags()
        assert len(tags) == 2

    def test_delete_tag(self):
        tag = db.create_tag("Stroke")
        assert db.delete_tag(tag["id"]) is True
        assert len(db.get_all_tags()) == 0

    def test_add_patient_tag(self, test_patient_data):
        patient = db.create_patient(test_patient_data)
        tag = db.create_tag("Stroke")
        assert db.add_patient_tag(patient["id"], tag["id"]) is True

    def test_get_patient_tags(self, test_patient_data):
        patient = db.create_patient(test_patient_data)
        tag = db.create_tag("Stroke")
        db.add_patient_tag(patient["id"], tag["id"])
        tags = db.get_patient_tags(patient["id"])
        assert len(tags) == 1
        assert tags[0]["name"] == "Stroke"

    def test_remove_patient_tag(self, test_patient_data):
        patient = db.create_patient(test_patient_data)
        tag = db.create_tag("Stroke")
        db.add_patient_tag(patient["id"], tag["id"])
        assert db.remove_patient_tag(patient["id"], tag["id"]) is True
        assert len(db.get_patient_tags(patient["id"])) == 0

    def test_get_patients_by_tag(self, test_patient_data):
        patient = db.create_patient(test_patient_data)
        tag = db.create_tag("Stroke")
        db.add_patient_tag(patient["id"], tag["id"])
        patients = db.get_patients_by_tag(tag["id"])
        assert len(patients) == 1


class TestGoalCRUD:
    def test_create_goal(self, test_patient_data):
        patient = db.create_patient(test_patient_data)
        goal = db.create_goal({
            "patient_id": patient["id"],
            "test_type": "10MWT",
            "target_speed_mps": 1.2,
            "target_date": "2025-12-31",
        })
        assert goal["patient_id"] == patient["id"]
        assert goal["target_speed_mps"] == 1.2
        assert goal["status"] == "active"

    def test_get_patient_goals(self, test_patient_data):
        patient = db.create_patient(test_patient_data)
        db.create_goal({
            "patient_id": patient["id"],
            "target_speed_mps": 1.2,
        })
        goals = db.get_patient_goals(patient["id"])
        assert len(goals) == 1

    def test_get_patient_goals_by_status(self, test_patient_data):
        patient = db.create_patient(test_patient_data)
        db.create_goal({
            "patient_id": patient["id"],
            "target_speed_mps": 1.2,
        })
        assert len(db.get_patient_goals(patient["id"], status="active")) == 1
        assert len(db.get_patient_goals(patient["id"], status="achieved")) == 0

    def test_update_goal(self, test_patient_data):
        patient = db.create_patient(test_patient_data)
        goal = db.create_goal({
            "patient_id": patient["id"],
            "target_speed_mps": 1.2,
        })
        updated = db.update_goal(goal["id"], {"status": "achieved"})
        assert updated["status"] == "achieved"

    def test_delete_goal(self, test_patient_data):
        patient = db.create_patient(test_patient_data)
        goal = db.create_goal({
            "patient_id": patient["id"],
            "target_speed_mps": 1.2,
        })
        assert db.delete_goal(goal["id"]) is True
        assert db.get_goal(goal["id"]) is None


class TestAdminStats:
    def test_get_all_tests_count(self, test_patient_data):
        patient = db.create_patient(test_patient_data)
        db.create_test({
            "patient_id": patient["id"],
            "walk_time_seconds": 8.5,
            "walk_speed_mps": 1.18,
        })
        assert db.get_all_tests_count() == 1

    def test_get_tests_by_period(self, test_patient_data):
        patient = db.create_patient(test_patient_data)
        db.create_test({
            "patient_id": patient["id"],
            "walk_time_seconds": 8.5,
            "walk_speed_mps": 1.18,
        })
        periods = db.get_tests_by_period()
        assert len(periods) >= 1
