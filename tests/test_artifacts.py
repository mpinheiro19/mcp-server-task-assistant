from unittest.mock import patch

import pytest

import mcp_assistant.config as config_module
import mcp_assistant.tools.artifacts as artifacts_module
from mcp_assistant.utils import _parse_index_table


@pytest.fixture()
def fake_dirs(tmp_path):
    prds = tmp_path / "prds"
    specs = tmp_path / "specs"
    plans = tmp_path / "plans"
    index_file = tmp_path / "index.md"
    with (
        patch.object(config_module, "PRDS_DIR", prds),
        patch.object(config_module, "SPECS_DIR", specs),
        patch.object(config_module, "PLANS_DIR", plans),
    ):
        with (
            patch("mcp_assistant.tools.artifacts.PRDS_DIR", prds),
            patch("mcp_assistant.tools.artifacts.SPECS_DIR", specs),
            patch("mcp_assistant.tools.artifacts.PLANS_DIR", plans),
            patch("mcp_assistant.tools.workflow.INDEX_FILE", index_file),
            patch("mcp_assistant.tools.workflow.PRDS_DIR", prds),
            patch("mcp_assistant.tools.workflow.SPECS_DIR", specs),
            patch("mcp_assistant.tools.workflow.PLANS_DIR", plans),
        ):
            yield {"prds": prds, "specs": specs, "plans": plans, "index": index_file}


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
    with pytest.raises(ValueError, match="already exists"):
        mcp.tools["create_prd"]("Minha Feature", "# Another Content")


def test_create_spec(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    result = mcp.tools["create_spec"]("Sub Feature", "prd-minha-feature.md", "# Spec")
    assert result["filename"] == "spec-minha-feature-sub-feature.md"
    assert (dirs["specs"] / "spec-minha-feature-sub-feature.md").exists()


def test_create_plan(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    result = mcp.tools["create_plan"](
        "Deploy Pipeline", "spec-deploy-pipeline.prompt.md", "# Plan"
    )
    assert result["filename"] == "plan-deploy-pipeline.prompt.md"
    assert (dirs["plans"] / "plan-deploy-pipeline.prompt.md").read_text() == "# Plan"


def test_create_plan_duplicate_raises(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    mcp.tools["create_plan"]("Deploy Pipeline", "spec-deploy-pipeline.prompt.md", "# Plan")
    with pytest.raises(ValueError, match="already exists"):
        mcp.tools["create_plan"](
            "Deploy Pipeline", "spec-deploy-pipeline.prompt.md", "# Another Plan"
        )


# ---------------------------------------------------------------------------
# Index integration tests
# ---------------------------------------------------------------------------


def test_create_prd_updates_index(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    mcp.tools["create_prd"]("My Feature", "# PRD Content")
    rows = _parse_index_table(dirs["index"].read_text())
    assert len(rows) == 1
    assert rows[0]["prd"] == "prd-my-feature.md"
    assert rows[0]["plan_status"] == "⏳ Waiting for Spec"
    assert rows[0]["implementation"] == "❌ Todo"


def test_create_spec_updates_index(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    mcp.tools["create_prd"]("My Feature", "# PRD")
    mcp.tools["create_spec"]("Sub Feature", "prd-my-feature.md", "# Spec")
    rows = _parse_index_table(dirs["index"].read_text())
    assert len(rows) == 1
    assert rows[0]["spec"] == "spec-my-feature-sub-feature.md"
    assert rows[0]["plan_status"] == "🟡 Spec Draft"
    assert rows[0]["implementation"] == "❌ Todo"


def test_create_plan_updates_index(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    mcp.tools["create_prd"]("My Feature", "# PRD")
    mcp.tools["create_spec"]("Sub Feature", "prd-my-feature.md", "# Spec")
    mcp.tools["create_plan"]("Sub Feature", "spec-my-feature-sub-feature.md", "# Plan")
    rows = _parse_index_table(dirs["index"].read_text())
    assert len(rows) == 1
    assert rows[0]["plan_status"] == "🟢 Done"
    assert rows[0]["implementation"] == "❌ Todo"


def test_create_prd_index_failure_best_effort(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    with patch("mcp_assistant.tools.artifacts._update_index", side_effect=OSError("disk full")):
        result = mcp.tools["create_prd"]("Fail Feature", "# PRD")
    assert result["filename"] == "prd-fail-feature.md"
    assert (dirs["prds"] / "prd-fail-feature.md").exists()
    assert "index_warning" in result
    assert "disk full" in result["index_warning"]
