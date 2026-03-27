# MCP - Development Lifecycle Manager

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
[![codecov](https://codecov.io/gh/mpinheiro19/mcp-server-task-assistant/branch/main/graph/badge.svg)](https://codecov.io/gh/mpinheiro19/mcp-server-task-assistant)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![Pre-release](https://img.shields.io/badge/pre--release-1.1.0b1-blue)

MCP server that manages the **Elicitation → PRD → Spec → Plan** artifact lifecycle for software projects.
Exposes tools, resources, and prompt templates consumed by Claude Code, Cursor, and VS Code Copilot via STDIO transport.

## Quick Start

```bash
uv sync
uv run mcp-assistant
```

The server starts in STDIO mode. Configure your client to spawn it — see [Configuration](docs/configuration.md).

## Features

- 🔍 Pre-PRD technical elicitation: repository scanning, architecture-aware question generation, and context consolidation
- 📝 Artifact lifecycle: Elicitation → PRD → Spec → Plan
- 🛠️ Exposes tools and prompt templates for LLM-based assistants
- 📂 Read-only resource URIs for filesystem state
- ⚡ Fast, stateless STDIO server
- 🧩 Integrates with Claude Code, Cursor, and VS Code Copilot

## What It Does

| Capability | Description |
| :--- | :--- |
| **Elicitation Tools** | Scan repositories, generate architecture-aware questions, consolidate answers into a technical context artifact |
| **Artifact Tools** | Create PRDs, Specs, and Plans; manage `index.md` status; inspect for duplicates |
| **Resources** | Read-only `flow://*` URIs exposing filesystem state, including elicitation artifacts |
| **Prompts** | Context-rich LLM prompt templates for authoring and reviewing artifacts; supports injecting enriched elicitation context into PRD generation |

## Workflow

```
run_expert_elicitation   →   (fill answers)   →   consolidate_technical_context
                                                          ↓
                                                  prd_from_idea(context_filename=…)
                                                          ↓
                                              create_prd → create_spec → create_plan
```

## Documentation

| Document | Contents |
| :--- | :--- |
| [Architecture](docs/architecture.md) | Module layout, registration pattern, data model, error strategy |
| [Tools Reference](docs/tools-reference.md) | All tools with parameters, return types, and examples |
| [Resources Reference](docs/resources-reference.md) | All `flow://*` resource URIs |
| [Prompts Reference](docs/prompts-reference.md) | Prompt templates and their injected context |
| [Configuration](docs/configuration.md) | Environment variables, client setup (Claude Code / Cursor / Copilot) |
| [VS Code Integration](docs/vscode-integration.md) | Step-by-step guide: register server, use tools in Copilot Chat, troubleshoot |
| [Development](docs/development.md) | Setup, testing, adding new tools, release |

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- `fastmcp >= 3.1.1`

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
