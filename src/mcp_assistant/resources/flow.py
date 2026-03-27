import json
import logging

from mcp_assistant.config import (
    CODES_ROOT,
    COPILOT_INSTRUCTIONS,
    ELICITATIONS_DIR,
    INDEX_FILE,
    PLANS_DIR,
    PRDS_DIR,
    SPECS_DIR,
)

logger = logging.getLogger(__name__)


def register(mcp) -> None:
    @mcp.resource("flow://index")
    def get_index() -> str:
        """Current contents of index.md"""
        logger.debug("resource_access uri=flow://index path=%s", INDEX_FILE)
        if not INDEX_FILE.exists():
            logger.info("resource_miss uri=flow://index")
            return "index.md not found."
        return INDEX_FILE.read_text()

    @mcp.resource("flow://copilot-instructions")
    def get_copilot_instructions() -> str:
        """Governance protocol (copilot-instructions.md)"""
        logger.debug(
            "resource_access uri=flow://copilot-instructions path=%s", COPILOT_INSTRUCTIONS
        )
        if not COPILOT_INSTRUCTIONS.exists():
            logger.info("resource_miss uri=flow://copilot-instructions")
            return "copilot-instructions.md not found."
        return COPILOT_INSTRUCTIONS.read_text()

    @mcp.resource("flow://projects")
    def get_projects() -> str:
        """List of projects in /Codes"""
        logger.debug("resource_access uri=flow://projects root=%s", CODES_ROOT)
        projects = [p.name for p in CODES_ROOT.iterdir() if p.is_dir()]
        logger.debug("resource_projects count=%d", len(projects))
        return json.dumps(sorted(projects))

    @mcp.resource("flow://prds")
    def get_prds() -> str:
        """List of files in prds/"""
        logger.debug("resource_access uri=flow://prds path=%s", PRDS_DIR)
        if not PRDS_DIR.exists():
            return json.dumps([])
        files = [f.name for f in PRDS_DIR.glob("*.md")]
        logger.debug("resource_prds count=%d", len(files))
        return json.dumps(sorted(files))

    @mcp.resource("flow://specs")
    def get_specs() -> str:
        """List of files in specs/ (relative paths, e.g. prd-slug/spec-name.md)"""
        logger.debug("resource_access uri=flow://specs path=%s", SPECS_DIR)
        if not SPECS_DIR.exists():
            return json.dumps([])
        files = [str(f.relative_to(SPECS_DIR)) for f in SPECS_DIR.rglob("*.md")]
        logger.debug("resource_specs count=%d", len(files))
        return json.dumps(sorted(files))

    @mcp.resource("flow://plans")
    def get_plans() -> str:
        """List of files in plans/"""
        logger.debug("resource_access uri=flow://plans path=%s", PLANS_DIR)
        if not PLANS_DIR.exists():
            return json.dumps([])
        files = [f.name for f in PLANS_DIR.glob("*.md")]
        logger.debug("resource_plans count=%d", len(files))
        return json.dumps(sorted(files))

    @mcp.resource("flow://prd/{filename}")
    def get_prd(filename: str) -> str:
        """Contents of a specific PRD"""
        logger.debug("resource_access uri=flow://prd/%s", filename)
        path = PRDS_DIR / filename
        if not path.resolve().is_relative_to(PRDS_DIR.resolve()):
            logger.warning(
                "path_traversal_blocked uri=flow://prd requested=%s resolved=%s",
                filename,
                path.resolve(),
            )
            raise ValueError(f"Invalid filename: '{filename}'")
        if not path.exists():
            logger.info("resource_miss uri=flow://prd/%s", filename)
            raise ValueError(f"PRD '{filename}' not found")
        return path.read_text()

    @mcp.resource("flow://spec/{prd_slug}/{spec_name}")
    def get_spec(prd_slug: str, spec_name: str) -> str:
        """Contents of a specific Spec (accessed as prd-slug/spec-name.md)"""
        logger.debug("resource_access uri=flow://spec/%s/%s", prd_slug, spec_name)
        path = SPECS_DIR / prd_slug / spec_name
        if not path.resolve().is_relative_to(SPECS_DIR.resolve()):
            logger.warning(
                "path_traversal_blocked uri=flow://spec requested=%s/%s resolved=%s",
                prd_slug,
                spec_name,
                path.resolve(),
            )
            raise ValueError(f"Invalid path: '{prd_slug}/{spec_name}'")
        if not path.exists():
            logger.info("resource_miss uri=flow://spec/%s/%s", prd_slug, spec_name)
            raise ValueError(f"Spec '{prd_slug}/{spec_name}' not found")
        return path.read_text()

    @mcp.resource("flow://plan/{filename}")
    def get_plan(filename: str) -> str:
        """Contents of a specific Plan"""
        logger.debug("resource_access uri=flow://plan/%s", filename)
        path = PLANS_DIR / filename
        if not path.resolve().is_relative_to(PLANS_DIR.resolve()):
            logger.warning(
                "path_traversal_blocked uri=flow://plan requested=%s resolved=%s",
                filename,
                path.resolve(),
            )
            raise ValueError(f"Invalid filename: '{filename}'")
        if not path.exists():
            logger.info("resource_miss uri=flow://plan/%s", filename)
            raise ValueError(f"Plan '{filename}' not found")
        return path.read_text()

    @mcp.resource("flow://elicitations")
    def list_elicitations() -> str:
        """List all elicitation and context artifacts."""
        logger.debug("resource_access uri=flow://elicitations path=%s", ELICITATIONS_DIR)
        if not ELICITATIONS_DIR.exists():
            return json.dumps([])
        files = sorted(
            f.name
            for f in ELICITATIONS_DIR.iterdir()
            if f.is_file() and f.suffix == ".md" and f.name != "index.md"
        )
        logger.debug("resource_elicitations count=%d", len(files))
        return json.dumps(files)

    @mcp.resource("flow://elicitation/{filename}")
    def get_elicitation(filename: str) -> str:
        """Return the content of an elicitation or context artifact."""
        logger.debug("resource_access uri=flow://elicitation/%s", filename)
        path = ELICITATIONS_DIR / filename
        if not path.resolve().is_relative_to(ELICITATIONS_DIR.resolve()):
            logger.warning(
                "path_traversal_blocked uri=flow://elicitation requested=%s resolved=%s",
                filename,
                path.resolve(),
            )
            raise ValueError(f"Invalid filename: '{filename}'")
        if not path.exists():
            logger.info("resource_miss uri=flow://elicitation/%s", filename)
            raise FileNotFoundError(f"File not found: '{filename}'")
        return path.read_text(encoding="utf-8")
