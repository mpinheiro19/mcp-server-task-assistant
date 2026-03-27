import json
from unittest.mock import AsyncMock, patch

import pytest

import mcp_assistant.resources.flow as flow_module
import mcp_assistant.tools.elicitation as elicitation_module
from mcp_assistant.tools.elicitation import (
    RepositoryContext,
    _extract_answers,
    _parse_questions,
    consolidate_technical_context,
    map_repository_context,
    run_expert_elicitation,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_repo(tmp_path):
    """Minimal fake repository with pyproject.toml."""
    repo = tmp_path / "my-project"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "my-project"\ndependencies = ["fastmcp"]'
    )
    (repo / "src").mkdir()
    (repo / "src" / "main.py").write_text("")
    return repo


@pytest.fixture()
def fake_dirs(tmp_path, sample_repo):
    """Patch ELICITATIONS_DIR and PROJECT_ROOT to tmp_path directories."""
    elicitations_dir = tmp_path / "elicitations"
    with (
        patch("mcp_assistant.tools.elicitation.ELICITATIONS_DIR", elicitations_dir),
        patch("mcp_assistant.tools.elicitation.PROJECT_ROOT", sample_repo),
        patch("mcp_assistant.tools.elicitation.ELICITATION_MAX_DEPTH", 3),
    ):
        yield {"elicitations": elicitations_dir, "root": sample_repo}


@pytest.fixture()
def mock_ctx():
    """Mock FastMCP Context with sample() returning 3 questions."""
    ctx = AsyncMock()
    ctx.sample = AsyncMock(
        return_value=AsyncMock(
            text="1. How does this integrate with existing modules?\n"
            "2. What backward compatibility constraints exist?\n"
            "3. What is the error handling strategy?"
        )
    )
    return ctx


# ---------------------------------------------------------------------------
# CaptureMCP helpers
# ---------------------------------------------------------------------------


class CaptureMCP:
    """Minimal mock that captures tools registered via mcp.tool(fn)."""

    def __init__(self):
        self.tools = {}

    def tool(self, fn=None):
        if fn is not None:
            self.tools[fn.__name__] = fn
            return fn

        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class CaptureResourceMCP:
    """Captures resources registered via @mcp.resource(uri)."""

    def __init__(self):
        self.resources = {}

    def resource(self, uri: str):
        def decorator(fn):
            self.resources[uri] = fn
            return fn

        return decorator


# ---------------------------------------------------------------------------
# map_repository_context
# ---------------------------------------------------------------------------


def test_map_returns_valid_context(fake_dirs, sample_repo):
    result = map_repository_context(str(sample_repo))
    assert isinstance(result, dict)
    assert "Python" in result["detected_stack"]
    assert "FastMCP" in result["detected_stack"]
    assert len(result["tree"]) > 0


def test_map_ignores_node_modules(fake_dirs, tmp_path):
    repo = tmp_path / "node-repo"
    repo.mkdir()
    (repo / "node_modules").mkdir()
    (repo / "node_modules" / "lodash.js").write_text("")
    (repo / "index.js").write_text("")
    result = map_repository_context(str(repo))
    assert not any("node_modules" in p for p in result["tree"])


def test_map_reads_pyproject_toml(fake_dirs, sample_repo):
    result = map_repository_context(str(sample_repo))
    assert "pyproject.toml" in result["manifests"]
    assert result["manifests"]["pyproject.toml"] != ""


def test_map_depth_limit(fake_dirs, tmp_path):
    repo = tmp_path / "deep-repo"
    repo.mkdir()
    deep = repo / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    (deep / "file.txt").write_text("")
    with patch("mcp_assistant.tools.elicitation.ELICITATION_MAX_DEPTH", 3):
        result = map_repository_context(str(repo))
    # depth 3 means parts count < 3, so a/b/c/d/file.txt (4 parts) should not appear
    assert not any("d" + "/" in p or p.endswith("/d") for p in result["tree"])
    assert not any("file.txt" in p and "a/b/c" in p for p in result["tree"])


def test_map_invalid_path_raises(fake_dirs):
    with pytest.raises(ValueError, match="does not exist or is not a directory"):
        map_repository_context("/nonexistent/path/xyz")


def test_map_defaults_to_codes_root(fake_dirs, sample_repo):
    result = map_repository_context("")
    assert result["root"] == str(sample_repo.resolve())


# ---------------------------------------------------------------------------
# run_expert_elicitation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_creates_elicitation_file(fake_dirs, mock_ctx):
    result = await run_expert_elicitation(mock_ctx, "My Feature", "Draft text")
    assert result["saved"] is True
    elicitation_path = fake_dirs["elicitations"] / result["filename"]
    assert elicitation_path.exists()
    assert result["filename"] == "my-feature.md"


@pytest.mark.asyncio
async def test_run_returns_sampling_used_true(fake_dirs, mock_ctx):
    result = await run_expert_elicitation(mock_ctx, "My Feature", "Draft text")
    assert result["sampling_used"] is True
    assert result["questions_count"] == 3


