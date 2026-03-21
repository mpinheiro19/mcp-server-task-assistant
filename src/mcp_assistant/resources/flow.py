import json

from mcp_assistant.config import (
    CODES_ROOT,
    COPILOT_INSTRUCTIONS,
    INDEX_FILE,
    PLANS_DIR,
    PRDS_DIR,
    SPECS_DIR,
)


def get_index() -> str:
    """Conteúdo atual de index.md"""
    if not INDEX_FILE.exists():
        return "index.md não encontrado."
    return INDEX_FILE.read_text()


def get_copilot_instructions() -> str:
    """Protocolo de governança (copilot-instructions.md)"""
    if not COPILOT_INSTRUCTIONS.exists():
        return "copilot-instructions.md não encontrado."
    return COPILOT_INSTRUCTIONS.read_text()


def get_projects() -> str:
    """Lista de projetos em /Codes"""
    projects = [p.name for p in CODES_ROOT.iterdir() if p.is_dir()]
    return json.dumps(sorted(projects))


def get_prds() -> str:
    """Lista de arquivos em prds/"""
    if not PRDS_DIR.exists():
        return json.dumps([])
    files = [f.name for f in PRDS_DIR.glob("*.md")]
    return json.dumps(sorted(files))


def get_specs() -> str:
    """Lista de arquivos em specs/"""
    if not SPECS_DIR.exists():
        return json.dumps([])
    files = [f.name for f in SPECS_DIR.glob("*.md")]
    return json.dumps(sorted(files))


def get_plans() -> str:
    """Lista de arquivos em plans/"""
    if not PLANS_DIR.exists():
        return json.dumps([])
    files = [f.name for f in PLANS_DIR.glob("*.md")]
    return json.dumps(sorted(files))


def get_prd(filename: str) -> str:
    """Conteúdo de um PRD específico"""
    path = PRDS_DIR / filename
    if not path.exists():
        raise ValueError(f"PRD '{filename}' não encontrado")
    return path.read_text()


def get_spec(filename: str) -> str:
    """Conteúdo de uma Spec específica"""
    path = SPECS_DIR / filename
    if not path.exists():
        raise ValueError(f"Spec '{filename}' não encontrada")
    return path.read_text()


def get_plan(filename: str) -> str:
    """Conteúdo de um Plan específico"""
    path = PLANS_DIR / filename
    if not path.exists():
        raise ValueError(f"Plan '{filename}' não encontrado")
    return path.read_text()


def register(mcp) -> None:
    mcp.resource("flow://index")(get_index)
    mcp.resource("flow://copilot-instructions")(get_copilot_instructions)
    mcp.resource("flow://projects")(get_projects)
    mcp.resource("flow://prds")(get_prds)
    mcp.resource("flow://specs")(get_specs)
    mcp.resource("flow://plans")(get_plans)
    mcp.resource("flow://prd/{filename}")(get_prd)
    mcp.resource("flow://spec/{filename}")(get_spec)
    mcp.resource("flow://plan/{filename}")(get_plan)
