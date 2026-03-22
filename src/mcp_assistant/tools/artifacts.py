import logging
import re
from typing import Literal

from fastmcp import Context
from pydantic import BaseModel, Field

from mcp_assistant.config import PLANS_DIR, PRDS_DIR, SPECS_DIR
from mcp_assistant.tools.workflow import (
    _get_index_row_by_prd,
    _get_index_row_by_spec,
    _update_index,
)
from mcp_assistant.utils import _slugify

logger = logging.getLogger(__name__)


class IdeaDetails(BaseModel):
    """Structured details collected during PRD ideation."""

    problem_statement: str = Field(description="Problem this feature solves")
    target_audience: str = Field(description="Who is the target user/persona")
    success_metrics: str = Field(description="KPIs/OKRs to measure success")
    scope_in: str = Field(description="What is in scope")
    scope_out: str = Field(default="", description="What is explicitly out of scope")
    priority: Literal["low", "medium", "high"] = Field(
        default="medium", description="Feature priority"
    )
    constraints: str = Field(default="", description="Technical or deadline constraints")
    dependencies: str = Field(default="", description="Related features or dependencies")
    acceptance_criteria: str = Field(
        default="", description="Acceptance Criteria and Definition of Done"
    )
    technical_notes: str = Field(
        default="", description="Entry points, latency targets, offline support"
    )
    project_path: str = Field(
        default="", description="Path to the project repository (default: current workspace)"
    )


def _render_prd_draft(feature_name: str, details: IdeaDetails) -> str:
    """Render a Markdown PRD draft from structured details.

    Args:
        feature_name: The human-readable name of the feature.
        details: Structured IdeaDetails collected via elicitation.

    Returns:
        A Markdown string representing the PRD draft.
    """
    scope_out_section = f"\n**Out of Scope:** {details.scope_out}" if details.scope_out else ""
    constraints_section = (
        f"\n\n## Constraints\n{details.constraints}" if details.constraints else ""
    )
    dependencies_section = (
        f"\n\n## Dependencies\n{details.dependencies}" if details.dependencies else ""
    )
    ac_section = (
        f"\n\n## Acceptance Criteria\n{details.acceptance_criteria}"
        if details.acceptance_criteria
        else ""
    )
    tech_section = (
        f"\n\n## Technical Notes\n{details.technical_notes}" if details.technical_notes else ""
    )

    return (
        f"# PRD: {feature_name}\n\n"
        f"## Problem Statement\n{details.problem_statement}\n\n"
        f"## Target Audience\n{details.target_audience}\n\n"
        f"## Success Metrics\n{details.success_metrics}\n\n"
        f"## Scope\n**In Scope:** {details.scope_in}{scope_out_section}\n\n"
        f"## Priority\n{details.priority.capitalize()}"
        f"{constraints_section}"
        f"{dependencies_section}"
        f"{ac_section}"
        f"{tech_section}\n"
    )


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

    @mcp.tool()
    async def ideate_prd(ctx: Context) -> dict:
        """Guides the user through a pre-PRD ideation journey using elicitation.

        Interactively collects feature details via a two-step elicitation flow:
        title → structured details form.  Duplicate detection happens synchronously
        between the two steps, returning an error rather than an extra elicitation
        round-trip so the server's elicitation request-ID counter stays below the
        client's ``tools/call`` request ID and avoids the duplicate-response bug
        that some MCP clients exhibit when both sides share the same integer ID.

        Args:
            ctx: FastMCP context used to send elicitation requests to the client.

        Returns:
            A dict with keys:
            - ``saved`` (bool): True if the PRD was created, False otherwise.
            - ``reason`` (str): Human-readable explanation when saved is False.
            - ``filename`` (str): Filename of the created PRD (only when saved is True).
            - ``path`` (str): Absolute path of the created PRD (only when saved is True).
            - ``content`` (str): Full Markdown content of the saved PRD (only when saved is True).
        """
        # Step 1 — collect feature title (elicitation id=0)
        title_result = await ctx.elicit("What is the name/title of the feature?", response_type=str)
        if title_result.action in ("decline", "cancel"):
            return {"saved": False, "reason": "Cancelled at title step"}

        feature_name: str = title_result.data  # type: ignore[union-attr]

        # Step 2 — synchronous duplicate check (fail-fast, no elicitation round-trip)
        slug = _slugify(feature_name)
        tokens = [t for t in slug.split("-") if len(t) >= 4]
        prd_patterns = [f"prd-{slug}*.md"] + [f"prd-*{t}*.md" for t in tokens]
        existing_prds: list[str] = []
        if PRDS_DIR.exists():
            seen: set = set()
            for pat in prd_patterns:
                for p in PRDS_DIR.glob(pat):
                    if p not in seen:
                        seen.add(p)
                        existing_prds.append(p.name)

        if existing_prds:
            logger.warning(
                "Duplicate PRD candidates detected for '%s': %s", feature_name, existing_prds
            )
            return {
                "saved": False,
                "reason": (
                    f"A PRD similar to '{feature_name}' already exists: "
                    f"{', '.join(existing_prds)}. "
                    "Review the existing PRD or choose a different feature name."
                ),
            }

        # Step 3 — structured details form (elicitation id=1)
        details_result = await ctx.elicit("Fill in the PRD details:", response_type=IdeaDetails)
        if details_result.action in ("decline", "cancel"):
            return {"saved": False, "reason": "Cancelled at details step"}

        details: IdeaDetails = details_result.data  # type: ignore[union-attr]
        draft = _render_prd_draft(feature_name, details)

        # Step 4 — persist immediately (no approval elicitation to avoid id=2 collision)
        logger.info("Saving PRD for feature '%s'", feature_name)
        prd_result = create_prd(feature_name, draft)
        return {"saved": True, "content": draft, **prd_result}
