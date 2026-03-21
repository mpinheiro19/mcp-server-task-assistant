"""
End-to-End Flow Tests
=====================
Simulates the complete PRD → Spec → Plan lifecycle through the tool layer,
verifying:

  - Each tool returns a JSON-serialisable dict.
  - Return payloads contain the expected fields (filename, path, …).
  - Index state is consistent after every stage.
  - Workflow status reflects the correct summary after a full cycle.
  - All return values are compatible with what an LLM would forward to the
    JSON-RPC content layer (strings, numbers, bools — no Path objects, etc.).
"""

import json
from unittest.mock import patch

import pytest

import mcp_assistant.config as config_module
import mcp_assistant.tools.artifacts as artifacts_module
import mcp_assistant.tools.workflow as workflow_module
from mcp_assistant.utils import _parse_index_table

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class CaptureMCP:
    def __init__(self):
        self.tools: dict = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


@pytest.fixture()
def env(tmp_path):
    """Isolated filesystem + patched config for a clean end-to-end run."""
    prds = tmp_path / "prds"
    specs = tmp_path / "specs"
    plans = tmp_path / "plans"
    index = tmp_path / "index.md"

    patches = [
        patch.object(config_module, "PRDS_DIR", prds),
        patch.object(config_module, "SPECS_DIR", specs),
        patch.object(config_module, "PLANS_DIR", plans),
        patch("mcp_assistant.tools.artifacts.PRDS_DIR", prds),
        patch("mcp_assistant.tools.artifacts.SPECS_DIR", specs),
        patch("mcp_assistant.tools.artifacts.PLANS_DIR", plans),
        patch("mcp_assistant.tools.workflow.INDEX_FILE", index),
        patch("mcp_assistant.tools.workflow.PRDS_DIR", prds),
        patch("mcp_assistant.tools.workflow.SPECS_DIR", specs),
        patch("mcp_assistant.tools.workflow.PLANS_DIR", plans),
    ]
    for p in patches:
        p.start()

    mcp = CaptureMCP()
    artifacts_module.register(mcp)
    workflow_module.register(mcp)

    yield mcp, {
        "prds": prds,
        "specs": specs,
        "plans": plans,
        "index": index,
        "tools": mcp.tools,
    }

    for p in patches:
        p.stop()


# ---------------------------------------------------------------------------
# Helper: assert a value is JSON-serialisable (no Path, datetime unserialised…)
# ---------------------------------------------------------------------------


def _assert_json_serialisable(value, context: str = "") -> None:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        pytest.fail(
            f"Return value is not JSON-serialisable{' (' + context + ')' if context else ''}: {exc}"
        )


# ---------------------------------------------------------------------------
# 1. Full PRD → Spec → Plan lifecycle
# ---------------------------------------------------------------------------


def test_full_lifecycle_prd_spec_plan(env):
    mcp, d = env
    tools = d["tools"]

    # Stage 1 — create PRD
    prd_result = tools["create_prd"](
        "Payment Gateway", "# PRD: Payment Gateway\n\nEnable payments."
    )
    assert prd_result["filename"] == "prd-payment-gateway.md"
    _assert_json_serialisable(prd_result, "create_prd")

    rows = _parse_index_table(d["index"].read_text())
    assert rows[0]["plan_status"] == "⏳ Waiting for Spec"

    # Stage 2 — create Spec
    spec_result = tools["create_spec"](
        "Checkout Flow", "prd-payment-gateway.md", "# Spec: Checkout Flow"
    )
    assert spec_result["filename"] == "spec-payment-gateway-checkout-flow.md"
    _assert_json_serialisable(spec_result, "create_spec")

    rows = _parse_index_table(d["index"].read_text())
    assert rows[0]["plan_status"] == "🟡 Spec Draft"

    # Stage 3 — create Plan
    plan_result = tools["create_plan"](
        "Checkout Flow", "spec-payment-gateway-checkout-flow.md", "# Plan: Checkout Flow"
    )
    assert plan_result["filename"] == "plan-checkout-flow.prompt.md"
    _assert_json_serialisable(plan_result, "create_plan")

    rows = _parse_index_table(d["index"].read_text())
    assert rows[0]["plan_status"] == "🟢 Done"


# ---------------------------------------------------------------------------
# 2. Workflow status reflects full cycle correctly
# ---------------------------------------------------------------------------


