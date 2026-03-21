import os
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

import mcp_assistant.resources.flow as flow_module
import mcp_assistant.tools.artifacts as artifacts_module
import mcp_assistant.tools.workflow as workflow_module
from mcp_assistant.api.app import create_app
from mcp_assistant.api.auth.dependencies import get_current_user
from mcp_assistant.api.models.auth import UserInfo


@pytest.fixture()
def fake_dirs(tmp_path):
    prds = tmp_path / "prds"
    specs = tmp_path / "specs"
    plans = tmp_path / "plans"
    index = tmp_path / "index.md"
    codes_root = tmp_path / "Codes"
    codes_root.mkdir()
    (codes_root / "project-a").mkdir()

    with (
        patch.object(artifacts_module, "PRDS_DIR", prds),
        patch.object(artifacts_module, "SPECS_DIR", specs),
        patch.object(artifacts_module, "PLANS_DIR", plans),
        patch.object(workflow_module, "PRDS_DIR", prds),
        patch.object(workflow_module, "SPECS_DIR", specs),
        patch.object(workflow_module, "PLANS_DIR", plans),
        patch.object(workflow_module, "INDEX_FILE", index),
        patch.object(flow_module, "PRDS_DIR", prds),
        patch.object(flow_module, "SPECS_DIR", specs),
        patch.object(flow_module, "PLANS_DIR", plans),
        patch.object(flow_module, "INDEX_FILE", index),
        patch.object(flow_module, "CODES_ROOT", codes_root),
    ):
        yield {
            "prds": prds,
            "specs": specs,
            "plans": plans,
            "index": index,
            "codes_root": codes_root,
        }


def _make_app_no_auth():
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: UserInfo(sub="1", login="testuser")
    return app


@pytest.fixture()
async def client(fake_dirs):
    app = _make_app_no_auth()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture()
async def client_auth_disabled(fake_dirs):
    with patch.dict(os.environ, {"ENABLE_OAUTH2": "false"}):
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac


@pytest.fixture()
async def client_auth_enabled(fake_dirs):
    with patch.dict(os.environ, {"ENABLE_OAUTH2": "true"}):
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
