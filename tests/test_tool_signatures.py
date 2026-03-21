"""
Tool Signature Validation
=========================
Verifies that every function registered with @mcp.tool() meets the quality bar
needed for a well-behaved MCP server:

  - All parameters carry explicit type annotations.
  - The function declares a return type annotation.
  - A non-trivial docstring exists (≥ 20 chars).
  - The docstring contains enough semantic signal for an LLM to decide
    *when* and *how* to call the tool (checked via keyword presence).
"""

import inspect
from unittest.mock import patch

import pytest

import mcp_assistant.tools.artifacts as artifacts_module
import mcp_assistant.tools.workflow as workflow_module

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class CaptureMCP:
    """Minimal stub that records every function passed to @mcp.tool()."""

    def __init__(self):
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


def _collect_tools(tmp_path) -> dict[str, object]:
    prds = tmp_path / "prds"
    specs = tmp_path / "specs"
    plans = tmp_path / "plans"
    index = tmp_path / "index.md"

    mcp = CaptureMCP()
    with (
        patch("mcp_assistant.tools.artifacts.PRDS_DIR", prds),
        patch("mcp_assistant.tools.artifacts.SPECS_DIR", specs),
        patch("mcp_assistant.tools.artifacts.PLANS_DIR", plans),
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", prds),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", specs),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", plans),
    ):
        artifacts_module.register(mcp)
        workflow_module.register(mcp)

    return mcp.tools


# ---------------------------------------------------------------------------
# Parametrised fixture — one test instance per tool
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def all_tools(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("sig_check")
    return _collect_tools(tmp)


@pytest.fixture(params=["create_prd", "create_spec", "create_plan"])
def artifact_tool_name(request):
    return request.param


@pytest.fixture(
    params=[
        "get_workflow_status",
        "update_index",
        "advance_stage",
        "check_duplicate",
        "list_artefacts",
        "sync_index",
    ]
)
def workflow_tool_name(request):
    return request.param


# ---------------------------------------------------------------------------
# 1. Every parameter must carry a type annotation
# ---------------------------------------------------------------------------


def test_artifact_tool_parameters_are_typed(all_tools, artifact_tool_name):
    fn = all_tools[artifact_tool_name]
    sig = inspect.signature(fn)
    for name, param in sig.parameters.items():
        assert (
            param.annotation is not inspect.Parameter.empty
        ), f"{artifact_tool_name}: parameter '{name}' has no type annotation"


def test_workflow_tool_parameters_are_typed(all_tools, workflow_tool_name):
    fn = all_tools[workflow_tool_name]
    sig = inspect.signature(fn)
    for name, param in sig.parameters.items():
        assert (
            param.annotation is not inspect.Parameter.empty
        ), f"{workflow_tool_name}: parameter '{name}' has no type annotation"


# ---------------------------------------------------------------------------
# 2. Every tool must declare a return type annotation
# ---------------------------------------------------------------------------


def test_artifact_tool_has_return_annotation(all_tools, artifact_tool_name):
    fn = all_tools[artifact_tool_name]
    sig = inspect.signature(fn)
    assert (
        sig.return_annotation is not inspect.Parameter.empty
    ), f"{artifact_tool_name}: missing return type annotation"


def test_workflow_tool_has_return_annotation(all_tools, workflow_tool_name):
    fn = all_tools[workflow_tool_name]
    sig = inspect.signature(fn)
    assert (
        sig.return_annotation is not inspect.Parameter.empty
    ), f"{workflow_tool_name}: missing return type annotation"


# ---------------------------------------------------------------------------
# 3. Every tool must have a meaningful docstring
# ---------------------------------------------------------------------------

_MIN_DOCSTRING_LEN = 20


def test_artifact_tool_has_docstring(all_tools, artifact_tool_name):
    fn = all_tools[artifact_tool_name]
    doc = inspect.getdoc(fn) or ""
    assert (
        len(doc) >= _MIN_DOCSTRING_LEN
    ), f"{artifact_tool_name}: docstring too short ({len(doc)} chars)"


def test_workflow_tool_has_docstring(all_tools, workflow_tool_name):
    fn = all_tools[workflow_tool_name]
    doc = inspect.getdoc(fn) or ""
    assert (
        len(doc) >= _MIN_DOCSTRING_LEN
    ), f"{workflow_tool_name}: docstring too short ({len(doc)} chars)"


# ---------------------------------------------------------------------------
# 4. create_* tools must mention the artifact type in their docstring
#    (LLMs need this to choose the right tool)
# ---------------------------------------------------------------------------


def test_create_prd_docstring_mentions_prd(all_tools):
    doc = (inspect.getdoc(all_tools["create_prd"]) or "").lower()
    assert "prd" in doc


def test_create_spec_docstring_mentions_spec(all_tools):
    doc = (inspect.getdoc(all_tools["create_spec"]) or "").lower()
    assert "spec" in doc


def test_create_plan_docstring_mentions_plan(all_tools):
    doc = (inspect.getdoc(all_tools["create_plan"]) or "").lower()
    assert "plan" in doc


# ---------------------------------------------------------------------------
# 5. Guard tools must document their safety intent
# ---------------------------------------------------------------------------


def test_update_index_docstring_warns_about_force(all_tools):
    doc = inspect.getdoc(all_tools["update_index"]) or ""
    assert "force" in doc.lower(), "update_index docstring must mention the 'force' guard"


def test_check_duplicate_docstring_is_readonly(all_tools):
    doc = inspect.getdoc(all_tools["check_duplicate"]) or ""
    assert any(
        kw in doc.lower() for kw in ("read", "modify", "hint")
    ), "check_duplicate docstring should state it is read-only"


# ---------------------------------------------------------------------------
# 6. advance_stage must enumerate valid status values in its docstring
# ---------------------------------------------------------------------------


def test_advance_stage_docstring_lists_valid_statuses(all_tools):
    doc = inspect.getdoc(all_tools["advance_stage"]) or ""
    assert (
        "⏳" in doc or "Waiting" in doc
    ), "advance_stage docstring must list valid plan_status values"
    assert (
        "❌" in doc or "Todo" in doc
    ), "advance_stage docstring must list valid implementation_status values"


# ---------------------------------------------------------------------------
# 7. Return types must be concrete (not Any or missing)
# ---------------------------------------------------------------------------


def test_create_prd_returns_dict(all_tools):

    sig = inspect.signature(all_tools["create_prd"])
    assert sig.return_annotation in (
        dict,
        dict,
        "dict",
    ), "create_prd must declare -> dict return type"


def test_list_artefacts_returns_list(all_tools):

    sig = inspect.signature(all_tools["list_artefacts"])
    origin = getattr(sig.return_annotation, "__origin__", sig.return_annotation)
    assert origin in (list, list), "list_artefacts must declare -> list[dict] return type"
