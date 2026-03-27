"""Integration tests for the ideate_prd tool using FastMCP in-memory transport."""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastmcp import Client, FastMCP
from fastmcp.client.transports import FastMCPTransport

import mcp_assistant.config as config_module
import mcp_assistant.tools.artifacts as artifacts_module

_SAMPLE_PRD = """\
# PRD: Integration Feature

## Problem Statement
Users lose context when switching tabs

## User Stories
- As a power user, I want tab state persistence so that I don't lose context.

## Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Data loss | Medium | High | Auto-save |

## Open Questions
- [ ] What is the max number of tabs to persist?
"""


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


def _make_elicitation_handler(responses):
    """Build an elicitation handler that returns responses sequentially."""
    call_index = 0

    async def handler(message, response_type, params, context):
        nonlocal call_index
        response = responses[call_index]
        call_index += 1
        return response

    # Expose call_index via a mutable wrapper so tests can assert on it
    handler.call_count = lambda: call_index
    return handler


_DETAILS_RESPONSE = {
    "problem_statement": "Users lose context when switching tabs",
    "target_audience": "Power users",
    "success_metrics": "Context restore rate 100%",
    "scope_in": "Tab state persistence",
    "project_path": "",
}


@pytest.mark.asyncio
async def test_ideate_prd_happy_path_returns_draft(_mcp_env):
    """Happy path: title + choice (skip) + details → LLM sampling → returns draft."""
    mcp, dirs = _mcp_env
    elicitation = _make_elicitation_handler(
        [
            {"value": "Integration Feature"},  # title
            {"run_elicitation": False},  # choice: skip pre-PRD elicitation
            _DETAILS_RESPONSE,  # details
        ]
    )

    def sampling_handler(messages, params, context):
        return _SAMPLE_PRD

    async with Client(
        FastMCPTransport(mcp),
        elicitation_handler=elicitation,
        sampling_handler=sampling_handler,
    ) as client:
        result = await client.call_tool("ideate_prd", {})

    assert result is not None
    assert result.structured_content is not None
    sc = result.structured_content
    assert sc["saved"] is True, "Draft should be auto-saved when no duplicate exists"
    assert sc["sampling_used"] is True
    assert sc["feature_name"] == "Integration Feature"
    assert "filename" in sc
    assert "path" in sc
    assert "User Stories" in sc["draft"]
    assert "Risks" in sc["draft"]
    assert "Open Questions" in sc["draft"]
    # File must exist on disk
    assert dirs["prds"].exists() and list(dirs["prds"].glob("*.md"))


@pytest.mark.asyncio
async def test_ideate_prd_sampling_fallback(_mcp_env):
    """When LLM sampling fails, the tool falls back to the basic template draft."""
    mcp, dirs = _mcp_env
    elicitation = _make_elicitation_handler(
        [
            {"value": "Fallback Feature"},  # title
            {"run_elicitation": False},  # choice: skip pre-PRD elicitation
            _DETAILS_RESPONSE,  # details
        ]
    )

    def sampling_handler(messages, params, context):
        raise RuntimeError("Sampling not supported")

    async with Client(
        FastMCPTransport(mcp),
        elicitation_handler=elicitation,
        sampling_handler=sampling_handler,
    ) as client:
        result = await client.call_tool("ideate_prd", {})

    assert result is not None
    sc = result.structured_content
    assert sc["saved"] is True
    assert sc["sampling_used"] is False
    assert sc["feature_name"] == "Fallback Feature"
    assert "filename" in sc
    assert "path" in sc
    # Fallback draft uses _render_prd_draft template
    assert "# PRD: Fallback Feature" in sc["draft"]
    assert "Users lose context" in sc["draft"]
    # File must exist on disk
    assert dirs["prds"].exists() and list(dirs["prds"].glob("*.md"))


@pytest.mark.asyncio
async def test_ideate_prd_cancel_at_title_no_file(_mcp_env):
    """Cancelling when asked for a title leaves no PRD file on disk."""
    mcp, dirs = _mcp_env

    async def elicitation_handler(message, response_type, params, context):
        from fastmcp.client.elicitation import ElicitResult

        return ElicitResult(action="cancel", content=None)

    async with Client(FastMCPTransport(mcp), elicitation_handler=elicitation_handler) as client:
        result = await client.call_tool("ideate_prd", {})

    assert not dirs["prds"].exists() or not list(dirs["prds"].glob("*.md"))
    assert result.structured_content["saved"] is False
    assert "Cancelled" in result.structured_content["reason"]


@pytest.mark.asyncio
async def test_ideate_prd_duplicate_blocks_creation(_mcp_env):
    """When a fuzzy-matching PRD exists, the tool returns an error immediately without prompting
    for extra elicitation — this prevents the id-collision bug where VS Code assigns the same
    integer ID to both the tools/call request and an elicitation request."""
    mcp, dirs = _mcp_env
    # Pre-create a related PRD
    dirs["prds"].mkdir(parents=True, exist_ok=True)
    (dirs["prds"] / "prd-dark-mode-legacy.md").write_text("old PRD")

    elicitation = _make_elicitation_handler(
        [
            {"value": "Dark Mode"},
        ]
    )

    async with Client(FastMCPTransport(mcp), elicitation_handler=elicitation) as client:
        result = await client.call_tool("ideate_prd", {})

    assert elicitation.call_count() == 1, "Only the title elicitation should have fired"
    assert not (dirs["prds"] / "prd-dark-mode.md").exists()
    assert result is not None
    assert result.structured_content is not None
    assert result.structured_content["saved"] is False
    assert "already exists" in result.structured_content["reason"]


@pytest.mark.asyncio
async def test_ideate_prd_with_project_path(_mcp_env, tmp_path):
    """project_path in details is passed to workspace context gathering."""
    mcp, dirs = _mcp_env

    # Create a fake project with README
    project = tmp_path / "my-project"
    project.mkdir()
    (project / "README.md").write_text("# My Project\nA test project.")
    (project / "pyproject.toml").write_text('[project]\nname = "my-project"')

    details_with_path = {**_DETAILS_RESPONSE, "project_path": str(project)}
    elicitation = _make_elicitation_handler(
        [
            {"value": "Project Feature"},  # title
            {"run_elicitation": False},  # choice: skip pre-PRD elicitation
            details_with_path,  # details
        ]
    )

    def sampling_handler(messages, params, context):
        return _SAMPLE_PRD

    async with Client(
        FastMCPTransport(mcp),
        elicitation_handler=elicitation,
        sampling_handler=sampling_handler,
    ) as client:
        result = await client.call_tool("ideate_prd", {})

    sc = result.structured_content
    assert sc["saved"] is True
    assert sc["sampling_used"] is True
    assert sc["feature_name"] == "Project Feature"
    assert "filename" in sc
    assert dirs["prds"].exists() and list(dirs["prds"].glob("*.md"))
