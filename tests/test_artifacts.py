from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import mcp_assistant.config as config_module
import mcp_assistant.tools.artifacts as artifacts_module
from mcp_assistant.tools.artifacts import ElicitationChoice, IdeaDetails, _render_prd_draft
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
    assert result["filename"] == "minha-feature.md"
    assert (dirs["prds"] / "minha-feature.md").read_text() == "# PRD Content"


def test_create_prd_duplicate_raises(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    mcp.tools["create_prd"]("Minha Feature", "# PRD Content")
    with pytest.raises(ValueError, match="already exists"):
        mcp.tools["create_prd"]("Minha Feature", "# Another Content")


def test_create_spec(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    result = mcp.tools["create_spec"]("Sub Feature", "minha-feature.md", "# Spec")
    assert result["filename"] == "minha-feature/sub-feature.md"
    assert (dirs["specs"] / "minha-feature" / "sub-feature.md").exists()


def test_create_plan(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    result = mcp.tools["create_plan"]("Deploy Pipeline", "some-prd/deploy-pipeline.md", "# Plan")
    assert result["filename"] == "deploy-pipeline.prompt.md"
    assert (dirs["plans"] / "deploy-pipeline.prompt.md").read_text() == "# Plan"


def test_create_plan_duplicate_raises(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    mcp.tools["create_plan"]("Deploy Pipeline", "some-prd/deploy-pipeline.md", "# Plan")
    with pytest.raises(ValueError, match="already exists"):
        mcp.tools["create_plan"]("Deploy Pipeline", "some-prd/deploy-pipeline.md", "# Another Plan")


# ---------------------------------------------------------------------------
# Index integration tests
# ---------------------------------------------------------------------------


def test_create_prd_updates_index(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    mcp.tools["create_prd"]("My Feature", "# PRD Content")
    rows = _parse_index_table(dirs["index"].read_text())
    assert len(rows) == 1
    assert rows[0]["prd"] == "my-feature.md"
    assert rows[0]["plan_status"] == "⏳ Waiting for Spec"
    assert rows[0]["implementation"] == "❌ Todo"


def test_create_spec_updates_index(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    mcp.tools["create_prd"]("My Feature", "# PRD")
    mcp.tools["create_spec"]("Sub Feature", "my-feature.md", "# Spec")
    rows = _parse_index_table(dirs["index"].read_text())
    assert len(rows) == 1
    assert rows[0]["spec"] == "my-feature/sub-feature.md"
    assert rows[0]["plan_status"] == "🟡 Spec Draft"
    assert rows[0]["implementation"] == "❌ Todo"


def test_create_plan_updates_index(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    mcp.tools["create_prd"]("My Feature", "# PRD")
    mcp.tools["create_spec"]("Sub Feature", "my-feature.md", "# Spec")
    mcp.tools["create_plan"]("Sub Feature", "my-feature/sub-feature.md", "# Plan")
    rows = _parse_index_table(dirs["index"].read_text())
    assert len(rows) == 1
    assert rows[0]["plan_status"] == "🟢 Done"
    assert rows[0]["implementation"] == "❌ Todo"


def test_create_prd_index_failure_best_effort(mcp_and_tools):
    mcp, dirs = mcp_and_tools
    with patch("mcp_assistant.tools.artifacts._update_index", side_effect=OSError("disk full")):
        result = mcp.tools["create_prd"]("Fail Feature", "# PRD")
    assert result["filename"] == "fail-feature.md"
    assert (dirs["prds"] / "fail-feature.md").exists()
    assert "index_warning" in result
    assert "disk full" in result["index_warning"]


# ---------------------------------------------------------------------------
# _render_prd_draft helper tests
# ---------------------------------------------------------------------------


def _make_details(**overrides) -> IdeaDetails:
    defaults = {
        "problem_statement": "Users cannot log in",
        "target_audience": "End users",
        "success_metrics": "Login success rate > 99%",
        "scope_in": "OAuth2 flow",
    }
    return IdeaDetails(**{**defaults, **overrides})


def test_render_prd_draft_contains_required_sections():
    details = _make_details()
    draft = _render_prd_draft("Login Feature", details)
    assert "# PRD: Login Feature" in draft
    assert "## Problem Statement" in draft
    assert "## Target Audience" in draft
    assert "## Success Metrics" in draft
    assert "## Scope" in draft
    assert "## Priority" in draft


def test_render_prd_draft_optional_sections_omitted_when_empty():
    details = _make_details()
    draft = _render_prd_draft("My Feature", details)
    assert "## Constraints" not in draft
    assert "## Dependencies" not in draft
    assert "## Acceptance Criteria" not in draft
    assert "## Technical Notes" not in draft


def test_render_prd_draft_optional_sections_included_when_set():
    details = _make_details(
        constraints="Must be GDPR compliant",
        dependencies="Auth service",
        acceptance_criteria="All tests pass",
        technical_notes="Use JWT",
    )
    draft = _render_prd_draft("My Feature", details)
    assert "## Constraints" in draft
    assert "## Dependencies" in draft
    assert "## Acceptance Criteria" in draft
    assert "## Technical Notes" in draft


# ---------------------------------------------------------------------------
# ideate_prd unit tests (mock ctx)
# ---------------------------------------------------------------------------


def _accepted(data):
    """Create a minimal AcceptedElicitation-like mock."""
    m = MagicMock()
    m.action = "accept"
    m.data = data
    return m


def _cancelled():
    m = MagicMock()
    m.action = "cancel"
    return m


def _declined():
    m = MagicMock()
    m.action = "decline"
    return m


@pytest.fixture()
def mock_ctx():
    ctx = MagicMock()
    ctx.elicit = AsyncMock()
    ctx.sample = AsyncMock()
    ctx.info = AsyncMock()
    ctx.report_progress = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_ideate_prd_full_flow_returns_draft(mcp_and_tools, mock_ctx):
    mcp, dirs = mcp_and_tools
    mock_ctx.elicit.side_effect = [
        _accepted("My New Feature"),  # title
        _accepted(ElicitationChoice(run_elicitation=False)),  # choice: skip elicitation
        _accepted(  # details
            IdeaDetails(
                problem_statement="A problem",
                target_audience="Devs",
                success_metrics="metric",
                scope_in="everything",
            )
        ),
    ]
    sample_result = MagicMock()
    sample_result.text = "# PRD: My New Feature\n\n## User Stories\n- As a dev...\n\n## Risks & Mitigations\n...\n\n## Open Questions\n- [ ] TBD"
    mock_ctx.sample.return_value = sample_result
    result = await mcp.tools["ideate_prd"](mock_ctx)
    assert result["saved"] is True, "Draft should be auto-saved when no duplicate exists"
    assert result["feature_name"] == "My New Feature"
    assert result["sampling_used"] is True
    assert result["elicitation_used"] is False
    assert "draft" in result
    assert "filename" in result
    assert "path" in result
    assert dirs["prds"].exists() and list(dirs["prds"].glob("*.md"))


@pytest.mark.asyncio
async def test_ideate_prd_cancel_at_title(mcp_and_tools, mock_ctx):
    mcp, dirs = mcp_and_tools
    mock_ctx.elicit.side_effect = [_cancelled()]
    result = await mcp.tools["ideate_prd"](mock_ctx)
    assert result["saved"] is False
    assert "title" in result["reason"].lower()
    assert not dirs["prds"].exists() or not list(dirs["prds"].glob("*.md"))


@pytest.mark.asyncio
async def test_ideate_prd_decline_at_details(mcp_and_tools, mock_ctx):
    mcp, dirs = mcp_and_tools
    mock_ctx.elicit.side_effect = [
        _accepted("Feature X"),  # title
        _accepted(ElicitationChoice(run_elicitation=False)),  # choice: skip
        _declined(),  # details
    ]
    result = await mcp.tools["ideate_prd"](mock_ctx)
    assert result["saved"] is False
    assert "details" in result["reason"].lower()


@pytest.mark.asyncio
async def test_ideate_prd_duplicate_found_returns_error(mcp_and_tools, mock_ctx):
    """When a similar PRD exists the tool returns an error after the title step — no extra
    elicitation round-trip is triggered, keeping the request-ID counter below 2 and
    avoiding the VS Code tools/call ID collision."""
    mcp, dirs = mcp_and_tools
    # Create a related PRD (similar slug tokens)
    dirs["prds"].mkdir(parents=True, exist_ok=True)
    (dirs["prds"] / "dark-mode-beta.md").write_text("existing")

    mock_ctx.elicit.side_effect = [
        _accepted("Dark Mode"),  # title (id=0) — only elicitation that fires
    ]
    result = await mcp.tools["ideate_prd"](mock_ctx)
    assert result["saved"] is False
    assert "already exists" in result["reason"]
    assert mock_ctx.elicit.call_count == 1, "No additional elicitation after duplicate detected"


@pytest.mark.asyncio
async def test_ideate_prd_with_elicitation_enriches_prd(mcp_and_tools, mock_ctx):
    """When the user opts into pre-PRD elicitation, the PRD is generated with enriched context."""
    mcp, dirs = mcp_and_tools

    answers_mock = MagicMock()
    answers_mock.answer_1 = "The auth module"
    answers_mock.answer_2 = "Repository pattern"
    answers_mock.answer_3 = "No major risks"

    mock_ctx.elicit.side_effect = [
        _accepted("Elicited Feature"),  # title
        _accepted(ElicitationChoice(run_elicitation=True)),  # choice: run elicitation
        _accepted(answers_mock),  # discovery answers
        _accepted(  # details
            IdeaDetails(
                problem_statement="A problem",
                target_audience="Devs",
                success_metrics="metric",
                scope_in="everything",
            )
        ),
    ]

    questions_result = MagicMock()
    questions_result.text = (
        "1. How does this integrate?\n2. Any patterns to follow?\n3. Main risks?"
    )
    prd_result = MagicMock()
    prd_result.text = "# PRD: Elicited Feature\n\n## Problem Statement\nA problem"
    mock_ctx.sample.side_effect = [questions_result, prd_result]

    result = await mcp.tools["ideate_prd"](mock_ctx)
    assert result["saved"] is True
    assert result["elicitation_used"] is True
    assert result["feature_name"] == "Elicited Feature"
    assert dirs["prds"].exists() and list(dirs["prds"].glob("*.md"))


@pytest.mark.asyncio
async def test_ideate_prd_elicitation_declined_proceeds_without_enrichment(mcp_and_tools, mock_ctx):
    """When the user declines the discovery form, the PRD is still generated without enrichment."""
    mcp, dirs = mcp_and_tools

    mock_ctx.elicit.side_effect = [
        _accepted("Feature Y"),  # title
        _accepted(ElicitationChoice(run_elicitation=True)),  # choice: run elicitation
        _declined(),  # discovery answers: declined
        _accepted(  # details
            IdeaDetails(
                problem_statement="Some problem",
                target_audience="Users",
                success_metrics="Some metric",
                scope_in="In scope stuff",
            )
        ),
    ]

    questions_result = MagicMock()
    questions_result.text = "1. Integration?\n2. Patterns?\n3. Risks?"
    prd_result = MagicMock()
    prd_result.text = "# PRD: Feature Y"
    mock_ctx.sample.side_effect = [questions_result, prd_result]

    result = await mcp.tools["ideate_prd"](mock_ctx)
    assert result["saved"] is True
    assert result["elicitation_used"] is False
    assert result["feature_name"] == "Feature Y"
