import logging
from datetime import datetime
from pathlib import Path

from mcp_assistant.config import INDEX_FILE, PLANS_DIR, PRDS_DIR, SPECS_DIR
from mcp_assistant.logging_config import log_operation
from mcp_assistant.utils import _migrate_index_header_if_needed, _parse_index_table, _slugify

logger = logging.getLogger(__name__)


_INDEX_HEADER = (
    "| PRD Source | Spec (File) | Feature | Plan Status | Elicitation | Implementation |\n"
    "| :--- | :--- | :--- | :--- | :--- | :--- |"
)


def _get_index_row_by_feature(feature_name: str) -> dict | None:
    """Return the index.md row matching feature_name (case-insensitive), or None."""
    if not INDEX_FILE.exists():
        return None
    rows = _parse_index_table(INDEX_FILE.read_text(encoding="utf-8"))
    feature_lower = feature_name.strip().lower()
    for row in rows:
        if row["feature"].strip().lower() == feature_lower:
            return row
    return None


def _update_index(
    prd_filename: str,
    spec_filename: str,
    feature_name: str,
    plan_status: str,
    implementation_status: str,
    elicitation_status: str = "—",
) -> str:
    """Upsert a row keyed by prd_filename in index.md.

    Creates the file with the 6-column schema if absent. Existing rows without
    an Elicitation column are preserved with "—". When elicitation_status is "—"
    and a row already exists with a non-default value, the existing value is kept.
    """
    existing = _get_index_row_by_prd(prd_filename)
    effective_elicitation = (
        existing["elicitation"]
        if existing and elicitation_status == "—"
        else elicitation_status
    )
    new_row = (
        f"| {prd_filename} | {spec_filename} | {feature_name} "
        f"| {plan_status} | {effective_elicitation} | {implementation_status} |"
    )

    if not INDEX_FILE.exists():
        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        content = _INDEX_HEADER + "\n" + new_row + "\n"
        INDEX_FILE.write_text(content)
        logger.debug("index_created path=%s prd=%s feature=%s", INDEX_FILE, prd_filename, feature_name)
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
    action = "updated" if updated else "inserted"
    logger.debug(
        "index_row_%s prd=%s feature=%s plan_status=%s impl=%s",
        action, prd_filename, feature_name, plan_status, implementation_status,
    )
    return content


def _get_index_row_by_prd(prd_filename: str) -> dict | None:
    """Return the index.md row whose PRD column matches prd_filename, or None."""
    if not INDEX_FILE.exists():
        return None
    for row in _parse_index_table(INDEX_FILE.read_text()):
        if row["prd"] == prd_filename:
            return row
    return None


def _get_index_row_by_spec(spec_filename: str) -> dict | None:
    """Return the index.md row whose Spec column matches spec_filename, or None."""
    if not INDEX_FILE.exists():
        return None
    for row in _parse_index_table(INDEX_FILE.read_text()):
        if row["spec"] == spec_filename:
            return row
    return None


