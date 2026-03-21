"""
Security & Error Handling Tests
================================
Covers OWASP-relevant attack surfaces in the MCP server:

  1. Path traversal via filename parameters (CWE-22).
  2. Oversized payloads — tools must handle large content without crashing.
  3. Injection characters in feature names — slugifier must neutralise them.
  4. Force-guard enforcement on mutating operations.
  5. Timeout/edge-case behaviour: empty strings, None-like inputs.
  6. index.md corruption — graceful handling of malformed rows.
"""

from unittest.mock import patch

import pytest

import mcp_assistant.prompts.templates as templates_module
import mcp_assistant.resources.flow as flow_module
import mcp_assistant.tools.artifacts as artifacts_module
import mcp_assistant.tools.workflow as workflow_module
from mcp_assistant.utils import _slugify

# ---------------------------------------------------------------------------
# Shared stubs
# ---------------------------------------------------------------------------


class CaptureMCP:
    def __init__(self):
        self.tools: dict = {}
        self.resources: dict = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator

    def resource(self, uri: str):
        def decorator(fn):
            self.resources[uri] = fn
            return fn

        return decorator


# ---------------------------------------------------------------------------
# 1. Path traversal — resources
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_filename",
    [
        "../../etc/passwd",
        "../secrets.md",
        "subdir/../../etc/shadow",
        "/etc/passwd",
    ],
)
def test_get_prd_rejects_path_traversal(tmp_path, bad_filename):
    mcp = CaptureMCP()
    prds = tmp_path / "prds"
    prds.mkdir()
    with patch("mcp_assistant.resources.flow.PRDS_DIR", prds):
        flow_module.register(mcp)
    with pytest.raises(ValueError, match="[Ii]nvalid"):
        mcp.resources["flow://prd/{filename}"](bad_filename)


@pytest.mark.parametrize(
    "bad_filename",
    [
        "../../etc/passwd",
        "../secrets.md",
    ],
)
def test_get_spec_rejects_path_traversal(tmp_path, bad_filename):
    mcp = CaptureMCP()
    specs = tmp_path / "specs"
    specs.mkdir()
    with patch("mcp_assistant.resources.flow.SPECS_DIR", specs):
        flow_module.register(mcp)
    with pytest.raises(ValueError, match="[Ii]nvalid"):
        mcp.resources["flow://spec/{filename}"](bad_filename)


@pytest.mark.parametrize(
    "bad_filename",
    [
        "../../etc/passwd",
        "../secrets.md",
    ],
)
def test_get_plan_rejects_path_traversal(tmp_path, bad_filename):
    mcp = CaptureMCP()
    plans = tmp_path / "plans"
    plans.mkdir()
    with patch("mcp_assistant.resources.flow.PLANS_DIR", plans):
        flow_module.register(mcp)
    with pytest.raises(ValueError, match="[Ii]nvalid"):
        mcp.resources["flow://plan/{filename}"](bad_filename)


# ---------------------------------------------------------------------------
# 2. Path traversal — prompts
# ---------------------------------------------------------------------------


class CaptureMCPPrompts:
    def __init__(self):
        self.prompts: dict = {}

    def prompt(self):
        def decorator(fn):
            self.prompts[fn.__name__] = fn
            return fn

        return decorator


@pytest.mark.parametrize(
    "bad_filename",
    [
        "../../etc/passwd",
        "../secrets.md",
        "/etc/passwd",
    ],
)
def test_spec_from_prd_rejects_path_traversal(tmp_path, bad_filename):
    mcp = CaptureMCPPrompts()
    prds = tmp_path / "prds"
    prds.mkdir()
    with (
        patch("mcp_assistant.prompts.templates.PRDS_DIR", prds),
        patch("mcp_assistant.prompts.templates.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.prompts.templates.PLANS_DIR", tmp_path / "plans"),
        patch("mcp_assistant.prompts.templates.SPEC_ASSISTANT_DIR", tmp_path / "spec-assistant"),
        patch("mcp_assistant.prompts.templates.INDEX_FILE", tmp_path / "index.md"),
        patch("mcp_assistant.prompts.templates.COPILOT_INSTRUCTIONS", tmp_path / "instructions.md"),
    ):
        templates_module.register(mcp)
    with pytest.raises(ValueError, match="[Ii]nvalid"):
        mcp.prompts["spec_from_prd"](bad_filename)


