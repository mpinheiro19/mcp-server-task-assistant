# Development Guide

## Prerequisites

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) package manager

## Setup

```bash
git clone <repo>
cd mcp-assistant
uv sync
```

This creates a `.venv` and installs all dependencies including the dev group.

---

## Project Layout

```
mcp-assistant/
├── src/mcp_assistant/   Package source (src layout)
├── tests/               pytest test suite
├── docs/                Documentation
├── configs/             Client configuration snippets
├── pyproject.toml       Project metadata and tool config
├── uv.lock              Pinned dependency lockfile
└── .python-version      Interpreter pin for uv/pyenv
```

The project uses the [src layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/), which ensures the installed package is always used in tests rather than the raw source directory.

---

## Running Tests

```bash
uv run pytest           # all tests
uv run pytest -v        # verbose output
uv run pytest tests/test_utils.py   # single file
```

The test suite is fast (<1 second) and fully offline — no network or real filesystem access. All path constants are patched to `tmp_path` fixtures.

### Test Coverage Areas

| File | Covers |
| :--- | :--- |
| `test_utils.py` | `_slugify` (accents, numbers, special chars) · `_parse_index_table` (happy path, empty, header-only) |
| `test_artifacts.py` | `create_prd/spec/plan` happy paths · duplicate detection |
| `test_workflow.py` | `get_workflow_status` · `advance_stage` (valid, invalid, not-found) · `check_duplicate` (no match, match) |

---

## Running the Server Locally

```bash
uv run mcp-assistant
```

The server starts in STDIO mode and waits for MCP messages. You will not see a prompt — the process is designed to be driven by a client. Press `Ctrl+C` to stop.

To test with a custom data root:

```bash
ASSISTANT_FLOW_ROOT=/path/to/your/Codes uv run mcp-assistant
```

---

## Adding a New Tool

1. Choose the appropriate module (`tools/artifacts.py` for creation, `tools/workflow.py` for state management).
2. Add the function inside the `register(mcp)` body, decorated with `@mcp.tool()`.
3. Import any new path constants from `mcp_assistant.config`.
4. Add tests in the corresponding `tests/test_*.py` file using the `CaptureMCP` mock pattern.

**Example:**

```python
# In tools/workflow.py, inside register(mcp):
@mcp.tool()
def reset_feature(feature_name: str) -> str:
    """Resets a feature row back to initial state."""
    ...
```

---

## Adding a New Resource

Add a function decorated with `@mcp.resource("flow://your-uri")` inside `resources/flow.py`'s `register(mcp)` body.

Resources should be **read-only** and return a `str` (or JSON-encoded string). See [`resources-reference.md`](resources-reference.md) for the existing resource catalogue.

---

## Code Style

- No formatter is enforced at this time; follow the existing style (PEP 8, 100-char line limit).
- Type annotations are used on all public function signatures.
- Internal helpers are prefixed with `_` (e.g., `_slugify`, `_parse_index_table`).
- Each module's public surface is the `register(mcp)` function only; all tool/resource functions are defined as closures within it.

---

## Release

The package is built with `hatchling`. To build a wheel:

```bash
uv build
```

The entry point `mcp-assistant` (mapped to `mcp_assistant.server:main`) is declared in `pyproject.toml` and available after `uv sync`.
