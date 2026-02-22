"""Tests for auth API endpoints (register, login)."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
class TestRegister:
    async def test_register_success(self, client):
        resp = await client.post("/api/auth/register", json={
            "username": "newtherapist",
            "password": "pass123",
            "name": "New Therapist",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["user"]["username"] == "newtherapist"
        assert data["user"]["role"] == "therapist"
        assert data["user"]["is_approved"] is False

    async def test_register_duplicate_username(self, client):
        await client.post("/api/auth/register", json={
            "username": "dupuser",
            "password": "pass123",
            "name": "Dup User",
        })
        resp = await client.post("/api/auth/register", json={
            "username": "dupuser",
            "password": "pass456",
            "name": "Dup User 2",
        })
        assert resp.status_code == 400

    async def test_register_missing_fields(self, client):
        resp = await client.post("/api/auth/register", json={
            "username": "incomplete",
        })
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    async def test_login_admin_success(self, client):
        resp = await client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["user"]["role"] == "admin"

    async def test_login_therapist_success(self, client):
        # Register first
        await client.post("/api/auth/register", json={
            "username": "therapist1",
            "password": "pass123",
            "name": "Therapist 1",
        })
        resp = await client.post("/api/auth/login", json={
            "username": "therapist1",
            "password": "pass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["user"]["role"] == "therapist"

    async def test_login_wrong_password(self, client):
        resp = await client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client):
        resp = await client.post("/api/auth/login", json={
            "username": "doesnotexist",
            "password": "pass",
        })
        assert resp.status_code == 401

    async def test_login_missing_fields(self, client):
        resp = await client.post("/api/auth/login", json={
            "username": "admin",
        })
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestMe:
    async def test_get_me_endpoint(self, client):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 200
