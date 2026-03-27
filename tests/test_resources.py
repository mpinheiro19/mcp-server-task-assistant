import json
from contextlib import contextmanager
from unittest.mock import patch

import pytest

import mcp_assistant.resources.flow as flow_module


class CaptureMCP:
    """Minimal mock that captures registered resource functions by URI."""

    def __init__(self):
        self.resources = {}

    def resource(self, uri: str):
        def decorator(fn):
            self.resources[uri] = fn
            return fn

        return decorator


@contextmanager
def patched_flow(tmp_path):
    codes_root = tmp_path / "Codes"
    codes_root.mkdir()
    (codes_root / "project-a").mkdir()
    (codes_root / "project-b").mkdir()
    prds = tmp_path / "prds"
    specs = tmp_path / "specs"
    plans = tmp_path / "plans"
    index = tmp_path / "index.md"
    instructions = tmp_path / "copilot-instructions.md"

    with (
        patch("mcp_assistant.resources.flow.CODES_ROOT", codes_root),
        patch("mcp_assistant.resources.flow.INDEX_FILE", index),
        patch("mcp_assistant.resources.flow.COPILOT_INSTRUCTIONS", instructions),
        patch("mcp_assistant.resources.flow.PRDS_DIR", prds),
        patch("mcp_assistant.resources.flow.SPECS_DIR", specs),
        patch("mcp_assistant.resources.flow.PLANS_DIR", plans),
    ):
        yield {
            "codes_root": codes_root,
            "index": index,
            "instructions": instructions,
            "prds": prds,
            "specs": specs,
            "plans": plans,
        }


@pytest.fixture()
def mcp_and_dirs(tmp_path):
    with patched_flow(tmp_path) as dirs:
        mcp = CaptureMCP()
        flow_module.register(mcp)
        yield mcp, dirs


# --- flow://index ---


def test_get_index_missing(mcp_and_dirs):
    mcp, _ = mcp_and_dirs
    assert "not found" in mcp.resources["flow://index"]()


def test_get_index_returns_content(mcp_and_dirs):
    mcp, dirs = mcp_and_dirs
    dirs["index"].write_text("# Index Content")
    assert mcp.resources["flow://index"]() == "# Index Content"


# --- flow://copilot-instructions ---


def test_get_copilot_instructions_missing(mcp_and_dirs):
    mcp, _ = mcp_and_dirs
    assert "not found" in mcp.resources["flow://copilot-instructions"]()


def test_get_copilot_instructions_returns_content(mcp_and_dirs):
    mcp, dirs = mcp_and_dirs
    dirs["instructions"].write_text("# Protocol")
    assert mcp.resources["flow://copilot-instructions"]() == "# Protocol"


# --- flow://projects ---


def test_get_projects_returns_sorted_dirs(mcp_and_dirs):
    mcp, _ = mcp_and_dirs
    result = json.loads(mcp.resources["flow://projects"]())
    assert result == ["project-a", "project-b"]


# --- flow://prds, flow://specs, flow://plans ---


def test_get_prds_empty_when_dir_missing(mcp_and_dirs):
    mcp, _ = mcp_and_dirs
    assert json.loads(mcp.resources["flow://prds"]()) == []


def test_get_prds_lists_md_files(mcp_and_dirs):
    mcp, dirs = mcp_and_dirs
    dirs["prds"].mkdir()
    (dirs["prds"] / "foo.md").write_text("x")
    (dirs["prds"] / "bar.md").write_text("x")
    result = json.loads(mcp.resources["flow://prds"]())
    assert result == ["bar.md", "foo.md"]


def test_get_specs_empty_when_dir_missing(mcp_and_dirs):
    mcp, _ = mcp_and_dirs
    assert json.loads(mcp.resources["flow://specs"]()) == []


def test_get_plans_empty_when_dir_missing(mcp_and_dirs):
    mcp, _ = mcp_and_dirs
    assert json.loads(mcp.resources["flow://plans"]()) == []


def test_get_plans_lists_files(mcp_and_dirs):
    mcp, dirs = mcp_and_dirs
    dirs["plans"].mkdir()
    (dirs["plans"] / "abc.md").write_text("x")
    result = json.loads(mcp.resources["flow://plans"]())
    assert result == ["abc.md"]


# --- flow://prd/{filename}, flow://spec/{filename}, flow://plan/{filename} ---


def test_get_prd_returns_content(mcp_and_dirs):
    mcp, dirs = mcp_and_dirs
    dirs["prds"].mkdir()
    (dirs["prds"] / "foo.md").write_text("# PRD Foo")
    assert mcp.resources["flow://prd/{filename}"]("foo.md") == "# PRD Foo"


def test_get_prd_missing_raises(mcp_and_dirs):
    mcp, _ = mcp_and_dirs
    with pytest.raises(ValueError, match="not found"):
        mcp.resources["flow://prd/{filename}"]("missing.md")


def test_get_spec_returns_content(mcp_and_dirs):
    mcp, dirs = mcp_and_dirs
    (dirs["specs"] / "prd-slug").mkdir(parents=True)
    (dirs["specs"] / "prd-slug" / "spec-foo.md").write_text("# Spec Foo")
    assert (
        mcp.resources["flow://spec/{prd_slug}/{spec_name}"]("prd-slug", "spec-foo.md")
        == "# Spec Foo"
    )


def test_get_spec_missing_raises(mcp_and_dirs):
    mcp, dirs = mcp_and_dirs
    dirs["specs"].mkdir()
    with pytest.raises(ValueError, match="not found"):
        mcp.resources["flow://spec/{prd_slug}/{spec_name}"]("prd-slug", "missing.md")


def test_get_plan_returns_content(mcp_and_dirs):
    mcp, dirs = mcp_and_dirs
    dirs["plans"].mkdir()
    (dirs["plans"] / "foo.md").write_text("# Plan Foo")
    assert mcp.resources["flow://plan/{filename}"]("foo.md") == "# Plan Foo"


def test_get_plan_missing_raises(mcp_and_dirs):
    mcp, _ = mcp_and_dirs
    with pytest.raises(ValueError, match="not found"):
        mcp.resources["flow://plan/{filename}"]("missing.md")
