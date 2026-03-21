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
        Creates a new PRD file in prds/.
        Slugifies feature_name → prd-<slug>.md. Checks for duplicates before creating.
        Automatically registers the artifact in index.md after creation.
        """
        slug = _slugify(feature_name)
        filename = f"prd-{slug}.md"
        path = PRDS_DIR / filename

        if path.exists():
            raise ValueError(
                f"PRD '{filename}' already exists. Use a different name or increment the version."
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
        Creates a new Spec file in specs/.
        Name: spec-<prd-slug>-<feature-slug>.md
        Updates index.md: fills spec_filename and changes plan_status to '🟡 Spec Draft'.
        Preserves the existing implementation_status.
        """
        prd_slug = re.sub(r"^prd-", "", prd_filename.removesuffix(".md"))
        feature_slug = _slugify(feature_name)
        filename = f"spec-{prd_slug}-{feature_slug}.md"
        path = SPECS_DIR / filename

        if path.exists():
            raise ValueError(
                f"Spec '{filename}' already exists. Use a different name or increment the version."
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
        Creates a new Plan file in plans/.
        Name: plan-<feature-slug>.prompt.md
        Updates index.md: changes plan_status to '🟢 Done'. Preserves implementation_status.
        spec_filename is required to locate the correct row in index.md.
        """
        slug = _slugify(feature_name)
        filename = f"plan-{slug}.prompt.md"
        path = PLANS_DIR / filename

        if path.exists():
            raise ValueError(
                f"Plan '{filename}' already exists. Use a different name or increment the version."
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
                    f"Spec '{spec_filename}' not found in index.md; " "entry not updated."
                )
        except Exception as exc:
            result["index_warning"] = str(exc)
        return result
