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
│   ├── api/             API-level tests (ideate_prd, …)
│   └── tools/           Tool-level tests (elicitation, …)
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
| `test_utils.py` | `_slugify` (accents, numbers, special chars) · `_parse_index_table` (happy path, empty, header-only) · `_migrate_index_header_if_needed` |
| `test_artifacts.py` | `create_prd/spec/plan` happy paths · duplicate detection |
| `test_workflow.py` | `get_workflow_status` · `advance_stage` (valid, invalid, not-found) · `check_duplicate` (no match, match) · `sync_index` · `update_index` |
| `test_prompts.py` | `prd_from_idea` (with/without context_filename) · `spec_from_prd` · `plan_from_spec` · `review_artefact` |
| `test_resources.py` | All `flow://*` URIs including elicitation resources |
| `test_server.py` | Server instantiation and module registration |
| `test_e2e_flow.py` | End-to-end artifact lifecycle (create PRD → Spec → Plan → index state) |
| `test_security.py` | Path traversal guards on all file-reading tools and resources |
| `tools/test_elicitation.py` | `map_repository_context` · `run_expert_elicitation` · `consolidate_technical_context` (sampling and fallback paths) |
| `api/test_ideate_prd.py` | `ideate_prd` elicitation flow · duplicate handling · sampling fallback |

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

1. Choose the appropriate module:
   - `tools/artifacts.py` — artifact creation tools
   - `tools/workflow.py` — state management tools
   - `tools/elicitation.py` — pre-PRD elicitation tools
2. Add the function inside the `register(mcp)` body (or as a top-level function passed to `mcp.tool()` for sync tools).
3. Import any new path constants from `mcp_assistant.config`.
4. Add tests in the corresponding `tests/` file using the `CaptureMCP` mock pattern.

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

- Formatter: **black** (line length 100). Linter: **ruff**.
- Type annotations are used on all public function signatures.
- Internal helpers are prefixed with `_` (e.g., `_slugify`, `_parse_index_table`).
- Each module's public surface is the `register(mcp)` function only; tool/resource functions are defined as closures within it (exception: standalone sync functions like `map_repository_context` that are passed to `mcp.tool()` directly).

---

## Release

The package is built with `hatchling`. To build a wheel:

```bash
uv build
```

The entry point `mcp-assistant` (mapped to `mcp_assistant.server:main`) is declared in `pyproject.toml` and available after `uv sync`.