def test_workflow_status_after_full_cycle(env):
    mcp, d = env
    tools = d["tools"]

    tools["create_prd"]("Feature A", "# PRD A")
    tools["create_spec"]("Sub A", "prd-feature-a.md", "# Spec A")
    tools["create_plan"]("Sub A", "spec-feature-a-sub-a.md", "# Plan A")
    # Mark Feature A as implemented so the 'done' counter picks it up
    tools["advance_stage"]("Sub A", "🟢 Done", "✅ Concluído")

    tools["create_prd"]("Feature B", "# PRD B")

    status = tools["get_workflow_status"]()
    _assert_json_serialisable(status, "get_workflow_status")

    assert status["summary"]["done"] == 1
    assert status["summary"]["todo"] == 1
    assert len(status["features"]) == 2


# ---------------------------------------------------------------------------
# 3. check_duplicate before creating avoids duplicates
# ---------------------------------------------------------------------------


def test_check_duplicate_guards_creation(env):
    mcp, d = env
    tools = d["tools"]

    assert tools["check_duplicate"]("Dark Mode")["has_duplicate"] is False

    tools["create_prd"]("Dark Mode", "# PRD")
    result = tools["check_duplicate"]("Dark Mode")
    assert result["has_duplicate"] is True
    _assert_json_serialisable(result, "check_duplicate")


# ---------------------------------------------------------------------------
# 4. advance_stage transitions are reflected in index
# ---------------------------------------------------------------------------


def test_advance_stage_full_transition(env):
    mcp, d = env
    tools = d["tools"]

    tools["create_prd"]("Dark Mode", "# PRD")
    d["index"].write_text(d["index"].read_text())  # no-op, ensure file is present

    tools["advance_stage"]("Dark Mode", "🟢 Done", "✅ Concluído")

    rows = _parse_index_table(d["index"].read_text())
    row = next(r for r in rows if "dark" in r["prd"].lower() or "dark" in r["feature"].lower())
    assert row["plan_status"] == "🟢 Done"
    assert row["implementation"] == "✅ Concluído"


# ---------------------------------------------------------------------------
# 5. list_artefacts returns JSON-serialisable structs with required fields
# ---------------------------------------------------------------------------


def test_list_artefacts_payload_shape(env):
    mcp, d = env
    tools = d["tools"]

    tools["create_prd"]("Shape Test", "# PRD")
    result = tools["list_artefacts"]("prd")

    assert len(result) == 1
    entry = result[0]
    _assert_json_serialisable(entry, "list_artefacts entry")
    assert "filename" in entry
    assert "size_bytes" in entry
    assert "modified_at" in entry
    assert isinstance(entry["size_bytes"], int)
    assert isinstance(entry["modified_at"], str)


def test_list_artefacts_all_payload_has_type_field(env):
    mcp, d = env
    tools = d["tools"]

    tools["create_prd"]("Multi", "# PRD")
    tools["create_spec"]("Part", "prd-multi.md", "# Spec")
    tools["create_plan"]("Part", "spec-multi-part.md", "# Plan")

    result = tools["list_artefacts"]("all")
    _assert_json_serialisable(result, "list_artefacts all")
    for entry in result:
        assert "type" in entry
        assert entry["type"] in {"prd", "spec", "plan"}


# ---------------------------------------------------------------------------
# 6. sync_index reconciles filesystem with index
# ---------------------------------------------------------------------------


def test_sync_index_full_reconciliation(env):
    mcp, d = env
    tools = d["tools"]

    # Create artifacts on disk without going through MCP tools
    d["prds"].mkdir(parents=True, exist_ok=True)
    d["specs"].mkdir(parents=True, exist_ok=True)
    d["plans"].mkdir(parents=True, exist_ok=True)
    (d["prds"] / "prd-orphan.md").write_text("# Orphan PRD")
    (d["specs"] / "spec-orphan-detail.md").write_text("# Orphan Spec")

    result = tools["sync_index"]()
    _assert_json_serialisable(result, "sync_index")
    assert "prd-orphan.md" in result["added"]


# ---------------------------------------------------------------------------
# 7. create_* tools return paths as strings, not Path objects
# ---------------------------------------------------------------------------


def test_create_prd_path_is_string(env):
    mcp, d = env
    result = d["tools"]["create_prd"]("String Path", "# PRD")
    assert isinstance(result["path"], str), "path field must be a str, not a Path"


def test_create_spec_path_is_string(env):
    mcp, d = env
    d["tools"]["create_prd"]("String Path", "# PRD")
    result = d["tools"]["create_spec"]("Detail", "prd-string-path.md", "# Spec")
    assert isinstance(result["path"], str)


def test_create_plan_path_is_string(env):
    mcp, d = env
    result = d["tools"]["create_plan"]("String Path", "spec-string-path.md", "# Plan")
    assert isinstance(result["path"], str)
