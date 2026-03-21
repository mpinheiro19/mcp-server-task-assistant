from datetime import datetime
from pathlib import Path

from mcp_assistant.config import INDEX_FILE, PLANS_DIR, PRDS_DIR, SPECS_DIR
from mcp_assistant.utils import _parse_index_table, _slugify


def _update_index(
    prd_filename: str,
    spec_filename: str,
    feature_name: str,
    plan_status: str,
    implementation_status: str,
) -> str:
    """Upsert a row keyed by prd_filename in index.md. Creates the file if absent."""
    header = (
        "| PRD Source | Spec (File) | Feature | Plan Status | Implementation |\n"
        "| :--- | :--- | :--- | :--- | :--- |"
    )
    new_row = (
        f"| {prd_filename} | {spec_filename} | {feature_name} "
        f"| {plan_status} | {implementation_status} |"
    )

    if not INDEX_FILE.exists():
        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
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
    added: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []

    rows = _parse_index_table(INDEX_FILE.read_text()) if INDEX_FILE.exists() else []
    indexed_prds = {row["prd"] for row in rows}

    if PRDS_DIR.exists():
        for prd_file in sorted(PRDS_DIR.glob("*.md")):
            fname = prd_file.name
            if fname not in indexed_prds:
                feature_name = (
                    fname.removeprefix("prd-").removesuffix(".md").replace("-", " ").title()
                )
                _update_index(fname, "", feature_name, "⏳ Waiting for Spec", "❌ Todo")
                added.append(fname)

    rows = _parse_index_table(INDEX_FILE.read_text()) if INDEX_FILE.exists() else []

    for row in rows:
        prd_slug = row["prd"].removeprefix("prd-").removesuffix(".md")

        if not row["spec"] and SPECS_DIR.exists():
            matching = list(SPECS_DIR.glob(f"spec-{prd_slug}-*.md"))
            if matching:
                spec_fname = matching[0].name
                feature_slug = spec_fname.removeprefix(f"spec-{prd_slug}-").removesuffix(".md")
                plan_fname = f"plan-{feature_slug}.prompt.md"
                has_plan = PLANS_DIR.exists() and (PLANS_DIR / plan_fname).exists()
                plan_status = "🟢 Done" if has_plan else "🟡 Spec Draft"
                _update_index(
                    row["prd"], spec_fname, row["feature"], plan_status, row["implementation"]
                )
                updated.append(row["prd"])
                continue

        if row["spec"] and row["plan_status"] != "🟢 Done" and PLANS_DIR.exists():
            feature_slug = row["spec"].removeprefix(f"spec-{prd_slug}-").removesuffix(".md")
            plan_fname = f"plan-{feature_slug}.prompt.md"
            if (PLANS_DIR / plan_fname).exists():
                _update_index(
                    row["prd"], row["spec"], row["feature"], "🟢 Done", row["implementation"]
                )
                updated.append(row["prd"])
                continue

        skipped.append(row["prd"])

    return {"added": added, "updated": updated, "skipped": skipped}


def register(mcp) -> None:
    @mcp.tool()
    def get_workflow_status() -> dict:
        """
        Returns the structured status from index.md.
        readOnlyHint=True — does not modify files.
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

    @mcp.tool()
    def update_index(
        prd_filename: str,
        spec_filename: str,
        feature_name: str,
        plan_status: str,
        implementation_status: str,
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
        return _update_index(
            prd_filename, spec_filename, feature_name, plan_status, implementation_status
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

        if not INDEX_FILE.exists():
            raise FileNotFoundError("index.md not found.")

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
            raise ValueError(f"Feature '{feature_name}' not found in index.md.")

        content = "".join(new_lines)
        INDEX_FILE.write_text(content)
        return content

    @mcp.tool()
    def check_duplicate(feature_name: str) -> dict:
        """
        Checks if a PRD, Spec or Plan already exists for feature_name.
        Searches by exact slug and individual tokens to cover
        camelCase conventions or partially different slugs.
        readOnlyHint=True — does not modify files.
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

    @mcp.tool()
    def list_artefacts(artefact_type: str) -> list[dict]:
        """
        Lists artifacts with filename, size and modification date.
        artefact_type: 'prd' | 'spec' | 'plan' | 'all'
        """
        valid = {"prd", "spec", "plan", "all"}
        if artefact_type not in valid:
            raise ValueError(f"Invalid artefact_type: '{artefact_type}'. Valid values: {valid}")

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
