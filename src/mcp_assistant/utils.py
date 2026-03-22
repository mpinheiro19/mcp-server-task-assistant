import re
import unicodedata
from pathlib import Path

from mcp_assistant.config import CODES_ROOT

_MAX_README_CHARS = 3000
_MAX_CONFIG_CHARS = 1000
_MAX_TOTAL_CHARS = 5000


def _slugify(name: str) -> str:
    """'Internacionalização Completa' → 'internacionalizacao-completa'"""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    lower = ascii_str.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lower).strip("-")
    return slug


def _parse_index_table(text: str) -> list[dict]:
    """Parse the markdown table in index.md and return a list of row dicts."""
    features = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("| :") or line.startswith("| PRD"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 5:
            continue
        features.append(
            {
                "prd": cols[0],
                "spec": cols[1],
                "feature": cols[2],
                "plan_status": cols[3],
                "implementation": cols[4],
            }
        )
    return features


def _gather_workspace_context(project_path: str = "") -> str:
    """Collect lightweight workspace context for LLM-based PRD generation.

    Reads top-level directory listing, README.md, and the main config file
    (pyproject.toml or package.json) from the given project path.

    Args:
        project_path: Filesystem path to the project root. Falls back to
            ``CODES_ROOT`` if empty.

    Returns:
        A Markdown string with ``## Project Structure``, ``## README``, and
        ``## Config`` sections. Truncated to ~5 000 chars total.
    """
    root = Path(project_path) if project_path else CODES_ROOT
    if not root.is_dir():
        return ""

    sections: list[str] = []

    # Top-level listing (no recursion)
    try:
        entries = sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        listing = "\n".join(
            f"{'📁 ' if e.is_dir() else '📄 '}{e.name}" for e in entries
        )
        sections.append(f"## Project Structure\n```\n{listing}\n```")
    except OSError:
        pass

    # README
    readme = root / "README.md"
    if readme.is_file():
        content = readme.read_text(errors="replace")[:_MAX_README_CHARS]
        sections.append(f"## README\n{content}")

    # Main config file
    for cfg_name in ("pyproject.toml", "package.json"):
        cfg = root / cfg_name
        if cfg.is_file():
            content = cfg.read_text(errors="replace")[:_MAX_CONFIG_CHARS]
            sections.append(f"## Config ({cfg_name})\n```\n{content}\n```")
            break

    result = "\n\n".join(sections)
    return result[:_MAX_TOTAL_CHARS]
