import os
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from mcp_assistant.api.app import create_app
from mcp_assistant.api.auth.dependencies import get_current_user
from mcp_assistant.api.models.auth import UserInfo


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_docs_available(client):
    resp = await client.get("/docs")
    assert resp.status_code == 200


async def test_redoc_available(client):
    resp = await client.get("/redoc")
    assert resp.status_code == 200


async def test_cors_allowed_origin(fake_dirs):
    with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000"}):
        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: UserInfo(sub="1", login="testuser")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health", headers={"Origin": "http://localhost:3000"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


async def test_cors_disallowed_origin(fake_dirs):
    with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000"}):
        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: UserInfo(sub="1", login="testuser")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health", headers={"Origin": "http://evil.com"})
    assert resp.status_code == 200
    assert "access-control-allow-origin" not in resp.headers


async def test_cors_no_origins_configured(fake_dirs):
    with patch.dict(os.environ, {"CORS_ORIGINS": ""}):
        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: UserInfo(sub="1", login="testuser")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health", headers={"Origin": "http://anywhere.com"})
    assert resp.status_code == 200
    assert "access-control-allow-origin" not in resp.headers


async def test_api_versioning_prefix(client):
    resp = await client.get("/api/v1/workflow/status")
    assert resp.status_code == 200


async def test_auth_required_when_enabled(client_auth_enabled):
    resp = await client_auth_enabled.get("/api/v1/workflow/status")
    assert resp.status_code == 401
