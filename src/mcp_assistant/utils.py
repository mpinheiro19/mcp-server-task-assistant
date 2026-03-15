import re
import unicodedata


def _slugify(name: str) -> str:
    """'Internacionalização Completa' → 'internacionalizacao-completa'"""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    lower = ascii_str.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lower).strip("-")
    return slug


def _parse_index_table(text: str) -> list[dict]:
    """Parseia tabela markdown do index.md retornando lista de dicts."""
    features = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("| :") or line.startswith("| PRD"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 5:
            continue
        features.append({
            "prd": cols[0],
            "spec": cols[1],
            "feature": cols[2],
            "plan_status": cols[3],
            "implementation": cols[4],
        })
    return features
