from unittest.mock import patch

import pytest

import mcp_assistant.config as config_module
import mcp_assistant.tools.artifacts as artifacts_module


@pytest.fixture()
def fake_dirs(tmp_path):
    prds = tmp_path / "prds"
    specs = tmp_path / "specs"
    plans = tmp_path / "plans"
    with (
        patch.object(config_module, "PRDS_DIR", prds),
        patch.object(config_module, "SPECS_DIR", specs),
        patch.object(config_module, "PLANS_DIR", plans),
    ):
        # Re-patch inside the tools modules too
        with (
            patch("mcp_assistant.tools.artifacts.PRDS_DIR", prds),
            patch("mcp_assistant.tools.artifacts.SPECS_DIR", specs),
            patch("mcp_assistant.tools.artifacts.PLANS_DIR", plans),
        ):
            yield {"prds": prds, "specs": specs, "plans": plans}


class CaptureMCP:
    """Minimal mock that captures registered tools."""

    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


@pytest.fixture()
def mcp_and_tools(fake_dirs):
    mcp = CaptureMCP()
    artifacts_module.register(mcp)
    return mcp, fake_dirs


def test_create_prd(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    result = mcp.tools["create_prd"]("Minha Feature", "# PRD Content")
    assert result["filename"] == "prd-minha-feature.md"
    assert (dirs["prds"] / "prd-minha-feature.md").read_text() == "# PRD Content"


def test_create_prd_duplicate_raises(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    mcp.tools["create_prd"]("Minha Feature", "# PRD Content")
    with pytest.raises(ValueError, match="já existe"):
        mcp.tools["create_prd"]("Minha Feature", "# Another Content")


def test_create_spec(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    result = mcp.tools["create_spec"]("Sub Feature", "prd-minha-feature.md", "# Spec")
    assert result["filename"] == "spec-minha-feature-sub-feature.md"
    assert (dirs["specs"] / "spec-minha-feature-sub-feature.md").exists()


def test_create_plan(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    result = mcp.tools["create_plan"]("Deploy Pipeline", "# Plan")
    assert result["filename"] == "plan-deploy-pipeline.prompt.md"
    assert (dirs["plans"] / "plan-deploy-pipeline.prompt.md").read_text() == "# Plan"


def test_create_plan_duplicate_raises(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    mcp.tools["create_plan"]("Deploy Pipeline", "# Plan")
    with pytest.raises(ValueError, match="já existe"):
        mcp.tools["create_plan"]("Deploy Pipeline", "# Another Plan")
