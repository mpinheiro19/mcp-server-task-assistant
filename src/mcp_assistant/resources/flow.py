import json

from mcp_assistant.config import (
    CODES_ROOT,
    COPILOT_INSTRUCTIONS,
    INDEX_FILE,
    PLANS_DIR,
    PRDS_DIR,
    SPECS_DIR,
)


def register(mcp) -> None:
    @mcp.resource("flow://index")
    def get_index() -> str:
        """Current contents of index.md"""
        if not INDEX_FILE.exists():
            return "index.md not found."
        return INDEX_FILE.read_text()

    @mcp.resource("flow://copilot-instructions")
    def get_copilot_instructions() -> str:
        """Governance protocol (copilot-instructions.md)"""
        if not COPILOT_INSTRUCTIONS.exists():
            return "copilot-instructions.md not found."
        return COPILOT_INSTRUCTIONS.read_text()

    @mcp.resource("flow://projects")
    def get_projects() -> str:
        """List of projects in /Codes"""
        projects = [p.name for p in CODES_ROOT.iterdir() if p.is_dir()]
        return json.dumps(sorted(projects))

    @mcp.resource("flow://prds")
    def get_prds() -> str:
        """List of files in prds/"""
        if not PRDS_DIR.exists():
            return json.dumps([])
        files = [f.name for f in PRDS_DIR.glob("*.md")]
        return json.dumps(sorted(files))

    @mcp.resource("flow://specs")
    def get_specs() -> str:
        """List of files in specs/"""
        if not SPECS_DIR.exists():
            return json.dumps([])
        files = [f.name for f in SPECS_DIR.glob("*.md")]
        return json.dumps(sorted(files))

    @mcp.resource("flow://plans")
    def get_plans() -> str:
        """List of files in plans/"""
        if not PLANS_DIR.exists():
            return json.dumps([])
        files = [f.name for f in PLANS_DIR.glob("*.md")]
        return json.dumps(sorted(files))

    @mcp.resource("flow://prd/{filename}")
    def get_prd(filename: str) -> str:
        """Contents of a specific PRD"""
        path = PRDS_DIR / filename
        if not path.exists():
            raise ValueError(f"PRD '{filename}' not found")
        return path.read_text()

    @mcp.resource("flow://spec/{filename}")
    def get_spec(filename: str) -> str:
        """Contents of a specific Spec"""
        path = SPECS_DIR / filename
        if not path.exists():
            raise ValueError(f"Spec '{filename}' not found")
        return path.read_text()

    @mcp.resource("flow://plan/{filename}")
    def get_plan(filename: str) -> str:
        """Contents of a specific Plan"""
        path = PLANS_DIR / filename
        if not path.exists():
            raise ValueError(f"Plan '{filename}' not found")
        return path.read_text()
