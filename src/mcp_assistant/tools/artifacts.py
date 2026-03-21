import re

from mcp_assistant.config import PLANS_DIR, PRDS_DIR, SPECS_DIR
from mcp_assistant.utils import _slugify


def create_prd(feature_name: str, content: str) -> dict:
    """
    Cria um novo arquivo PRD em prds/.
    Slugifica feature_name → prd-<slug>.md. Verifica duplicata antes de criar.
    """
    slug = _slugify(feature_name)
    filename = f"prd-{slug}.md"
    path = PRDS_DIR / filename

    if path.exists():
        raise ValueError(
            f"PRD '{filename}' já existe. Use um nome diferente ou incremente a versão."
        )

    PRDS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return {"filename": filename, "path": str(path)}


def create_spec(feature_name: str, prd_filename: str, content: str) -> dict:
    """
    Cria um novo arquivo Spec em specs/.
    Nome: spec-<prd-slug>-<feature-slug>.md
    """
    prd_slug = re.sub(r"^prd-", "", prd_filename.removesuffix(".md"))
    feature_slug = _slugify(feature_name)
    filename = f"spec-{prd_slug}-{feature_slug}.md"
    path = SPECS_DIR / filename

    if path.exists():
        raise ValueError(
            f"Spec '{filename}' já existe. Use um nome diferente ou incremente a versão."
        )

    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return {"filename": filename, "path": str(path)}


def create_plan(feature_name: str, content: str) -> dict:
    """
    Cria um novo arquivo Plan em plans/.
    Nome: plan-<feature-slug>.prompt.md
    """
    slug = _slugify(feature_name)
    filename = f"plan-{slug}.prompt.md"
    path = PLANS_DIR / filename

    if path.exists():
        raise ValueError(
            f"Plan '{filename}' já existe. Use um nome diferente ou incremente a versão."
        )

    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return {"filename": filename, "path": str(path)}


def register(mcp) -> None:
    mcp.tool()(create_prd)
    mcp.tool()(create_spec)
    mcp.tool()(create_plan)
