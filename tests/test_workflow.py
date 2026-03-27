from unittest.mock import patch

import pytest

import mcp_assistant.tools.workflow as workflow_module
from mcp_assistant.utils import _parse_index_table

INDEX_CONTENT = """\
| PRD Source | Spec (File) | Feature | Plan Status | Elicitation | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| prd-foo.md | spec-foo.md | Foo Feature | 🟢 Done | — | ✅ Concluído |
| prd-bar.md | spec-bar.md | Bar Feature | 🟡 Pending | — | ❌ Todo |
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
    with pytest.raises(ValueError, match="Invalid plan_status"):
        mcp.tools["advance_stage"]("Bar Feature", "Invalid", "❌ Todo")


def test_advance_stage_invalid_impl_status(mcp_with_tools):
    mcp, _ = mcp_with_tools
    with pytest.raises(ValueError, match="Invalid implementation_status"):
        mcp.tools["advance_stage"]("Bar Feature", "🟢 Done", "Invalid")


def test_advance_stage_feature_not_found(mcp_with_tools):
    mcp, _ = mcp_with_tools
    with pytest.raises(ValueError, match="not found"):
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
    (prds / "nova-feature.md").write_text("# existing")
    with (
        patch("mcp_assistant.tools.workflow.PRDS_DIR", prds),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
        patch("mcp_assistant.tools.workflow.INDEX_FILE", tmp_path / "index.md"),
    ):
        workflow_module.register(mcp)
        result = mcp.tools["check_duplicate"]("Nova Feature")
    assert result["has_duplicate"] is True
    assert any("nova-feature.md" in m for m in result["matches"])


# --- update_index ---


def test_update_index_creates_index_when_missing(mcp_with_tools):
    mcp, index_file = mcp_with_tools
    index_file.unlink()
    content = mcp.tools["update_index"](
        "prd-new.md", "spec-new.md", "New Feature", "🟡 Pending", "❌ Todo", force=True
    )
    assert "prd-new.md" in content
    assert "New Feature" in content
    assert index_file.exists()


def test_update_index_appends_new_row(mcp_with_tools):
    mcp, index_file = mcp_with_tools
    mcp.tools["update_index"](
        "prd-baz.md", "spec-baz.md", "Baz Feature", "🟢 Done", "✅ Concluído", force=True
    )
    rows = _parse_index_table(index_file.read_text())
    assert any(r["prd"] == "prd-baz.md" for r in rows)


def test_update_index_replaces_existing_row(mcp_with_tools):
    mcp, index_file = mcp_with_tools
    mcp.tools["update_index"](
        "prd-foo.md", "spec-foo.md", "Foo Feature", "🟡 Pending", "🔄 In Progress", force=True
    )
    rows = _parse_index_table(index_file.read_text())
    foo = next(r for r in rows if r["prd"] == "prd-foo.md")
    assert foo["plan_status"] == "🟡 Pending"
    assert foo["implementation"] == "🔄 In Progress"


# --- list_artefacts ---


@pytest.fixture()
def mcp_with_artefacts(tmp_path):
    mcp = CaptureMCP()
    prds = tmp_path / "prds"
    specs = tmp_path / "specs"
    plans = tmp_path / "plans"
    prds.mkdir()
    specs.mkdir()
    plans.mkdir()
    (prds / "alpha.md").write_text("# PRD Alpha")
    (specs / "alpha").mkdir()
    (specs / "alpha" / "detail.md").write_text("# Spec Alpha")
    (plans / "alpha.md").write_text("# Plan Alpha")
    index = tmp_path / "index.md"
    index.write_text(INDEX_CONTENT)
    with (
        patch("mcp_assistant.tools.workflow.PRDS_DIR", prds),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", specs),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", plans),
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index),
    ):
        workflow_module.register(mcp)
        yield mcp


def test_list_artefacts_prd(mcp_with_artefacts):
    result = mcp_with_artefacts.tools["list_artefacts"]("prd")
    assert len(result) == 1
    assert result[0]["filename"] == "alpha.md"
    assert "size_bytes" in result[0]
    assert "modified_at" in result[0]


def test_list_artefacts_spec(mcp_with_artefacts):
    result = mcp_with_artefacts.tools["list_artefacts"]("spec")
    assert len(result) == 1
    assert result[0]["filename"] == "alpha/detail.md"


def test_list_artefacts_plan(mcp_with_artefacts):
    result = mcp_with_artefacts.tools["list_artefacts"]("plan")
    assert len(result) == 1
    assert result[0]["filename"] == "alpha.md"


def test_list_artefacts_all(mcp_with_artefacts):
    result = mcp_with_artefacts.tools["list_artefacts"]("all")
    assert len(result) == 3
    types = {r["type"] for r in result}
    assert types == {"prd", "spec", "plan"}


def test_list_artefacts_invalid_type_raises(mcp_with_artefacts):
    with pytest.raises(ValueError, match="Invalid artefact_type"):
        mcp_with_artefacts.tools["list_artefacts"]("unknown")


# --- update_index force guard ---


def test_update_index_force_false_raises(mcp_with_tools):
    mcp, _ = mcp_with_tools
    with pytest.raises(PermissionError, match="force=True"):
        mcp.tools["update_index"]("prd-foo.md", "spec-foo.md", "Foo Feature", "🟢 Done", "❌ Todo")


def test_update_index_force_true_works(mcp_with_tools):
    mcp, index_file = mcp_with_tools
    content = mcp.tools["update_index"](
        "prd-foo.md", "spec-foo-updated.md", "Foo Feature", "🟢 Done", "✅ Concluído", force=True
    )
    assert "spec-foo-updated.md" in content


# --- sync_index ---


def test_sync_index_adds_missing_prd(tmp_path):
    mcp = CaptureMCP()
    prds = tmp_path / "prds"
    prds.mkdir()
    (prds / "nova-feature.md").write_text("# PRD")
    index_file = tmp_path / "index.md"
    with (
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index_file),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", prds),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
    ):
        workflow_module.register(mcp)
        result = mcp.tools["sync_index"]()
    assert "nova-feature.md" in result["added"]
    rows = _parse_index_table(index_file.read_text())
    assert len(rows) == 1
    assert rows[0]["plan_status"] == "⏳ Waiting for Spec"
    assert rows[0]["implementation"] == "❌ Todo"


def test_sync_index_updates_spec_field(tmp_path):
    mcp = CaptureMCP()
    prds = tmp_path / "prds"
    prds.mkdir()
    specs = tmp_path / "specs"
    (prds / "foo.md").write_text("# PRD")
    (specs / "foo").mkdir(parents=True)
    (specs / "foo" / "bar.md").write_text("# Spec")
    index_file = tmp_path / "index.md"
    index_file.write_text(
        "| PRD Source | Spec (File) | Feature | Plan Status | Elicitation | Implementation |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        "| foo.md |  | Foo | ⏳ Waiting for Spec | — | ❌ Todo |\n"
    )
    with (
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index_file),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", prds),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", specs),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
    ):
        workflow_module.register(mcp)
        result = mcp.tools["sync_index"]()
    assert "foo.md" in result["updated"]
    rows = _parse_index_table(index_file.read_text())
    foo = next(r for r in rows if r["prd"] == "foo.md")
    assert foo["spec"] == "foo/bar.md"
    assert foo["plan_status"] == "🟡 Spec Draft"


# ---------------------------------------------------------------------------
# Elicitation column tests
# ---------------------------------------------------------------------------

INDEX_6COL = """\
| PRD Source | Spec (File) | Feature | Plan Status | Elicitation | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| prd-foo.md | spec-foo.md | Foo Feature | 🟢 Done | ✅ Consolidated | ✅ Concluído |
| prd-bar.md | spec-bar.md | Bar Feature | 🟡 Pending | ⏳ Pending | ❌ Todo |
"""

INDEX_5COL_LEGACY = """\
| PRD Source | Spec (File) | Feature | Plan Status | Implementation |
| :--- | :--- | :--- | :--- | :--- |
| prd-foo.md | spec-foo.md | Foo Feature | 🟢 Done | ✅ Concluído |
| prd-bar.md | spec-bar.md | Bar Feature | 🟡 Pending | ❌ Todo |
"""


def test_parse_index_table_5col_backward_compat():
    rows = _parse_index_table(INDEX_5COL_LEGACY)
    assert len(rows) == 2
    for row in rows:
        assert row["elicitation"] == "—"


def test_parse_index_table_6col():
    rows = _parse_index_table(INDEX_6COL)
    foo = next(r for r in rows if r["prd"] == "prd-foo.md")
    bar = next(r for r in rows if r["prd"] == "prd-bar.md")
    assert foo["elicitation"] == "✅ Consolidated"
    assert bar["elicitation"] == "⏳ Pending"


def test_update_index_with_elicitation_column(tmp_path):
    mcp = CaptureMCP()
    index_file = tmp_path / "index.md"
    with (
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index_file),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", tmp_path / "prds"),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
    ):
        workflow_module.register(mcp)
        mcp.tools["update_index"](
            "prd-new.md",
            "spec-new.md",
            "New Feature",
            "🟡 Pending",
            "❌ Todo",
            elicitation_status="⏳ Pending",
            force=True,
        )
    content = index_file.read_text()
    assert "⏳ Pending" in content


def test_update_index_preserves_elicitation(tmp_path):
    mcp = CaptureMCP()
    index_file = tmp_path / "index.md"
    index_file.write_text(INDEX_6COL)
    with (
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index_file),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", tmp_path / "prds"),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
    ):
        workflow_module.register(mcp)
        # Call with default elicitation_status="—" — should NOT overwrite existing value
        mcp.tools["update_index"](
            "prd-foo.md",
            "spec-foo.md",
            "Foo Feature",
            "🟢 Done",
            "✅ Concluído",
            force=True,
        )
    rows = _parse_index_table(index_file.read_text())
    foo = next(r for r in rows if r["prd"] == "prd-foo.md")
    assert foo["elicitation"] == "✅ Consolidated"


def test_get_workflow_status_includes_elicitation(tmp_path):
    mcp = CaptureMCP()
    index_file = tmp_path / "index.md"
    index_file.write_text(INDEX_6COL)
    with (
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index_file),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", tmp_path / "prds"),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
    ):
        workflow_module.register(mcp)
        result = mcp.tools["get_workflow_status"]()
    for feature in result["features"]:
        assert "elicitation" in feature


def test_advance_stage_preserves_elicitation(tmp_path):
    mcp = CaptureMCP()
    index_file = tmp_path / "index.md"
    index_file.write_text(INDEX_6COL)
    with (
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index_file),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", tmp_path / "prds"),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
    ):
        workflow_module.register(mcp)
        mcp.tools["advance_stage"]("Foo Feature", "🟢 Done", "✅ Concluído")
    rows = _parse_index_table(index_file.read_text())
    foo = next(r for r in rows if r["feature"] == "Foo Feature")
    assert foo["elicitation"] == "✅ Consolidated"


def test_sync_index_preserves_elicitation(tmp_path):
    mcp = CaptureMCP()
    prds = tmp_path / "prds"
    prds.mkdir()
    specs = tmp_path / "specs"
    (prds / "foo.md").write_text("# PRD")
    (specs / "foo").mkdir(parents=True)
    (specs / "foo" / "bar.md").write_text("# Spec")
    index_file = tmp_path / "index.md"
    index_file.write_text(
        "| PRD Source | Spec (File) | Feature | Plan Status | Elicitation | Implementation |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        "| foo.md |  | Foo | ⏳ Waiting for Spec | ✅ Consolidated | ❌ Todo |\n"
    )
    with (
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index_file),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", prds),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", specs),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
    ):
        workflow_module.register(mcp)
        mcp.tools["sync_index"]()
    rows = _parse_index_table(index_file.read_text())
    foo = next(r for r in rows if r["prd"] == "foo.md")
    assert foo["elicitation"] == "✅ Consolidated"


def test_get_index_row_by_feature_found(tmp_path):
    index_file = tmp_path / "index.md"
    index_file.write_text(INDEX_6COL)
    with patch("mcp_assistant.tools.workflow.INDEX_FILE", index_file):
        import mcp_assistant.tools.workflow as wf

        row = wf._get_index_row_by_feature("Foo Feature")
    assert row is not None
    assert row["prd"] == "prd-foo.md"
    assert row["elicitation"] == "✅ Consolidated"


def test_get_index_row_by_feature_not_found(tmp_path):
    index_file = tmp_path / "index.md"
    index_file.write_text(INDEX_6COL)
    with patch("mcp_assistant.tools.workflow.INDEX_FILE", index_file):
        import mcp_assistant.tools.workflow as wf

        row = wf._get_index_row_by_feature("Nonexistent Feature")
    assert row is None
