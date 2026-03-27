# VS Code Copilot Integration Example

This guide shows how to wire `mcp-assistant` into VS Code Copilot so that the
**Elicitation → PRD → Spec → Plan** tools are available directly inside chat and agent requests.

---

## Prerequisites

- VS Code 1.99+ with the **GitHub Copilot** extension
- `uv` installed and on your `PATH`
- This repository cloned somewhere on your machine

---

## Step 1 — Register the MCP Server

Create (or open) `.vscode/mcp.json` in your workspace root and add:

```json
{
  "servers": {
    "assistant-flow": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/mcp-assistant",
        "mcp-assistant"
      ],
      "env": {
        "ASSISTANT_FLOW_ROOT": "/absolute/path/to/Codes"
      }
    }
  }
}
```

Replace the two path placeholders:

| Placeholder | What to put here |
| :--- | :--- |
| `/absolute/path/to/mcp-assistant` | Absolute path to the cloned `mcp-assistant` folder |
| `/absolute/path/to/Codes` | Parent directory that contains your `copilot-assistants/` folder |

A pre-filled snippet for the default layout is available at
[`configs/vscode-copilot.json`](../configs/vscode-copilot.json).

---

## Step 2 — Verify the Server Starts

1. Open the **Command Palette** (`Ctrl+Shift+P`) and run **MCP: List Servers**.
2. `assistant-flow` should appear with status **Running**.
3. If it shows **Error**, open the Output panel → **MCP: assistant-flow** to read
   the server's stderr for diagnostic messages.

---

## Step 3 — Use the Tools in Copilot Chat

Open Copilot Chat (`Ctrl+Alt+I`) and switch to **Agent mode** (`@`). The tools
registered in `mcp-assistant` are injected automatically. Example interactions:

### Check for duplicate features before creating a PRD

```
@copilot check if there is already a PRD for "user authentication"
```

Copilot calls `check_duplicate("user authentication")` and reports any matches.

### Generate a new PRD from an idea

```
@copilot create a PRD for "offline mode support"
```

Copilot calls the `prd_from_idea` prompt, injecting the current governance
protocol and `index.md` state, then calls `create_prd` with the generated content.

### Advance a feature to "In Progress"

```
@copilot mark "Offline Mode" as in progress
```

Copilot calls `advance_stage("Offline Mode", "🟢 Done", "🔄 In Progress")` and
updates `index.md` in place.

### Review an artifact for compliance

```
@copilot review prd-offline-mode.md for compliance
```

Copilot calls `review_artefact("prd-offline-mode.md", "prd")`, which injects the
governance protocol and produces a structured compliance checklist.

---

## Step 4 — Explore Available Resources

Resources expose real-time filesystem state. You can ask Copilot to fetch them
directly:

```
@copilot what features are currently tracked in index.md?
```

This causes Copilot to read `flow://index` and summarise the table.

```
@copilot list all existing PRD files
```

This reads `flow://prds` and returns a sorted JSON array of filenames.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
| :--- | :--- | :--- |
| Server stays in "Starting" state | `uv` not found on `PATH` | Add `uv` to your shell profile and restart VS Code |
| `ASSISTANT_FLOW_ROOT` error | Wrong path in `mcp.json` | Verify the path contains a `copilot-assistants/` directory |
| Tools not appearing in chat | Agent mode not active | Switch chat mode to Agent (`@`) |
| `copilot-instructions.md not found` | `ASSISTANT_FLOW_ROOT` points to wrong directory | Check path — it must be the **parent** of `copilot-assistants/` |

---

## Environment Variables Reference

| Variable | Default | Description |
| :--- | :--- | :--- |
| `ASSISTANT_FLOW_ROOT` | `/home/mpinheiro19/Codes` | Root directory containing `copilot-assistants/` |

Override via `env` in `.vscode/mcp.json` to run on any machine without editing
source code.

---

## Related Guides

- [Configuration](configuration.md) — full client setup reference
- [Tools Reference](tools-reference.md) — all available tools with parameters
- [Resources Reference](resources-reference.md) — all `flow://` URIs
- [Prompts Reference](prompts-reference.md) — prompt templates and injected context
