from fastmcp import FastMCP

from mcp_assistant.tools import artifacts, workflow
from mcp_assistant.resources import flow
from mcp_assistant.prompts import templates

mcp = FastMCP(
    name="AssistantFlowServer",
    instructions="Gerencia o ciclo PRD→Spec→Plan. Sempre verifique duplicatas antes de criar artefatos.",
)

artifacts.register(mcp)
workflow.register(mcp)
flow.register(mcp)
templates.register(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