def sync_index() -> dict:
    """
    Reconciles filesystem artifacts with index.md.

    Pass 1 — PRD files not yet in index are inserted with default statuses
             (plan_status='⏳ Waiting for Spec', implementation='❌ Todo').
    Pass 2 — Rows with an empty spec field are updated when a matching spec
             file exists on the filesystem; rows whose plan_status is not
             '🟢 Done' are updated when a matching plan file is found.

    Returns {"added": [...], "updated": [...], "skipped": [...]}.
    """
    logger.info("start op=sync_index")
    added: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []

    if INDEX_FILE.exists():
        migrated = _migrate_index_header_if_needed(INDEX_FILE.read_text())
        INDEX_FILE.write_text(migrated)
        logger.debug("sync_index header_migration_checked path=%s", INDEX_FILE)

    rows = _parse_index_table(INDEX_FILE.read_text()) if INDEX_FILE.exists() else []
    indexed_prds = {row["prd"] for row in rows}
    logger.debug("sync_index pass=1 existing_rows=%d", len(rows))

    if PRDS_DIR.exists():
        for prd_file in sorted(PRDS_DIR.glob("*.md")):
            fname = prd_file.name
            if fname not in indexed_prds:
                feature_name = fname.removesuffix(".md").replace("-", " ").title()
                _update_index(fname, "", feature_name, "⏳ Waiting for Spec", "❌ Todo")
                added.append(fname)
                logger.info("sync_index pass=1 added prd=%s", fname)

    rows = _parse_index_table(INDEX_FILE.read_text()) if INDEX_FILE.exists() else []
    logger.debug("sync_index pass=2 rows=%d", len(rows))

    for row in rows:
        prd_slug = row["prd"].removesuffix(".md")

        if not row["spec"] and SPECS_DIR.exists():
            matching = list(SPECS_DIR.glob(f"{prd_slug}/*.md"))
            if matching:
                spec_file = matching[0]
                spec_fname = str(spec_file.relative_to(SPECS_DIR))
                feature_slug = spec_file.stem
                plan_fname = f"{feature_slug}.prompt.md"
                has_plan = PLANS_DIR.exists() and (PLANS_DIR / plan_fname).exists()
                plan_status = "🟢 Done" if has_plan else "🟡 Spec Draft"
                _update_index(
                    row["prd"],
                    spec_fname,
                    row["feature"],
                    plan_status,
                    row["implementation"],
                    elicitation_status=row.get("elicitation", "—"),
                )
                updated.append(row["prd"])
                logger.info(
                    "sync_index pass=2 updated prd=%s spec=%s plan_status=%s",
                    row["prd"], spec_fname, plan_status,
                )
                continue

        if row["spec"] and row["plan_status"] != "🟢 Done" and PLANS_DIR.exists():
            feature_slug = Path(row["spec"]).stem
            plan_fname = f"{feature_slug}.prompt.md"
            if (PLANS_DIR / plan_fname).exists():
                _update_index(
                    row["prd"],
                    row["spec"],
                    row["feature"],
                    "🟢 Done",
                    row["implementation"],
                    elicitation_status=row.get("elicitation", "—"),
                )
                updated.append(row["prd"])
                logger.info(
                    "sync_index pass=2 plan_found prd=%s plan_status=🟢 Done", row["prd"]
                )
                continue

        skipped.append(row["prd"])
        logger.debug("sync_index pass=2 skipped prd=%s", row["prd"])

    logger.info(
        "end op=sync_index status=ok added=%d updated=%d skipped=%d",
        len(added), len(updated), len(skipped),
    )
    return {"added": added, "updated": updated, "skipped": skipped}