@pytest.mark.asyncio
async def test_run_fallback_on_sample_failure(fake_dirs, mock_ctx):
    mock_ctx.sample = AsyncMock(side_effect=Exception("sampling failed"))
    result = await run_expert_elicitation(mock_ctx, "My Feature", "Draft text")
    assert result["sampling_used"] is False
    assert result["saved"] is True
    assert (fake_dirs["elicitations"] / result["filename"]).exists()


@pytest.mark.asyncio
async def test_run_clamps_num_questions_min(fake_dirs, mock_ctx):
    mock_ctx.sample = AsyncMock(side_effect=Exception("fail"))
    result = await run_expert_elicitation(mock_ctx, "My Feature", "Draft", num_questions=1)
    assert result["questions_count"] >= 3


@pytest.mark.asyncio
async def test_run_clamps_num_questions_max(fake_dirs, mock_ctx):
    mock_ctx.sample = AsyncMock(side_effect=Exception("fail"))
    result = await run_expert_elicitation(mock_ctx, "My Feature", "Draft", num_questions=10)
    assert result["questions_count"] <= 7


@pytest.mark.asyncio
async def test_run_file_structure(fake_dirs, mock_ctx):
    result = await run_expert_elicitation(mock_ctx, "My Feature", "Draft text")
    content = (fake_dirs["elicitations"] / result["filename"]).read_text()
    assert "## Pending Questions" in content
    assert "## 📝 Answers" in content


@pytest.mark.asyncio
async def test_run_registers_in_index(fake_dirs, mock_ctx):
    await run_expert_elicitation(mock_ctx, "My Feature", "Draft text")
    index_path = fake_dirs["elicitations"] / "index.md"
    assert index_path.exists()
    assert "⏳ Pending" in index_path.read_text()


# ---------------------------------------------------------------------------
# consolidate_technical_context
# ---------------------------------------------------------------------------


def _make_elicitation_file(elicitations_dir, slug, root, answers=None):
    """Write a minimal elicitation file with optional filled-in answers."""
    elicitations_dir.mkdir(parents=True, exist_ok=True)
    q1 = "How does this integrate with existing modules?"
    q2 = "What is the error handling strategy?"

    answers_section = ""
    if answers:
        answers_section = "\n".join(f"**{i + 1}.** {q}\n> {a}" for i, (q, a) in enumerate(answers))
    else:
        answers_section = f"**1.** {q1}\n>\n\n**2.** {q2}\n>"

    content = f"""# Technical Elicitation: Test Feature

## Identified Architectural Context
- **Stack:** Python, FastMCP
- **Patterns:** Clean Architecture
- **Root:** {root}

## 🔍 Original PRD Draft
> Original PRD content here

## Pending Questions
1. {q1}
2. {q2}

## 📝 Answers
<!-- Fill in each answer below the corresponding question -->

{answers_section}
"""
    path = elicitations_dir / f"{slug}.md"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_consolidate_creates_context_file(fake_dirs, mock_ctx, sample_repo):
    mock_ctx.sample = AsyncMock(
        return_value=AsyncMock(text="## Summary\nConsolidated context.")
    )
    _make_elicitation_file(
        fake_dirs["elicitations"],
        "test-feature",
        str(sample_repo),
        answers=[("How does this integrate?", "Via the existing plugin interface."),
                 ("Error handling?", "Use structured exceptions.")],
    )
    result = await consolidate_technical_context(
        mock_ctx, "Test Feature", "test-feature.md"
    )
    assert result["saved"] is True
    assert (fake_dirs["elicitations"] / result["context_filename"]).exists()
    assert result["context_filename"] == "context-test-feature.md"


@pytest.mark.asyncio
async def test_consolidate_fails_on_empty_answers(fake_dirs, mock_ctx, sample_repo):
    _make_elicitation_file(fake_dirs["elicitations"], "no-answers", str(sample_repo))
    result = await consolidate_technical_context(
        mock_ctx, "No Answers", "no-answers.md"
    )
    assert result["saved"] is False
    assert "reason" in result
    assert "No answers found" in result["reason"]


@pytest.mark.asyncio
async def test_consolidate_fails_on_missing_file(fake_dirs, mock_ctx):
    fake_dirs["elicitations"].mkdir(parents=True, exist_ok=True)
    with pytest.raises(FileNotFoundError):
        await consolidate_technical_context(mock_ctx, "Missing", "missing.md")


@pytest.mark.asyncio
async def test_consolidate_path_traversal(fake_dirs, mock_ctx):
    fake_dirs["elicitations"].mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError, match="Invalid filename"):
        await consolidate_technical_context(
            mock_ctx, "Evil", "../../../etc/passwd"
        )


