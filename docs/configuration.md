# Configuration

## Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `ASSISTANT_FLOW_ROOT` | `/home/mpinheiro19/Codes` | Root directory that contains `copilot-assistants/`. Override to run on a different machine or path. |

All path constants in `config.py` derive from this root:

```python
COPILOT_ROOT = CODES_ROOT / "copilot-assistants"
PRDS_DIR     = COPILOT_ROOT / "prds"
SPECS_DIR    = COPILOT_ROOT / "specs"
PLANS_DIR    = COPILOT_ROOT / "plans"
INDEX_FILE   = COPILOT_ROOT / "index.md"
```

---

## Client Configuration

Pre-built configuration snippets are available in `configs/`. Merge the relevant file into your client's settings.

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

See [`../configs/claude-code.json`](../configs/claude-code.json) for a copy-pasteable snippet with the default paths.

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
