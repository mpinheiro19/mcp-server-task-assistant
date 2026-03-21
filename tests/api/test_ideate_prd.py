"""Integration tests for the ideate_prd tool using FastMCP in-memory transport."""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastmcp import Client, FastMCP
from fastmcp.client.transports import FastMCPTransport

import mcp_assistant.config as config_module
import mcp_assistant.tools.artifacts as artifacts_module


@pytest.fixture()
def _mcp_env(tmp_path: Path):
    """Spin up an in-memory FastMCP server with artifact tools registered,
    all paths redirected to a temp directory."""
    prds = tmp_path / "prds"
    specs = tmp_path / "specs"
    plans = tmp_path / "plans"
    index_file = tmp_path / "index.md"

    with (
        patch.object(config_module, "PRDS_DIR", prds),
        patch.object(config_module, "SPECS_DIR", specs),
        patch.object(config_module, "PLANS_DIR", plans),
        patch.object(config_module, "INDEX_FILE", index_file),
        patch("mcp_assistant.tools.artifacts.PRDS_DIR", prds),
        patch("mcp_assistant.tools.artifacts.SPECS_DIR", specs),
        patch("mcp_assistant.tools.artifacts.PLANS_DIR", plans),
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index_file),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", prds),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", specs),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", plans),
    ):
        mcp = FastMCP("test-ideate-prd")
        artifacts_module.register(mcp)
        yield mcp, {"prds": prds, "specs": specs, "plans": plans, "index": index_file}


@pytest.mark.asyncio
async def test_ideate_prd_happy_path_creates_file(_mcp_env):
    """Full happy path: all elicitations answered → PRD file is created on disk."""
    mcp, dirs = _mcp_env
    responses = [
        {"value": "Integration Feature"},  # title (str wrapped as {value: ...})
        {  # IdeaDetails fields
            "problem_statement": "Users lose context when switching tabs",
            "target_audience": "Power users",
            "success_metrics": "Context restore rate 100%",
            "scope_in": "Tab state persistence",
        },
        {},  # approval (None response_type → empty dict)
    ]
    call_index = 0

    async def elicitation_handler(message, response_type, params, context):
        nonlocal call_index
        response = responses[call_index]
        call_index += 1
        return response

    async with Client(FastMCPTransport(mcp), elicitation_handler=elicitation_handler) as client:
        result = await client.call_tool("ideate_prd", {})

    # call_tool returns a list of content items; extract the text result
    assert result is not None
    assert call_index == 3
    prd_file = dirs["prds"] / "prd-integration-feature.md"
    assert prd_file.exists(), "PRD file should have been written to disk"
    content = prd_file.read_text()
    assert "# PRD: Integration Feature" in content
    assert "Users lose context" in content


@pytest.mark.asyncio
async def test_ideate_prd_cancel_at_title_no_file(_mcp_env):
    """Cancelling when asked for a title leaves no PRD file on disk."""
    mcp, dirs = _mcp_env

    async def elicitation_handler(message, response_type, params, context):
        from fastmcp.client.elicitation import ElicitResult

        return ElicitResult(action="cancel", content=None)

    async with Client(FastMCPTransport(mcp), elicitation_handler=elicitation_handler) as client:
        await client.call_tool("ideate_prd", {})

    assert not dirs["prds"].exists() or not list(dirs["prds"].glob("*.md"))


@pytest.mark.asyncio
async def test_ideate_prd_duplicate_warning_shown_and_user_continues(_mcp_env):
    """When a fuzzy-matching PRD exists, the warning elicitation is fired; accepting continues."""
    mcp, dirs = _mcp_env
    # Pre-create a related PRD
    dirs["prds"].mkdir(parents=True, exist_ok=True)
    (dirs["prds"] / "prd-dark-mode-legacy.md").write_text("old PRD")

    responses = [
        {"value": "Dark Mode"},  # title
        {},  # accept duplicate warning
        {  # details
            "problem_statement": "Users want dark theme",
            "target_audience": "All users",
            "success_metrics": "50% activation",
            "scope_in": "UI theming",
        },
        {},  # approval
    ]
    call_index = 0

    async def elicitation_handler(message, response_type, params, context):
        nonlocal call_index
        response = responses[call_index]
        call_index += 1
        return response

    async with Client(FastMCPTransport(mcp), elicitation_handler=elicitation_handler) as client:
        await client.call_tool("ideate_prd", {})

    assert call_index == 4, "All 4 elicitation steps should have fired"
    assert (dirs["prds"] / "prd-dark-mode.md").exists()