@pytest.mark.parametrize(
    "bad_filename",
    [
        "../../etc/passwd",
        "../secrets.md",
    ],
)
def test_plan_from_spec_rejects_path_traversal(tmp_path, bad_filename):
    mcp = CaptureMCPPrompts()
    specs = tmp_path / "specs"
    specs.mkdir()
    with (
        patch("mcp_assistant.prompts.templates.PRDS_DIR", tmp_path / "prds"),
        patch("mcp_assistant.prompts.templates.SPECS_DIR", specs),
        patch("mcp_assistant.prompts.templates.PLANS_DIR", tmp_path / "plans"),
        patch("mcp_assistant.prompts.templates.SPEC_ASSISTANT_DIR", tmp_path / "spec-assistant"),
        patch("mcp_assistant.prompts.templates.INDEX_FILE", tmp_path / "index.md"),
        patch("mcp_assistant.prompts.templates.COPILOT_INSTRUCTIONS", tmp_path / "instructions.md"),
    ):
        templates_module.register(mcp)
    with pytest.raises(ValueError, match="[Ii]nvalid"):
        mcp.prompts["plan_from_spec"](bad_filename)


@pytest.mark.parametrize(
    "bad_filename",
    [
        "../../etc/passwd",
        "../secrets.md",
    ],
)
def test_review_artefact_rejects_path_traversal(tmp_path, bad_filename):
    mcp = CaptureMCPPrompts()
    prds = tmp_path / "prds"
    prds.mkdir()
    with (
        patch("mcp_assistant.prompts.templates.PRDS_DIR", prds),
        patch("mcp_assistant.prompts.templates.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.prompts.templates.PLANS_DIR", tmp_path / "plans"),
        patch("mcp_assistant.prompts.templates.SPEC_ASSISTANT_DIR", tmp_path / "spec-assistant"),
        patch("mcp_assistant.prompts.templates.INDEX_FILE", tmp_path / "index.md"),
        patch("mcp_assistant.prompts.templates.COPILOT_INSTRUCTIONS", tmp_path / "instructions.md"),
    ):
        templates_module.register(mcp)
    with pytest.raises(ValueError, match="[Ii]nvalid"):
        mcp.prompts["review_artefact"](bad_filename, "prd")


# ---------------------------------------------------------------------------
# 3. Injection characters in feature_name are sanitised by _slugify
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "malicious_name,expected_slug",
    [
        ("feature; rm -rf /", "feature-rm-rf"),
        ("feature | cat /etc/passwd", "feature-cat-etc-passwd"),
        # backtick → single separator dash
        ("feature`whoami`", "feature-whoami"),
        # $( and ) are each non-alphanum → two dashes collapse into separators
        ("feature$(id)", "feature-id"),
        ("../../../etc/passwd", "etc-passwd"),
        # < and > become leading/trailing dashes that get stripped; () split around 1
        ("<script>alert(1)</script>", "script-alert-1-script"),
    ],
)
def test_slugify_neutralises_injection_chars(malicious_name, expected_slug):
    slug = _slugify(malicious_name)
    assert slug == expected_slug
    # The slug must never contain shell-dangerous characters
    for ch in [";", "|", "`", "$", "(", ")", "<", ">", '"', "'", "&", "!"]:
        assert ch not in slug, f"Dangerous char '{ch}' leaked into slug: {slug}"


def test_create_prd_with_injection_name_produces_safe_filename(tmp_path):
    mcp = CaptureMCP()
    prds = tmp_path / "prds"
    index = tmp_path / "index.md"
    with (
        patch("mcp_assistant.tools.artifacts.PRDS_DIR", prds),
        patch("mcp_assistant.tools.artifacts.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.artifacts.PLANS_DIR", tmp_path / "plans"),
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", prds),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
    ):
        artifacts_module.register(mcp)
        result = mcp.tools["create_prd"]("feature; rm -rf /", "# PRD")

    # Filename must not contain shell-special characters
    filename = result["filename"]
    for ch in [";", "|", "`", "$", "(", ")", "<", ">", " ", "/"]:
        assert ch not in filename, f"Unsafe character '{ch}' in filename: {filename}"


# ---------------------------------------------------------------------------
# 4. Force-guard: update_index without force=True must raise PermissionError
# ---------------------------------------------------------------------------


def test_update_index_without_force_raises(tmp_path):
    mcp = CaptureMCP()
    index = tmp_path / "index.md"
    with (
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", tmp_path / "prds"),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
    ):
        workflow_module.register(mcp)
        with pytest.raises(PermissionError, match="force=True"):
            mcp.tools["update_index"]("prd-foo.md", "spec-foo.md", "Foo", "🟢 Done", "✅ Concluído")


