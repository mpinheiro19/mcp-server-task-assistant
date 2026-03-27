import logging

from fastmcp import FastMCP

from mcp_assistant.config import log_config
from mcp_assistant.logging_config import setup_logging
from mcp_assistant.prompts import templates
from mcp_assistant.resources import flow
from mcp_assistant.tools import artifacts, elicitation, workflow

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="AssistantFlowServer",
    instructions="Manages the PRD→Spec→Plan cycle. Always check for duplicates before creating artifacts.",
)

artifacts.register(mcp)
elicitation.register(mcp)
workflow.register(mcp)
flow.register(mcp)
templates.register(mcp)


def main() -> None:
    setup_logging()
    log_config()
    logger.info(
        "server starting name=AssistantFlowServer "
        "modules=artifacts,elicitation,workflow,flow,templates"
    )
    mcp.run()
    logger.info("server stopped")


if __name__ == "__main__":
    main()
