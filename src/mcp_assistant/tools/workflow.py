from datetime import datetime
from pathlib import Path

from mcp_assistant.config import INDEX_FILE, PLANS_DIR, PRDS_DIR, SPECS_DIR
from mcp_assistant.utils import _parse_index_table, _slugify


def get_workflow_status() -> dict:
    """
    Retorna o status estruturado do index.md.
    readOnlyHint=True — não modifica arquivos.
    """
    if not INDEX_FILE.exists():
        return {"features": [], "summary": {"done": 0, "in_progress": 0, "todo": 0}}

    text = INDEX_FILE.read_text()
    features = _parse_index_table(text)

    done = sum(
        1 for f in features if "✅" in f["implementation"] or "Concluído" in f["implementation"]
    )
    in_progress = sum(1 for f in features if "🔄" in f["implementation"])
    todo = sum(1 for f in features if "❌" in f["implementation"])

    return {
        "features": features,
        "summary": {"done": done, "in_progress": in_progress, "todo": todo},
    }


def update_index(
    prd_filename: str,
    spec_filename: str,
    feature_name: str,
    plan_status: str,
    implementation_status: str,
) -> str:
    """
    Localiza linha por prd_filename na tabela do index.md ou adiciona nova linha.
    Preserva todas as outras linhas intactas. Retorna conteúdo atualizado.
    """
    header = "| PRD Origem | Spec (Arquivo) | Feature | Plan Status | Implementation |\n| :--- | :--- | :--- | :--- | :--- |"
    new_row = f"| {prd_filename} | {spec_filename} | {feature_name} | {plan_status} | {implementation_status} |"

    if not INDEX_FILE.exists():
        content = header + "\n" + new_row + "\n"
        INDEX_FILE.write_text(content)
        return content

    text = INDEX_FILE.read_text()
    lines = text.splitlines(keepends=True)
    updated = False
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if (
            stripped.startswith("|")
            and prd_filename in stripped
            and not stripped.startswith("| PRD")
            and not stripped.startswith("| :")
        ):
            new_lines.append(new_row + "\n")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(new_row + "\n")

    content = "".join(new_lines)
    INDEX_FILE.write_text(content)
    return content


def advance_stage(
    feature_name: str,
    plan_status: str,
    implementation_status: str,
) -> str:
    """
    Localiza linha por feature_name no index.md e atualiza os campos de status.

    plan_status válidos: '⏳ Waiting for Spec', '🟡 Spec Draft', '🟡 Pending', '🟢 Done'
    implementation_status válidos: '❌ Todo', '🔄 In Progress', '✅ Concluído'
    """
    valid_plan = {"⏳ Waiting for Spec", "🟡 Spec Draft", "🟡 Pending", "🟢 Done"}
    valid_impl = {"❌ Todo", "🔄 In Progress", "✅ Concluído"}

    if plan_status not in valid_plan:
        raise ValueError(f"plan_status inválido: '{plan_status}'. Válidos: {valid_plan}")
    if implementation_status not in valid_impl:
        raise ValueError(
            f"implementation_status inválido: '{implementation_status}'. Válidos: {valid_impl}"
        )

    if not INDEX_FILE.exists():
        raise FileNotFoundError("index.md não encontrado.")

    text = INDEX_FILE.read_text()
    lines = text.splitlines(keepends=True)
    new_lines = []
    updated = False

    for line in lines:
        stripped = line.strip()
        if (
            stripped.startswith("|")
            and feature_name in stripped
            and not stripped.startswith("| PRD")
            and not stripped.startswith("| :---")
        ):
            cols = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cols) >= 5:
                cols[3] = plan_status
                cols[4] = implementation_status
                new_line = "| " + " | ".join(cols) + " |\n"
                new_lines.append(new_line)
                updated = True
                continue
        new_lines.append(line)

    if not updated:
        raise ValueError(f"Feature '{feature_name}' não encontrada em index.md.")

    content = "".join(new_lines)
    INDEX_FILE.write_text(content)
    return content


def check_duplicate(feature_name: str) -> dict:
    """
    Verifica se já existe PRD, Spec ou Plan para feature_name.
    Busca por slug exato e também por tokens individuais do slug para cobrir
    arquivos com convenção camelCase ou slugs parcialmente diferentes.
    readOnlyHint=True — não modifica arquivos.
    """
    slug = _slugify(feature_name)
    tokens = [t for t in slug.split("-") if len(t) >= 4]

    def _glob_dir(directory: Path, patterns: list[str]) -> list[str]:
        if not directory.exists():
            return []
        found: set[Path] = set()
        for pat in patterns:
            found.update(directory.glob(pat))
        return sorted(str(p) for p in found)

    prd_patterns = [f"prd-{slug}*.md"] + [f"prd-*{t}*.md" for t in tokens]
    spec_patterns = [f"spec-*{slug}*.md"] + [f"spec-*{t}*.md" for t in tokens]
    plan_patterns = [f"plan-{slug}*.md"] + [f"plan-*{t}*.md" for t in tokens]

    matches = (
        _glob_dir(PRDS_DIR, prd_patterns)
        + _glob_dir(SPECS_DIR, spec_patterns)
        + _glob_dir(PLANS_DIR, plan_patterns)
    )
    seen: set[str] = set()
    unique_matches = [m for m in matches if not (m in seen or seen.add(m))]  # type: ignore[func-returns-value]

    return {"has_duplicate": len(unique_matches) > 0, "matches": unique_matches}


def list_artefacts(artefact_type: str) -> list[dict]:
    """
    Lista artefatos com filename, tamanho e data de modificação.
    artefact_type: 'prd' | 'spec' | 'plan' | 'all'
    """
    valid = {"prd", "spec", "plan", "all"}
    if artefact_type not in valid:
        raise ValueError(f"artefact_type inválido: '{artefact_type}'. Válidos: {valid}")

    dirs: dict[str, Path] = {"prd": PRDS_DIR, "spec": SPECS_DIR, "plan": PLANS_DIR}

    def _entries(directory: Path) -> list[dict]:
        if not directory.exists():
            return []
        result = []
        for f in sorted(directory.glob("*.md")):
            stat = f.stat()
            result.append(
                {
                    "filename": f.name,
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )
        return result

    if artefact_type == "all":
        return (
            [{"type": "prd", **e} for e in _entries(PRDS_DIR)]
            + [{"type": "spec", **e} for e in _entries(SPECS_DIR)]
            + [{"type": "plan", **e} for e in _entries(PLANS_DIR)]
        )

    return _entries(dirs[artefact_type])


def register(mcp) -> None:
    mcp.tool()(get_workflow_status)
    mcp.tool()(update_index)
    mcp.tool()(advance_stage)
    mcp.tool()(check_duplicate)
    mcp.tool()(list_artefacts)
