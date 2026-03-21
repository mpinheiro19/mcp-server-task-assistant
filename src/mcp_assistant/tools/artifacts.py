import re

from mcp_assistant.config import PLANS_DIR, PRDS_DIR, SPECS_DIR
from mcp_assistant.tools.workflow import (
    _get_index_row_by_prd,
    _get_index_row_by_spec,
    _update_index,
)
from mcp_assistant.utils import _slugify


def register(mcp) -> None:
    @mcp.tool()
    def create_prd(feature_name: str, content: str) -> dict:
        """
        Cria um novo arquivo PRD em prds/.
        Slugifica feature_name → prd-<slug>.md. Verifica duplicata antes de criar.
        Registra automaticamente o artefato no index.md após a criação.
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

        result: dict = {"filename": filename, "path": str(path)}
        try:
            _update_index(filename, "", feature_name, "⏳ Waiting for Spec", "❌ Todo")
        except Exception as exc:
            result["index_warning"] = str(exc)
        return result

    @mcp.tool()
    def create_spec(feature_name: str, prd_filename: str, content: str) -> dict:
        """
        Cria um novo arquivo Spec em specs/.
        Nome: spec-<prd-slug>-<feature-slug>.md
        Atualiza o index.md: preenche spec_filename e muda plan_status para '🟡 Spec Draft'.
        Preserva o implementation_status existente.
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

        result: dict = {"filename": filename, "path": str(path)}
        try:
            existing = _get_index_row_by_prd(prd_filename)
            impl = existing["implementation"] if existing else "❌ Todo"
            _update_index(prd_filename, filename, feature_name, "🟡 Spec Draft", impl)
        except Exception as exc:
            result["index_warning"] = str(exc)
        return result

    @mcp.tool()
    def create_plan(feature_name: str, spec_filename: str, content: str) -> dict:
        """
        Cria um novo arquivo Plan em plans/.
        Nome: plan-<feature-slug>.prompt.md
        Atualiza o index.md: muda plan_status para '🟢 Done'. Preserva implementation_status.
        spec_filename é necessário para localizar a linha correta no index.md.
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

        result: dict = {"filename": filename, "path": str(path)}
        try:
            existing = _get_index_row_by_spec(spec_filename)
            if existing:
                _update_index(
                    existing["prd"],
                    spec_filename,
                    existing["feature"],
                    "🟢 Done",
                    existing["implementation"],
                )
            else:
                result["index_warning"] = (
                    f"Spec '{spec_filename}' não encontrada no index.md; " "entrada não atualizada."
                )
        except Exception as exc:
            result["index_warning"] = str(exc)
        return result
