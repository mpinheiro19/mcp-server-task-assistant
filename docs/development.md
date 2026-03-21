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

The test suite is fully offline — no network or real filesystem access. All path constants are patched to `tmp_path` fixtures.

### Test Coverage Areas

| File | Covers |
| :--- | :--- |
| `test_utils.py` | `_slugify` (accents, numbers, special chars) · `_parse_index_table` (happy path, empty, header-only) |
| `test_artifacts.py` | `create_prd/spec/plan` happy paths · duplicate detection |
| `test_workflow.py` | `get_workflow_status` · `advance_stage` (valid, invalid, not-found) · `check_duplicate` (no match, match) |
| `test_resources.py` | All `flow://` resource URIs (index, projects, prds, specs, plans, individual files) |
| `test_prompts.py` | Prompt template generation for all four prompt types |
| `api/test_app.py` | App factory · CORS allowed/blocked · health endpoint · auth flag |
| `api/test_artifacts.py` | POST `/api/v1/artifacts/{prds,specs,plans}` · GET `/api/v1/artifacts` · 409 duplicates |
| `api/test_workflow.py` | GET status · PUT index · PATCH stage · GET duplicates |
| `api/test_resources.py` | All resource read endpoints · 404 on missing files |
| `api/test_auth.py` | `/auth/login`, `/auth/callback`, `/auth/me`, `/auth/logout` with flag on and off |

---

## Running the Server Locally

**STDIO (MCP):**
```bash
uv run mcp-assistant
```

The server starts in STDIO mode and waits for MCP messages. You will not see a prompt — the process is designed to be driven by a client. Press `Ctrl+C` to stop.

**REST API:**
```bash
uv run mcp-assistant-api
# Listens on http://localhost:8000 by default
# OpenAPI: http://localhost:8000/docs
```

To test with a custom data root:

```bash
ASSISTANT_FLOW_ROOT=/path/to/your/Codes uv run mcp-assistant
ASSISTANT_FLOW_ROOT=/path/to/your/Codes uv run mcp-assistant-api
```

---

## Adding a New Tool

1. Choose the appropriate module (`tools/artifacts.py` for creation, `tools/workflow.py` for state management).
2. Define the function at **module level** (not inside `register`). FastMCP reads the docstring as the tool description.
3. Register it inside `register(mcp)` by calling `mcp.tool()(your_function)`.
4. Import any new path constants from `mcp_assistant.config`.
5. Add tests in the corresponding `tests/test_*.py` file using the `CaptureMCP` mock pattern.
6. If it should also be accessible via REST API, add a handler in `src/mcp_assistant/api/v1/`.

**Example:**

```python
# In tools/workflow.py, at module level:
def reset_feature(feature_name: str) -> str:
    """Resets a feature row back to initial state."""
    ...

# Inside register(mcp):
def register(mcp) -> None:
    ...
    mcp.tool()(reset_feature)
```

---

## Adding a New Resource

Define the function at **module level** in `resources/flow.py`, then register it inside `register(mcp)` using `mcp.resource("flow://your-uri")(your_function)`.

Resources should be **read-only** and return a `str` (or JSON-encoded string). See [`resources-reference.md`](resources-reference.md) for the existing resource catalogue.

---

## Code Style

- **Formatter:** `black` (100-char line limit). Run `uv run black src/ tests/` before committing.
- **Linter:** `ruff`. Run `uv run ruff check src/ tests/`.
- Type annotations are used on all public function signatures.
- Internal helpers are prefixed with `_` (e.g., `_slugify`, `_parse_index_table`).
- Tool and resource functions live at **module level**; `register(mcp)` is a thin wrapper that calls `mcp.tool()(fn)` / `mcp.resource(uri)(fn)`.

---

## Release

The package is built with `hatchling`. To build a wheel:

```bash
uv build
```

Two entry points are declared in `pyproject.toml` and available after `uv sync`:
- `mcp-assistant` → `mcp_assistant.server:main` (STDIO MCP server)
- `mcp-assistant-api` → `mcp_assistant.api_server:main` (FastAPI REST server)
