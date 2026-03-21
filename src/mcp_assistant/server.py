from fastmcp import FastMCP

from mcp_assistant.prompts import templates
from mcp_assistant.resources import flow
from mcp_assistant.tools import artifacts, workflow

mcp = FastMCP(
    name="AssistantFlowServer",
    instructions="Manages the PRD→Spec→Plan cycle. Always check for duplicates before creating artifacts.",
)

artifacts.register(mcp)
workflow.register(mcp)
flow.register(mcp)
templates.register(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
