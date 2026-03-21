# MCP - Development Lifecycle Manager

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
[![codecov](https://codecov.io/gh/mpinheiro19/mcp-server-task-assistant/branch/main/graph/badge.svg)](https://codecov.io/gh/mpinheiro19/mcp-server-task-assistant)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![Pre-release](https://img.shields.io/github/v/release/mpinheiro19/mcp-server-task-assistant?include_prereleases&label=pre-release)

MCP server that manages the **PRD → Spec → Plan** artifact lifecycle for software projects.
Exposes tools, resources, and prompt templates via STDIO transport (consumed by Claude Code, Cursor, VS Code Copilot) and a standalone FastAPI REST API for browser and scripted clients.

## Quick Start

**STDIO (MCP clients — Claude Code, Cursor, VS Code Copilot):**
```bash
uv sync
uv run mcp-assistant
```

**REST API (HTTP clients, browsers, scripts):**
```bash
uv sync
uv run mcp-assistant-api
# → http://localhost:8000  |  docs at /docs
```

Configure the MCP client to spawn the STDIO server — see [Configuration](docs/configuration.md).
Configure CORS, auth and ports — see [REST API](docs/rest-api.md).

## Features

- 📝 Artifact lifecycle: PRD → Spec → Plan
- 🛠️ Exposes tools and prompt templates for LLM-based assistants
- 📂 Read-only resource URIs for filesystem state
- ⚡ Fast, stateless STDIO server (MCP transport)
- 🌐 FastAPI REST API with OpenAPI docs, CORS, and optional OAuth2
- 🧩 Integrates with Claude Code, Cursor, and VS Code Copilot

## What It Does

| Capability   | Description                                                                 |
| :---        | :---                                                                       |
| **Tools**   | Create PRDs, Specs, and Plans; manage `index.md` status; inspect for duplicates |
| **Resources** | Read-only `flow://*` URIs exposing filesystem state                        |
| **Prompts** | Context-rich LLM prompt templates for authoring and reviewing artifacts     |

## Documentation

| Document | Contents |
| :--- | :--- |
| [Architecture](docs/architecture.md) | Module layout, registration pattern, data model, error strategy |
| [Tools Reference](docs/tools-reference.md) | All tools with parameters, return types, and examples |
| [Resources Reference](docs/resources-reference.md) | All `flow://*` resource URIs |
| [Prompts Reference](docs/prompts-reference.md) | Prompt templates and their injected context |
| [Configuration](docs/configuration.md) | Environment variables, client setup (Claude Code / Cursor / Copilot) |
| [VS Code Integration](docs/vscode-integration.md) | Step-by-step guide: register server, use tools in Copilot Chat, troubleshoot |
| [REST API](docs/rest-api.md) | HTTP endpoints, auth, CORS, env vars, error format |
| [Development](docs/development.md) | Setup, testing, adding new tools, release |

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- `fastmcp >= 3.1.1` (STDIO server)
- `fastapi >= 0.110`, `uvicorn >= 0.29` (REST API)

## Example Usage

```bash
# Example: Starting the server (see Quick Start)
uv run mcp-assistant
```

## Contributing

Contributions are welcome! Please read the [Contributing Guide](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before opening issues or pull requests.

## Support

For questions, suggestions, or support, open an issue or start a discussion on GitHub.

## License

This project is licensed under the [MIT License](LICENSE).
