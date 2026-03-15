import pytest
from unittest.mock import patch
from pathlib import Path

import mcp_assistant.tools.workflow as workflow_module
import mcp_assistant.config as config_module
from mcp_assistant.utils import _parse_index_table

INDEX_CONTENT = """\
| PRD Origem | Spec (Arquivo) | Feature | Plan Status | Implementation |
| :--- | :--- | :--- | :--- | :--- |
| prd-foo.md | spec-foo.md | Foo Feature | 🟢 Done | ✅ Concluído |
| prd-bar.md | spec-bar.md | Bar Feature | 🟡 Pending | ❌ Todo |
"""


class CaptureMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


@pytest.fixture()
def index_file(tmp_path):
    f = tmp_path / "index.md"
    f.write_text(INDEX_CONTENT)
    return f


@pytest.fixture()
def mcp_with_tools(index_file):
    mcp = CaptureMCP()
    with (
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index_file),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", index_file.parent / "prds"),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", index_file.parent / "specs"),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", index_file.parent / "plans"),
    ):
        workflow_module.register(mcp)
        yield mcp, index_file


def test_get_workflow_status(mcp_with_tools):
    mcp, _ = mcp_with_tools
    result = mcp.tools["get_workflow_status"]()
    assert result["summary"]["done"] == 1
    assert result["summary"]["todo"] == 1
    assert len(result["features"]) == 2


def test_get_workflow_status_no_file(tmp_path):
    mcp = CaptureMCP()
    missing = tmp_path / "missing.md"
    with patch("mcp_assistant.tools.workflow.INDEX_FILE", missing):
        workflow_module.register(mcp)
        result = mcp.tools["get_workflow_status"]()
    assert result == {"features": [], "summary": {"done": 0, "in_progress": 0, "todo": 0}}


def test_advance_stage_updates_status(mcp_with_tools):
    mcp, index_file = mcp_with_tools
    mcp.tools["advance_stage"]("Bar Feature", "🟢 Done", "✅ Concluído")
    updated = _parse_index_table(index_file.read_text())
    bar = next(f for f in updated if f["feature"] == "Bar Feature")
    assert bar["plan_status"] == "🟢 Done"
    assert bar["implementation"] == "✅ Concluído"


def test_advance_stage_invalid_plan_status(mcp_with_tools):
    mcp, _ = mcp_with_tools
    with pytest.raises(ValueError, match="plan_status inválido"):
        mcp.tools["advance_stage"]("Bar Feature", "Invalid", "❌ Todo")


def test_advance_stage_invalid_impl_status(mcp_with_tools):
    mcp, _ = mcp_with_tools
    with pytest.raises(ValueError, match="implementation_status inválido"):
        mcp.tools["advance_stage"]("Bar Feature", "🟢 Done", "Invalid")


def test_advance_stage_feature_not_found(mcp_with_tools):
    mcp, _ = mcp_with_tools
    with pytest.raises(ValueError, match="não encontrada"):
        mcp.tools["advance_stage"]("Nonexistent", "🟢 Done", "✅ Concluído")


def test_check_duplicate_no_match(tmp_path):
    mcp = CaptureMCP()
    prds = tmp_path / "prds"
    prds.mkdir()
    with (
        patch("mcp_assistant.tools.workflow.PRDS_DIR", prds),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
        patch("mcp_assistant.tools.workflow.INDEX_FILE", tmp_path / "index.md"),
    ):
        workflow_module.register(mcp)
        result = mcp.tools["check_duplicate"]("Nova Feature")
    assert result == {"has_duplicate": False, "matches": []}


def test_check_duplicate_finds_match(tmp_path):
    mcp = CaptureMCP()
    prds = tmp_path / "prds"
    prds.mkdir()
    (prds / "prd-nova-feature.md").write_text("# existing")
    with (
        patch("mcp_assistant.tools.workflow.PRDS_DIR", prds),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
        patch("mcp_assistant.tools.workflow.INDEX_FILE", tmp_path / "index.md"),
    ):
        workflow_module.register(mcp)
        result = mcp.tools["check_duplicate"]("Nova Feature")
    assert result["has_duplicate"] is True
    assert any("prd-nova-feature.md" in m for m in result["matches"])
