import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from mcp_assistant.api.app import create_app
from mcp_assistant.api.auth.dependencies import get_current_user, make_session_cookie
from mcp_assistant.api.models.auth import UserInfo


async def test_login_disabled_returns_json(client_auth_disabled):
    resp = await client_auth_disabled.get("/auth/login")
    assert resp.status_code == 200
    assert resp.json() == {"enabled": False}


async def test_login_enabled_redirects(client_auth_enabled):
    resp = await client_auth_enabled.get("/auth/login", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "github.com/login/oauth/authorize" in resp.headers["location"]


async def test_callback_disabled_returns_404(client_auth_disabled):
    resp = await client_auth_disabled.get("/auth/callback?code=abc")
    assert resp.status_code == 404


async def test_callback_enabled_exchanges_code(fake_dirs):
    with patch.dict(os.environ, {"ENABLE_OAUTH2": "true"}):
        app = create_app()

        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {"access_token": "test-token"}
        mock_token_response.raise_for_status = MagicMock()

        mock_userinfo_response = MagicMock()
        mock_userinfo_response.json.return_value = {
            "id": 42,
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "avatar_url": "https://example.com/avatar.png",
        }
        mock_userinfo_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_token_response)
        mock_client.get = AsyncMock(return_value=mock_userinfo_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("mcp_assistant.api.auth.router.httpx.AsyncClient", return_value=mock_client):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.get("/auth/callback?code=abc", follow_redirects=False)

    assert resp.status_code in (302, 307)
    assert "session" in resp.cookies


async def test_me_disabled(client_auth_disabled):
    resp = await client_auth_disabled.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json() == {"auth_enabled": False}


async def test_me_enabled_unauthenticated(client_auth_enabled):
    resp = await client_auth_enabled.get("/auth/me")
    assert resp.status_code == 401


async def test_me_enabled_with_valid_session(fake_dirs):
    with patch.dict(os.environ, {"ENABLE_OAUTH2": "true"}):
        app = create_app()
        user = UserInfo(sub="1", login="testuser", name="Test User")
        cookie_value = make_session_cookie(user)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            ac.cookies.set("session", cookie_value)
            resp = await ac.get("/auth/me")

    assert resp.status_code == 200
    data = resp.json()
    assert data["login"] == "testuser"


async def test_logout_clears_cookie(client_auth_disabled):
    resp = await client_auth_disabled.post("/auth/logout")
    assert resp.status_code == 200
    assert resp.json() == {"logged_out": True}


async def test_v1_requires_auth_when_enabled(client_auth_enabled):
    resp = await client_auth_enabled.get("/api/v1/workflow/status")
    assert resp.status_code == 401


async def test_v1_accessible_when_auth_disabled(client_auth_disabled):
    resp = await client_auth_disabled.get("/api/v1/workflow/status")
    assert resp.status_code == 200
