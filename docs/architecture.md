# Architecture

## Overview

`mcp-assistant` is a Model Context Protocol (MCP) server that manages the **PRD → Spec → Plan** artifact lifecycle for software projects. It exposes tools, resources, and prompt templates consumed by MCP-compatible clients (Claude Code, Cursor, VS Code Copilot).

Transport is **STDIO only** — the server is spawned as a subprocess by the client and communicates over stdin/stdout.

---

## Module Map

```
src/mcp_assistant/
├── server.py          Entry point. Instantiates FastMCP and wires all modules.
├── config.py          Centralized path constants. Reads ASSISTANT_FLOW_ROOT env var.
├── utils.py           Pure helper functions (_slugify, _parse_index_table).
├── tools/
│   ├── artifacts.py   Artifact creation tools (create_prd, create_spec, create_plan).
│   └── workflow.py    Workflow management tools (check_duplicate, advance_stage, …).
├── resources/
│   └── flow.py        Read-only resources exposing filesystem state as flow://* URIs.
└── prompts/
    └── templates.py   Prompt templates that inject context for LLM-driven authoring.
```

---

## Registration Pattern

Each module exposes a single `register(mcp: FastMCP) -> None` function. `server.py` calls each one after creating the `FastMCP` instance:

```python
# server.py
mcp = FastMCP(name="AssistantFlowServer", instructions="…")

artifacts.register(mcp)
workflow.register(mcp)
flow.register(mcp)
templates.register(mcp)
```

This avoids circular imports and makes each module independently testable — tests inject a lightweight mock that captures decorated functions by name.

---

## Data Layer

The server has **no database**. All state lives in the `copilot-assistants/` directory tree:

```
copilot-assistants/
├── index.md                   Source-of-truth status table (Markdown)
├── copilot-instructions.md    Governance protocol injected into prompts
├── spec-driven-assistant/     Prompt templates on disk
├── prds/                      prd-<slug>.md
├── specs/                     spec-<prd-slug>-<feature-slug>.md
└── plans/                     plan-<slug>.prompt.md
```

`config.py` exposes `Path` constants for every directory/file. The root can be overridden via the `ASSISTANT_FLOW_ROOT` environment variable, making the server portable across machines.

---

## Slug Convention

All filenames are derived from human-readable names through `_slugify()`:

1. Unicode NFC normalization → ASCII transliteration
2. Lowercase
3. Non-alphanumeric runs → `-`
4. Strip leading/trailing dashes

Examples:

| Input | Slug |
| :--- | :--- |
| `"Auth & Authorization"` | `auth-authorization` |
| `"Internacionalização"` | `internacionalizacao` |
| `"Feature v2.0"` | `feature-v2-0` |

---

## Index Table Format

`index.md` tracks the status of every feature as a Markdown table:

```markdown
| PRD Origem | Spec (Arquivo) | Feature | Plan Status | Implementation |
| :--- | :--- | :--- | :--- | :--- |
| prd-auth.md | spec-auth-login.md | Login Flow | 🟢 Done | ✅ Concluído |
```

`_parse_index_table()` parses this into a list of dicts. Tools that update it operate line-by-line to preserve all formatting outside the target row.

---

## Error Strategy

- **Duplicate artifacts** → `ValueError` before any file is written.
- **Missing files** → `ValueError` or `FileNotFoundError` with a descriptive message.
- **Invalid enum arguments** (e.g., `plan_status`) → `ValueError` listing valid options.
- FastMCP surfaces these as structured MCP error responses to the client.

---

## Testing Approach

Tests use `unittest.mock.patch` to redirect `Path` constants to `tmp_path` fixtures. A minimal `CaptureMCP` mock captures decorated functions without requiring a live FastMCP instance, keeping tests fast and free of I/O side-effects.

See [`../tests/`](../tests/) for the full suite.
