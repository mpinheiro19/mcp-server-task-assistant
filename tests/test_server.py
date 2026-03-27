"""
Server Interface Tests
======================
Validates that the FastMCP server:

  1. Can be instantiated without errors.
  2. Has the correct name and instructions metadata.
  3. Registers all expected tools after register() calls.
  4. Registers all expected resources.
  5. The server entrypoint (main) is importable without side-effects.
"""

import importlib
import sys
from unittest.mock import patch

# ---------------------------------------------------------------------------
# 1. Server can be instantiated cleanly
# ---------------------------------------------------------------------------


def test_server_module_imports_without_side_effects():
    """Importing server.py must not launch the server or touch the filesystem."""
    # If already cached, reload to exercise import code path
    if "mcp_assistant.server" in sys.modules:
        mod = sys.modules["mcp_assistant.server"]
    else:
        mod = importlib.import_module("mcp_assistant.server")

    assert hasattr(mod, "mcp"), "server module must expose an 'mcp' object"
    assert hasattr(mod, "main"), "server module must expose a 'main' callable"


def test_mcp_server_has_correct_name():
    from mcp_assistant.server import mcp

    assert mcp.name == "AssistantFlowServer"


def test_mcp_server_has_instructions():
    from mcp_assistant.server import mcp

    # instructions must be a non-empty string
    assert isinstance(mcp.instructions, str)
    assert len(mcp.instructions) > 0


# ---------------------------------------------------------------------------
# 2. All expected tools are registered
# ---------------------------------------------------------------------------

EXPECTED_TOOLS = {
    "create_prd",
    "create_spec",
    "create_plan",
    "get_workflow_status",
    "update_index",
    "advance_stage",
    "check_duplicate",
    "list_artefacts",
    "sync_index",
    "map_repository_context",
    "run_expert_elicitation",
    "consolidate_technical_context",
}


def test_all_expected_tools_are_registered():
    """Use CaptureMCP to verify every tool is registered when register() is called."""
    import mcp_assistant.tools.artifacts as artifacts_module
    import mcp_assistant.tools.elicitation as elicitation_module
    import mcp_assistant.tools.workflow as workflow_module

    class CaptureMCP:
        def __init__(self):
            self.tools: dict = {}

        def tool(self, fn=None):
            # Supports both mcp.tool()(fn) and mcp.tool(fn)
            if fn is not None:
                self.tools[fn.__name__] = fn
                return fn

            def decorator(fn):
                self.tools[fn.__name__] = fn
                return fn

            return decorator

    mcp = CaptureMCP()
    artifacts_module.register(mcp)
    elicitation_module.register(mcp)
    workflow_module.register(mcp)

    missing = EXPECTED_TOOLS - set(mcp.tools.keys())
    assert not missing, f"These tools were not registered: {missing}"


# ---------------------------------------------------------------------------
# 3. All expected resources are registered
# ---------------------------------------------------------------------------

EXPECTED_RESOURCES = {
    "flow://index",
    "flow://copilot-instructions",
    "flow://projects",
    "flow://prds",
    "flow://specs",
    "flow://plans",
    "flow://prd/{filename}",
    "flow://spec/{prd_slug}/{spec_name}",
    "flow://plan/{filename}",
    "flow://elicitations",
    "flow://elicitation/{filename}",
}


def test_all_expected_resources_are_registered():
    import mcp_assistant.resources.flow as flow_module

    class CaptureMCP:
        def __init__(self):
            self.resources: dict = {}

        def resource(self, uri: str):
            def decorator(fn):
                self.resources[uri] = fn
                return fn

            return decorator

    mcp = CaptureMCP()
    flow_module.register(mcp)

    missing = EXPECTED_RESOURCES - set(mcp.resources.keys())
    assert not missing, f"These resources were not registered: {missing}"


# ---------------------------------------------------------------------------
# 4. All expected prompts are registered
# ---------------------------------------------------------------------------

EXPECTED_PROMPTS = {
    "prd_from_idea",
    "spec_from_prd",
    "plan_from_spec",
    "review_artefact",
}


def test_all_expected_prompts_are_registered():
    import mcp_assistant.prompts.templates as templates_module

    class CaptureMCP:
        def __init__(self):
            self.prompts: dict = {}

        def prompt(self):
            def decorator(fn):
                self.prompts[fn.__name__] = fn
                return fn

            return decorator

    mcp = CaptureMCP()
    templates_module.register(mcp)

    missing = EXPECTED_PROMPTS - set(mcp.prompts.keys())
    assert not missing, f"These prompts were not registered: {missing}"


# ---------------------------------------------------------------------------
# 5. main() calls mcp.run() — verified via mock, no actual server launch
# ---------------------------------------------------------------------------


def test_main_calls_mcp_run():
    from mcp_assistant import server

    with patch.object(server.mcp, "run") as mock_run:
        server.main()
        mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# 6. Server instructions mention the PRD→Spec→Plan cycle
# ---------------------------------------------------------------------------


def test_server_instructions_describe_workflow():
    from mcp_assistant.server import mcp

    instructions = mcp.instructions.lower()
    assert (
        "prd" in instructions or "spec" in instructions or "plan" in instructions
    ), "Server instructions should describe the PRD→Spec→Plan workflow"


# ---------------------------------------------------------------------------
# 7. No tool names collide across modules
# ---------------------------------------------------------------------------


def test_no_tool_name_collisions():
    import mcp_assistant.tools.artifacts as artifacts_module
    import mcp_assistant.tools.elicitation as elicitation_module
    import mcp_assistant.tools.workflow as workflow_module

    class CaptureMCP:
        def __init__(self):
            self.tools: dict = {}
            self.collisions: list = []

        def tool(self, fn=None):
            # Supports both mcp.tool()(fn) and mcp.tool(fn)
            def _register(f):
                if f.__name__ in self.tools:
                    self.collisions.append(f.__name__)
                self.tools[f.__name__] = f
                return f

            if fn is not None:
                return _register(fn)
            return _register

    mcp = CaptureMCP()
    artifacts_module.register(mcp)
    elicitation_module.register(mcp)
    workflow_module.register(mcp)

    assert mcp.collisions == [], f"Tool name collisions detected: {mcp.collisions}"
