from unittest.mock import patch

import pytest

import mcp_assistant.prompts.templates as templates_module


class CaptureMCP:
    """Minimal mock that captures registered prompt functions by name."""

    def __init__(self):
        self.prompts = {}

    def prompt(self):
        def decorator(fn):
            self.prompts[fn.__name__] = fn
            return fn

        return decorator


@pytest.fixture()
def dirs(tmp_path):
    prds = tmp_path / "prds"
    specs = tmp_path / "specs"
    plans = tmp_path / "plans"
    spec_assistant = tmp_path / "spec-driven-assistant"
    index = tmp_path / "index.md"
    instructions = tmp_path / "copilot-instructions.md"

    prds.mkdir()
    specs.mkdir()
    plans.mkdir()
    spec_assistant.mkdir()

    return {
        "prds": prds,
        "specs": specs,
        "plans": plans,
        "spec_assistant": spec_assistant,
        "index": index,
        "instructions": instructions,
    }


@pytest.fixture()
def mcp_and_prompts(dirs):
    mcp = CaptureMCP()
    with (
        patch("mcp_assistant.prompts.templates.PRDS_DIR", dirs["prds"]),
        patch("mcp_assistant.prompts.templates.SPECS_DIR", dirs["specs"]),
        patch("mcp_assistant.prompts.templates.PLANS_DIR", dirs["plans"]),
        patch("mcp_assistant.prompts.templates.SPEC_ASSISTANT_DIR", dirs["spec_assistant"]),
        patch("mcp_assistant.prompts.templates.INDEX_FILE", dirs["index"]),
        patch("mcp_assistant.prompts.templates.COPILOT_INSTRUCTIONS", dirs["instructions"]),
    ):
        templates_module.register(mcp)
        yield mcp, dirs


# --- prd_from_idea ---


def test_prd_from_idea_returns_one_message(mcp_and_prompts):
    mcp, _ = mcp_and_prompts
    result = mcp.prompts["prd_from_idea"]("Add dark mode")
    assert len(result) == 1


def test_prd_from_idea_includes_idea_in_content(mcp_and_prompts):
    mcp, _ = mcp_and_prompts
    result = mcp.prompts["prd_from_idea"]("Add dark mode")
    assert "Add dark mode" in result[0].content.text


def test_prd_from_idea_includes_index_when_present(mcp_and_prompts):
    mcp, dirs = mcp_and_prompts
    dirs["index"].write_text("| PRD | Spec | Feature | Plan | Impl |\n| foo |")
    result = mcp.prompts["prd_from_idea"]("Anything")
    assert "foo" in result[0].content.text


def test_prd_from_idea_fallback_when_index_missing(mcp_and_prompts):
    mcp, _ = mcp_and_prompts
    result = mcp.prompts["prd_from_idea"]("Anything")
    assert "ainda não existe" in result[0].content.text


def test_prd_from_idea_injects_protocol_when_present(mcp_and_prompts):
    mcp, dirs = mcp_and_prompts
    dirs["instructions"].write_text("# Governance Rules")
    result = mcp.prompts["prd_from_idea"]("Anything")
    assert "Governance Rules" in result[0].content.text


# --- spec_from_prd ---


def test_spec_from_prd_raises_when_prd_missing(mcp_and_prompts):
    mcp, _ = mcp_and_prompts
    with pytest.raises(ValueError, match="não encontrado"):
        mcp.prompts["spec_from_prd"]("prd-missing.md")


def test_spec_from_prd_includes_prd_content(mcp_and_prompts):
    mcp, dirs = mcp_and_prompts
    (dirs["prds"] / "prd-foo.md").write_text("# My PRD\nSome content here.")
    result = mcp.prompts["spec_from_prd"]("prd-foo.md")
    assert len(result) == 1
    assert "My PRD" in result[0].content.text
    assert "Some content here" in result[0].content.text


def test_spec_from_prd_injects_tech_spec_template(mcp_and_prompts):
    mcp, dirs = mcp_and_prompts
    (dirs["prds"] / "prd-bar.md").write_text("# PRD Bar")
    (dirs["spec_assistant"] / "tech-spec-prompt.md").write_text("# Tech Spec Template")
    result = mcp.prompts["spec_from_prd"]("prd-bar.md")
    assert "Tech Spec Template" in result[0].content.text


# --- plan_from_spec ---


def test_plan_from_spec_raises_when_spec_missing(mcp_and_prompts):
    mcp, _ = mcp_and_prompts
    with pytest.raises(ValueError, match="não encontrada"):
        mcp.prompts["plan_from_spec"]("spec-missing.md")


def test_plan_from_spec_includes_spec_content(mcp_and_prompts):
    mcp, dirs = mcp_and_prompts
    (dirs["specs"] / "spec-foo.md").write_text("# My Spec\nDetails here.")
    result = mcp.prompts["plan_from_spec"]("spec-foo.md")
    assert len(result) == 1
    assert "My Spec" in result[0].content.text


def test_plan_from_spec_injects_example_plan_when_present(mcp_and_prompts):
    mcp, dirs = mcp_and_prompts
    (dirs["specs"] / "spec-foo.md").write_text("# Spec")
    (dirs["plans"] / "plan-example.md").write_text("# Example Plan Style")
    result = mcp.prompts["plan_from_spec"]("spec-foo.md")
    assert "Example Plan Style" in result[0].content.text


# --- review_artefact ---


def test_review_artefact_invalid_type_raises(mcp_and_prompts):
    mcp, _ = mcp_and_prompts
    with pytest.raises(ValueError, match="artefact_type inválido"):
        mcp.prompts["review_artefact"]("file.md", "unknown")


def test_review_artefact_missing_file_raises(mcp_and_prompts):
    mcp, _ = mcp_and_prompts
    with pytest.raises(ValueError, match="não encontrado"):
        mcp.prompts["review_artefact"]("prd-missing.md", "prd")


def test_review_artefact_prd_includes_content(mcp_and_prompts):
    mcp, dirs = mcp_and_prompts
    (dirs["prds"] / "prd-foo.md").write_text("# PRD to Review")
    result = mcp.prompts["review_artefact"]("prd-foo.md", "prd")
    assert len(result) == 1
    assert "PRD to Review" in result[0].content.text


def test_review_artefact_spec(mcp_and_prompts):
    mcp, dirs = mcp_and_prompts
    (dirs["specs"] / "spec-foo.md").write_text("# Spec to Review")
    result = mcp.prompts["review_artefact"]("spec-foo.md", "spec")
    assert "Spec to Review" in result[0].content.text


def test_review_artefact_plan(mcp_and_prompts):
    mcp, dirs = mcp_and_prompts
    (dirs["plans"] / "plan-foo.md").write_text("# Plan to Review")
    result = mcp.prompts["review_artefact"]("plan-foo.md", "plan")
    assert "Plan to Review" in result[0].content.text