@pytest.mark.asyncio
async def test_consolidate_frontmatter_present(fake_dirs, mock_ctx, sample_repo):
    mock_ctx.sample = AsyncMock(
        return_value=AsyncMock(text="## Summary\nContext.")
    )
    _make_elicitation_file(
        fake_dirs["elicitations"],
        "with-fm",
        str(sample_repo),
        answers=[("Q1?", "A1."), ("Q2?", "A2.")],
    )
    result = await consolidate_technical_context(
        mock_ctx, "With Fm", "with-fm.md"
    )
    content = (fake_dirs["elicitations"] / result["context_filename"]).read_text()
    assert content.startswith("---")


@pytest.mark.asyncio
async def test_consolidate_sampling_used(fake_dirs, mock_ctx, sample_repo):
    mock_ctx.sample = AsyncMock(
        return_value=AsyncMock(text="## Summary\nLLM-generated context.")
    )
    _make_elicitation_file(
        fake_dirs["elicitations"],
        "sampling-test",
        str(sample_repo),
        answers=[("Q1?", "A1."), ("Q2?", "A2.")],
    )
    result = await consolidate_technical_context(
        mock_ctx, "Sampling Test", "sampling-test.md"
    )
    assert result["sampling_used"] is True


@pytest.mark.asyncio
async def test_consolidate_fallback(fake_dirs, mock_ctx, sample_repo):
    mock_ctx.sample = AsyncMock(side_effect=Exception("sampling unavailable"))
    _make_elicitation_file(
        fake_dirs["elicitations"],
        "fallback-test",
        str(sample_repo),
        answers=[("Q1?", "A1."), ("Q2?", "A2.")],
    )
    result = await consolidate_technical_context(
        mock_ctx, "Fallback Test", "fallback-test.md"
    )
    assert result["saved"] is True
    assert result["sampling_used"] is False


@pytest.mark.asyncio
async def test_consolidate_updates_index(fake_dirs, mock_ctx, sample_repo):
    mock_ctx.sample = AsyncMock(
        return_value=AsyncMock(text="## Summary\nContext.")
    )
    _make_elicitation_file(
        fake_dirs["elicitations"],
        "index-update",
        str(sample_repo),
        answers=[("Q1?", "A1."), ("Q2?", "A2.")],
    )
    await consolidate_technical_context(
        mock_ctx, "Index Update", "index-update.md"
    )
    index_path = fake_dirs["elicitations"] / "index.md"
    assert "✅ Consolidated" in index_path.read_text()


# ---------------------------------------------------------------------------
# MCP Resources (flow.py)
# ---------------------------------------------------------------------------


@pytest.fixture()
def flow_mcp_and_dirs(tmp_path):
    """Register flow resources with ELICITATIONS_DIR patched to tmp_path."""
    elicitations_dir = tmp_path / "elicitations"
    with patch("mcp_assistant.resources.flow.ELICITATIONS_DIR", elicitations_dir):
        mcp = CaptureResourceMCP()
        flow_module.register(mcp)
        yield mcp, elicitations_dir


def test_list_elicitations_empty(flow_mcp_and_dirs):
    mcp, elicitations_dir = flow_mcp_and_dirs
    fn = mcp.resources["flow://elicitations"]
    result = fn()
    assert result == "[]"


def test_list_elicitations_lists_files(flow_mcp_and_dirs):
    mcp, elicitations_dir = flow_mcp_and_dirs
    elicitations_dir.mkdir(parents=True, exist_ok=True)
    (elicitations_dir / "foo.md").write_text("content")
    (elicitations_dir / "context-foo.md").write_text("content")
    (elicitations_dir / "index.md").write_text("index")  # should NOT be listed
    fn = mcp.resources["flow://elicitations"]
    result = json.loads(fn())
    assert "foo.md" in result
    assert "context-foo.md" in result
    assert "index.md" not in result


def test_get_elicitation_returns_content(flow_mcp_and_dirs):
    mcp, elicitations_dir = flow_mcp_and_dirs
    elicitations_dir.mkdir(parents=True, exist_ok=True)
    (elicitations_dir / "bar.md").write_text("hello elicitation")
    fn = mcp.resources["flow://elicitation/{filename}"]
    result = fn("bar.md")
    assert result == "hello elicitation"


def test_get_elicitation_path_traversal(flow_mcp_and_dirs):
    mcp, elicitations_dir = flow_mcp_and_dirs
    elicitations_dir.mkdir(parents=True, exist_ok=True)
    fn = mcp.resources["flow://elicitation/{filename}"]
    with pytest.raises(ValueError, match="Invalid filename"):
        fn("../index.md")


def test_get_elicitation_not_found(flow_mcp_and_dirs):
    mcp, elicitations_dir = flow_mcp_and_dirs
    elicitations_dir.mkdir(parents=True, exist_ok=True)
    fn = mcp.resources["flow://elicitation/{filename}"]
    with pytest.raises(FileNotFoundError):
        fn("nonexistent.md")