def register(mcp) -> None:
    @mcp.tool()
    def get_workflow_status() -> dict:
        """
        Returns the structured status from index.md.
        readOnlyHint=True — does not modify files.
        """
        with log_operation(logger, "get_workflow_status"):
            if not INDEX_FILE.exists():
                logger.info("get_workflow_status index_missing")
                return {"features": [], "summary": {"done": 0, "in_progress": 0, "todo": 0}}

            text = INDEX_FILE.read_text()
            features = _parse_index_table(text)

            done = sum(
                1 for f in features if "✅" in f["implementation"] or "Concluído" in f["implementation"]
            )
            in_progress = sum(1 for f in features if "🔄" in f["implementation"])
            todo = sum(1 for f in features if "❌" in f["implementation"])

            logger.info(
                "get_workflow_status rows=%d done=%d in_progress=%d todo=%d",
                len(features), done, in_progress, todo,
            )
            return {
                "features": features,
                "summary": {"done": done, "in_progress": in_progress, "todo": todo},
            }

    @mcp.tool()
    def update_index(
        prd_filename: str,
        spec_filename: str,
        feature_name: str,
        plan_status: str,
        implementation_status: str,
        elicitation_status: str = "—",
        force: bool = False,
    ) -> str:
        """
        Manually upserts a row in index.md. Requires force=True.

        index.md is managed automatically by create_prd, create_spec, and
        create_plan. Only call this tool directly when correcting data, and
        only with force=True to confirm the intent.
        """
        if not force:
            raise PermissionError(
                "update_index requires force=True. "
                "index.md is managed automatically by create_prd, create_spec, and create_plan."
            )
        logger.info(
            "update_index forced prd=%s spec=%s feature=%s plan_status=%s impl=%s",
            prd_filename, spec_filename, feature_name, plan_status, implementation_status,
        )
        return _update_index(
            prd_filename,
            spec_filename,
            feature_name,
            plan_status,
            implementation_status,
            elicitation_status=elicitation_status,
        )

    mcp.tool()(sync_index)

    @mcp.tool()
    def advance_stage(
        feature_name: str,
        plan_status: str,
        implementation_status: str,
    ) -> str:
        """
        Finds a row by feature_name in index.md and updates the status fields.

        Valid plan_status: '⏳ Waiting for Spec', '🟡 Spec Draft', '🟡 Pending', '🟢 Done'
        Valid implementation_status: '❌ Todo', '🔄 In Progress', '✅ Concluído'
        """
        valid_plan = {"⏳ Waiting for Spec", "🟡 Spec Draft", "🟡 Pending", "🟢 Done"}
        valid_impl = {"❌ Todo", "🔄 In Progress", "✅ Concluído"}

        if plan_status not in valid_plan:
            raise ValueError(f"Invalid plan_status: '{plan_status}'. Valid values: {valid_plan}")
        if implementation_status not in valid_impl:
            raise ValueError(
                f"Invalid implementation_status: '{implementation_status}'. Valid values: {valid_impl}"
            )

        row = _get_index_row_by_feature(feature_name)
        if row is None:
            logger.warning("advance_stage feature_not_found feature=%s", feature_name)
            raise ValueError(f"Feature '{feature_name}' not found in index.md.")

        logger.info(
            "advance_stage feature=%s plan_status=%s impl=%s",
            feature_name, plan_status, implementation_status,
        )
        return _update_index(
            prd_filename=row["prd"],
            spec_filename=row["spec"],
            feature_name=feature_name,
            plan_status=plan_status,
            implementation_status=implementation_status,
            elicitation_status=row["elicitation"],
        )

    @mcp.tool()
    def check_duplicate(feature_name: str) -> dict:
        """
        Checks if a PRD, Spec or Plan already exists for feature_name.
        Searches by exact slug and individual tokens to cover
        camelCase conventions or partially different slugs.
        readOnlyHint=True — does not modify files.
        """
        logger.debug("check_duplicate feature=%s", feature_name)
        slug = _slugify(feature_name)
        tokens = [t for t in slug.split("-") if len(t) >= 4]

        def _glob_dir(directory: Path, patterns: list[str]) -> list[str]:
            if not directory.exists():
                return []
            found: set[Path] = set()
            for pat in patterns:
                found.update(directory.glob(pat))
            return sorted(str(p) for p in found)

        prd_patterns = [f"{slug}*.md"] + [f"*{t}*.md" for t in tokens]
        spec_patterns = [f"*/{slug}*.md"] + [f"*/*{t}*.md" for t in tokens]
        plan_patterns = [f"{slug}*.prompt.md"] + [f"*{t}*.prompt.md" for t in tokens]

        matches = (
            _glob_dir(PRDS_DIR, prd_patterns)
            + _glob_dir(SPECS_DIR, spec_patterns)
            + _glob_dir(PLANS_DIR, plan_patterns)
        )
        seen: set[str] = set()
        unique_matches = [m for m in matches if not (m in seen or seen.add(m))]  # type: ignore[func-returns-value]

        has_dup = len(unique_matches) > 0
        if has_dup:
            logger.info(
                "check_duplicate feature=%s has_duplicate=True matches=%d",
                feature_name, len(unique_matches),
            )
        else:
            logger.debug("check_duplicate feature=%s has_duplicate=False", feature_name)

        return {"has_duplicate": has_dup, "matches": unique_matches}

    @mcp.tool()
    def list_artefacts(artefact_type: str) -> list[dict]:
        """
        Lists artifacts with filename, size and modification date.
        artefact_type: 'prd' | 'spec' | 'plan' | 'all'
        """
        logger.debug("list_artefacts type=%s", artefact_type)
        valid = {"prd", "spec", "plan", "all"}
        if artefact_type not in valid:
            raise ValueError(f"Invalid artefact_type: '{artefact_type}'. Valid values: {valid}")

        dirs: dict[str, Path] = {"prd": PRDS_DIR, "spec": SPECS_DIR, "plan": PLANS_DIR}

        def _entries(directory: Path, recursive: bool = False) -> list[dict]:
            if not directory.exists():
                return []
            result = []
            files = sorted(directory.rglob("*.md") if recursive else directory.glob("*.md"))
            for f in files:
                if not f.is_file():
                    continue
                stat = f.stat()
                result.append(
                    {
                        "filename": str(f.relative_to(directory)) if recursive else f.name,
                        "size_bytes": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )
            return result

        if artefact_type == "all":
            result = (
                [{"type": "prd", **e} for e in _entries(PRDS_DIR)]
                + [{"type": "spec", **e} for e in _entries(SPECS_DIR, recursive=True)]
                + [{"type": "plan", **e} for e in _entries(PLANS_DIR)]
            )
            logger.info("list_artefacts type=all count=%d", len(result))
            return result

        if artefact_type == "spec":
            result = _entries(SPECS_DIR, recursive=True)
            logger.info("list_artefacts type=spec count=%d", len(result))
            return result

        result = _entries(dirs[artefact_type])
        logger.info("list_artefacts type=%s count=%d", artefact_type, len(result))
        return result