# ---------------------------------------------------------------------------
# 5. Oversized payloads — tools must not crash on large inputs
# ---------------------------------------------------------------------------


def test_create_prd_handles_large_content(tmp_path):
    mcp = CaptureMCP()
    prds = tmp_path / "prds"
    index = tmp_path / "index.md"
    large_content = "x" * 1_000_000  # 1 MB of content
    with (
        patch("mcp_assistant.tools.artifacts.PRDS_DIR", prds),
        patch("mcp_assistant.tools.artifacts.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.artifacts.PLANS_DIR", tmp_path / "plans"),
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", prds),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
    ):
        artifacts_module.register(mcp)
        result = mcp.tools["create_prd"]("Big Feature", large_content)

    assert result["filename"] == "prd-big-feature.md"
    assert (prds / "prd-big-feature.md").stat().st_size == 1_000_000


# ---------------------------------------------------------------------------
# 6. Duplicate creation raises ValueError, not a silent overwrite
# ---------------------------------------------------------------------------


def test_create_spec_duplicate_raises(tmp_path):
    mcp = CaptureMCP()
    specs = tmp_path / "specs"
    index = tmp_path / "index.md"
    with (
        patch("mcp_assistant.tools.artifacts.PRDS_DIR", tmp_path / "prds"),
        patch("mcp_assistant.tools.artifacts.SPECS_DIR", specs),
        patch("mcp_assistant.tools.artifacts.PLANS_DIR", tmp_path / "plans"),
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", tmp_path / "prds"),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", specs),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
    ):
        artifacts_module.register(mcp)
        mcp.tools["create_spec"]("Auth Flow", "prd-auth.md", "# Spec v1")
        with pytest.raises(ValueError, match="already exists"):
            mcp.tools["create_spec"]("Auth Flow", "prd-auth.md", "# Spec v2 — overwrite attempt")

    original = (specs / "spec-auth-auth-flow.md").read_text()
    assert original == "# Spec v1", "Original content must not be overwritten on duplicate"


# ---------------------------------------------------------------------------
# 7. advance_stage with unknown feature raises ValueError (no silent no-op)
# ---------------------------------------------------------------------------


def test_advance_stage_unknown_feature_raises(tmp_path):
    mcp = CaptureMCP()
    index = tmp_path / "index.md"
    index.write_text(
        "| PRD Origem | Spec (Arquivo) | Feature | Plan Status | Implementation |\n"
        "| :--- | :--- | :--- | :--- | :--- |\n"
        "| prd-foo.md | spec-foo.md | Foo Feature | 🟡 Pending | ❌ Todo |\n"
    )
    with (
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", tmp_path / "prds"),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
    ):
        workflow_module.register(mcp)
        with pytest.raises(ValueError, match="not found"):
            mcp.tools["advance_stage"]("Nonexistent Feature", "🟢 Done", "✅ Concluído")


# ---------------------------------------------------------------------------
# 8. Malformed index.md rows are skipped gracefully (no crash)
# ---------------------------------------------------------------------------


def test_workflow_status_with_malformed_index_rows(tmp_path):
    mcp = CaptureMCP()
    index = tmp_path / "index.md"
    # Mix of valid and malformed rows
    index.write_text(
        "| PRD Origem | Spec (Arquivo) | Feature | Plan Status | Implementation |\n"
        "| :--- | :--- | :--- | :--- | :--- |\n"
        "| prd-foo.md | spec-foo.md | Foo Feature | 🟢 Done | ✅ Concluído |\n"
        "| only-two-cols |\n"  # malformed — fewer than 5 columns
        "| prd-bar.md | spec-bar.md | Bar Feature | 🟡 Pending | ❌ Todo |\n"
    )
    with (
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", tmp_path / "prds"),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
    ):
        workflow_module.register(mcp)
        result = mcp.tools["get_workflow_status"]()

    # Only the two valid rows must appear; the malformed row must be silently skipped
    assert len(result["features"]) == 2


# ---------------------------------------------------------------------------
# 9. list_artefacts with invalid type raises, not returns empty list
# ---------------------------------------------------------------------------


def test_list_artefacts_invalid_type_raises_not_empty(tmp_path):
    mcp = CaptureMCP()
    with (
        patch("mcp_assistant.tools.workflow.INDEX_FILE", tmp_path / "index.md"),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", tmp_path / "prds"),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", tmp_path / "specs"),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", tmp_path / "plans"),
    ):
        workflow_module.register(mcp)
        with pytest.raises(ValueError):
            mcp.tools["list_artefacts"]("unknown_type")
