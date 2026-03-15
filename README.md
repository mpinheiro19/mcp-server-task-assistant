# mcp-assistant

MCP server that manages the **PRD → Spec → Plan** artifact lifecycle for software projects.
Exposes tools, resources, and prompt templates consumed by Claude Code, Cursor, and VS Code Copilot via STDIO transport.

## Quick Start

```bash
uv sync
uv run mcp-assistant
```

The server starts in STDIO mode. Configure your client to spawn it — see [Configuration](docs/configuration.md).

## What It Does

| Capability | Description |
| :--- | :--- |
| **Tools** | Create PRDs, Specs, and Plans; manage `index.md` status; inspect for duplicates |
| **Resources** | Read-only `flow://*` URIs exposing filesystem state |
| **Prompts** | Context-rich LLM prompt templates for authoring and reviewing artifacts |

## Documentation

| Document | Contents |
| :--- | :--- |
| [Architecture](docs/architecture.md) | Module layout, registration pattern, data model, error strategy |
| [Tools Reference](docs/tools-reference.md) | All tools with parameters, return types, and examples |
| [Resources Reference](docs/resources-reference.md) | All `flow://*` resource URIs |
| [Prompts Reference](docs/prompts-reference.md) | Prompt templates and their injected context |
| [Configuration](docs/configuration.md) | Environment variables, client setup (Claude Code / Cursor / Copilot) |
| [Development](docs/development.md) | Setup, testing, adding new tools, release |

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- `fastmcp >= 3.1.1`

## License

MIT
