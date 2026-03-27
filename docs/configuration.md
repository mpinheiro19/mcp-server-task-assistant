# Configuration

## Quick Start

Clone the repo, then run:

```bash
bash scripts/setup.sh
```

This auto-detects the repo root and generates all client configs in `configs/`. Override
the defaults by setting env vars before running:

```bash
MCP_ASSISTANT_DIR=/path/to/mcp-assistant \
ASSISTANT_FLOW_ROOT=/path/to/Codes \
bash scripts/setup.sh
```

---

## Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MCP_ASSISTANT_DIR` | Git repo root (auto-detected) | Absolute path to the `mcp-assistant` project root. |
| `ASSISTANT_FLOW_ROOT` | `~/Codes` | Root directory that contains `copilot-assistants/`. |
| `ELICITATION_MAX_DEPTH` | `3` | Maximum directory depth when scanning a repository with `map_repository_context`. |

All path constants in `config.py` derive from `ASSISTANT_FLOW_ROOT`:

```python
COPILOT_ROOT    = CODES_ROOT / "copilot-assistants"
PRDS_DIR        = COPILOT_ROOT / "prds"
SPECS_DIR       = COPILOT_ROOT / "specs"
PLANS_DIR       = COPILOT_ROOT / "plans"
ELICITATIONS_DIR = COPILOT_ROOT / "elicitations"
INDEX_FILE      = COPILOT_ROOT / "index.md"
```

See [`.env.example`](../.env.example) for a reference of all configurable variables.

---

## Client Configuration

Config files in `configs/` are **generated** by `scripts/setup.sh` from `*.json.template`
sources. Edit the templates, not the JSON files.

Merge the generated file into your client's settings after running setup.

### Claude Code

Target file: `~/.claude/settings.json`

```json
{
  "mcpServers": {
    "assistant-flow": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/mcp-assistant", "mcp-assistant"],
      "env": {
        "ASSISTANT_FLOW_ROOT": "/absolute/path/to/Codes"
      }
    }
  }
}
```

See [`../configs/claude-code.json`](../configs/claude-code.json) for the generated snippet.

### Cursor

Target file: `.cursor/mcp.json` in your workspace root.

See [`../configs/cursor.json`](../configs/cursor.json).

### VS Code Copilot

Target file: `.vscode/mcp.json` in your workspace root.

See [`../configs/vscode-copilot.json`](../configs/vscode-copilot.json).

---

## Transport

The server uses **STDIO transport exclusively**. The client spawns the process and communicates over stdin/stdout. No ports are opened; no network access is required.

---

## Python Version

The project targets **Python 3.10+**. The pinned interpreter version is declared in `.python-version` for `uv` and `pyenv` compatibility.

---

## Dependency Management

Dependencies are managed with **uv**. The `uv.lock` file pins all transitive dependencies for reproducible installs.

```bash
# Install all dependencies (including dev)
uv sync

# Add a new dependency
uv add <package>

# Add a dev-only dependency
uv add --dev <package>
```

The only runtime dependency is `fastmcp>=3.1.1`. The `dev` group adds `pytest>=8.0` for testing.
