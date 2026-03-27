import logging
import re
import unicodedata
from pathlib import Path

from mcp_assistant.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

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
    """Parse the markdown table in index.md and return a list of row dicts.

    Supports both the legacy 5-column schema and the updated 6-column schema
    (with Elicitation column). Rows with 5 columns get elicitation="—" injected.
    """
    features = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("| :") or line.startswith("| PRD"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) == 5:
            features.append(
                {
                    "prd": cols[0],
                    "spec": cols[1],
                    "feature": cols[2],
                    "plan_status": cols[3],
                    "elicitation": "—",
                    "implementation": cols[4],
                }
            )
        elif len(cols) >= 6:
            features.append(
                {
                    "prd": cols[0],
                    "spec": cols[1],
                    "feature": cols[2],
                    "plan_status": cols[3],
                    "elicitation": cols[4],
                    "implementation": cols[5],
                }
            )
    schema = "5-col" if any(len(line.strip("|").split("|")) == 5 for line in text.splitlines() if line.strip().startswith("|") and not line.strip().startswith("| PRD") and not line.strip().startswith("| :")) else "6-col"
    logger.debug("_parse_index_table rows=%d schema=%s", len(features), schema)
    return features


def _migrate_index_header_if_needed(content: str) -> str:
    """If index.md has the 5-column header, replace with 6-column header."""
    old_header = "| PRD Source | Spec (File) | Feature | Plan Status | Implementation |"
    new_header = "| PRD Source | Spec (File) | Feature | Plan Status | Elicitation | Implementation |"
    old_sep = "| :--- | :--- | :--- | :--- | :--- |"
    new_sep = "| :--- | :--- | :--- | :--- | :--- | :--- |"
    migrated = content.replace(old_header, new_header).replace(old_sep, new_sep)
    if migrated != content:
        logger.info("index_header_migrated from=5-col to=6-col")
    return migrated


def _gather_workspace_context(project_path: str = "") -> str:
    """Collect lightweight workspace context for LLM-based PRD generation.

    Reads top-level directory listing, README.md, and the main config file
    (pyproject.toml or package.json) from the given project path.

    Args:
        project_path: Filesystem path to the project root. Falls back to
            ``PROJECT_ROOT`` if empty.

    Returns:
        A Markdown string with ``## Project Structure``, ``## README``, and
        ``## Config`` sections. Truncated to ~5 000 chars total.
    """
    root = Path(project_path) if project_path else PROJECT_ROOT
    if not root.is_dir():
        logger.debug("_gather_workspace_context root_not_found path=%s", root)
        return ""

    logger.debug("_gather_workspace_context root=%s", root)
    sections: list[str] = []

    # Top-level listing (no recursion)
    try:
        entries = sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        listing = "\n".join(f"{'📁 ' if e.is_dir() else '📄 '}{e.name}" for e in entries)
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
    truncated = result[:_MAX_TOTAL_CHARS]
    logger.debug(
        "_gather_workspace_context root=%s sections=%d chars=%d",
        root, len(sections), len(truncated),
    )
    return truncated
