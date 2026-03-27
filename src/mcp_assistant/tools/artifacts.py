import logging
from typing import Literal

from fastmcp import Context
from pydantic import BaseModel, Field

from mcp_assistant.config import PLANS_DIR, PRDS_DIR, SPECS_DIR
from mcp_assistant.logging_config import LOG_PREVIEW_CHARS, log_operation
from mcp_assistant.prompts.templates import _build_prd_prompt
from mcp_assistant.tools.workflow import (
    _get_index_row_by_prd,
    _get_index_row_by_spec,
    _update_index,
)
from mcp_assistant.tools.elicitation import collect_pre_prd_elicitation
from mcp_assistant.utils import _gather_workspace_context, _slugify

logger = logging.getLogger(__name__)


class ElicitationChoice(BaseModel):
    """User preference for the pre-PRD architectural discovery step."""

    run_elicitation: bool = Field(
        default=True,
        description=(
            "Run a short architectural discovery session before generating the PRD? "
            "Recommended for better-informed results."
        ),
    )


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
        with log_operation(logger, "create_prd", feature=feature_name):
            slug = _slugify(feature_name)
            filename = f"{slug}.md"
            path = PRDS_DIR / filename

            if path.exists():
                raise ValueError(
                    f"PRD '{filename}' already exists. Use a different name or increment the version."
                )

            PRDS_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            size = path.stat().st_size
            logger.info("prd_written filename=%s size_bytes=%d", filename, size)
            logger.debug(
                "content_preview tool=create_prd chars=%d preview=%r",
                min(LOG_PREVIEW_CHARS, len(content)),
                content[:LOG_PREVIEW_CHARS],
            )

            result: dict = {"filename": filename, "path": str(path)}
            try:
                _update_index(filename, "", feature_name, "⏳ Waiting for Spec", "❌ Todo")
            except Exception as exc:
                logger.warning("index_update_failed filename=%s error=%r", filename, str(exc))
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
        with log_operation(logger, "create_spec", feature=feature_name, prd=prd_filename):
            prd_slug = prd_filename.removesuffix(".md")
            feature_slug = _slugify(feature_name)
            spec_dir = SPECS_DIR / prd_slug
            filename = f"{prd_slug}/{feature_slug}.md"
            path = spec_dir / f"{feature_slug}.md"

            if path.exists():
                raise ValueError(
                    f"Spec '{filename}' already exists. Use a different name or increment the version."
                )

            spec_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            size = path.stat().st_size
            logger.info("spec_written filename=%s size_bytes=%d", filename, size)
            logger.debug(
                "content_preview tool=create_spec chars=%d preview=%r",
                min(LOG_PREVIEW_CHARS, len(content)),
                content[:LOG_PREVIEW_CHARS],
            )

            result: dict = {"filename": filename, "path": str(path)}
            try:
                existing = _get_index_row_by_prd(prd_filename)
                impl = existing["implementation"] if existing else "❌ Todo"
                _update_index(prd_filename, filename, feature_name, "🟡 Spec Draft", impl)
            except Exception as exc:
                logger.warning("index_update_failed filename=%s error=%r", filename, str(exc))
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
        with log_operation(logger, "create_plan", feature=feature_name, spec=spec_filename):
            slug = _slugify(feature_name)
            filename = f"{slug}.prompt.md"
            path = PLANS_DIR / filename

            if path.exists():
                raise ValueError(
                    f"Plan '{filename}' already exists. Use a different name or increment the version."
                )

            PLANS_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            size = path.stat().st_size
            logger.info("plan_written filename=%s size_bytes=%d", filename, size)
            logger.debug(
                "content_preview tool=create_plan chars=%d preview=%r",
                min(LOG_PREVIEW_CHARS, len(content)),
                content[:LOG_PREVIEW_CHARS],
            )

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
                    logger.warning(
                        "spec_not_in_index spec=%s plan=%s", spec_filename, filename
                    )
                    result["index_warning"] = (
                        f"Spec '{spec_filename}' not found in index.md; " "entry not updated."
                    )
            except Exception as exc:
                logger.warning("index_update_failed filename=%s error=%r", filename, str(exc))
                result["index_warning"] = str(exc)
            return result

    @mcp.tool()
    async def ideate_prd(ctx: Context) -> dict:
        """Guides the user through a pre-PRD ideation journey using elicitation and LLM sampling.

        Interactively collects feature details via a two-step elicitation flow:
        title → structured details form.  Then gathers workspace context and uses
        ``ctx.sample()`` to have the LLM generate an elaborated PRD draft with
        User Stories, Risks, Architecture suggestions and Open Questions.

        If the client does not support MCP sampling, falls back to a basic
        template-based PRD draft.

        The elaborated draft is automatically persisted as a PRD file when no
        duplicate is detected.  On duplicate, returns ``saved=False`` with a
        ``reason`` so the orchestrating LLM can inform the user.

        Args:
            ctx: FastMCP context used to send elicitation and sampling requests.

        Returns:
            A dict with keys:
            - ``saved`` (bool): True when the PRD was persisted; False on conflict/cancel.
            - ``draft`` (str): Full Markdown PRD draft for the LLM to present to the user.
            - ``filename`` (str): Created file name (only when ``saved=True``).
            - ``path`` (str): Absolute path to the created file (only when ``saved=True``).
            - ``feature_name`` (str): The feature title.
            - ``sampling_used`` (bool): Whether LLM sampling was used.
            - ``reason`` (str): Explains why the PRD was not saved (only when ``saved=False``).
        """
        logger.info("start op=ideate_prd")

        # Step 1 — collect feature title (elicitation id=0)
        logger.debug("ideate_prd step=1 action=elicit_title")
        title_result = await ctx.elicit("What is the name/title of the feature?", response_type=str)
        if title_result.action in ("decline", "cancel"):
            logger.info("ideate_prd cancelled step=title action=%s", title_result.action)
            return {"saved": False, "reason": "Cancelled at title step"}

        feature_name: str = title_result.data  # type: ignore[union-attr]
        logger.info("ideate_prd step=1 feature=%s", feature_name)

        # Step 2 — synchronous duplicate check (fail-fast, no elicitation round-trip)
        logger.debug("ideate_prd step=2 action=duplicate_check feature=%s", feature_name)
        slug = _slugify(feature_name)
        tokens = [t for t in slug.split("-") if len(t) >= 4]
        prd_patterns = [f"{slug}*.md"] + [f"*{t}*.md" for t in tokens]
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
                "duplicate_prd_detected feature=%s matches=%s", feature_name, existing_prds
            )
            return {
                "saved": False,
                "reason": (
                    f"A PRD similar to '{feature_name}' already exists: "
                    f"{', '.join(existing_prds)}. "
                    "Review the existing PRD or choose a different feature name."
                ),
            }
        logger.debug("ideate_prd step=2 no_duplicates_found feature=%s", feature_name)

        # Step 3 — offer pre-PRD architectural discovery (premise, skippable)
        logger.debug("ideate_prd step=3 action=elicit_choice feature=%s", feature_name)
        choice_result = await ctx.elicit(
            "Run an architectural discovery session before generating the PRD?",
            response_type=ElicitationChoice,
        )

        enriched_context = ""
        if choice_result.action == "accept" and choice_result.data.run_elicitation:
            logger.info("ideate_prd step=3 elicitation=requested feature=%s", feature_name)
            enriched_context = await collect_pre_prd_elicitation(ctx, feature_name)
            logger.info(
                "ideate_prd step=3 elicitation=done feature=%s enriched_chars=%d",
                feature_name,
                len(enriched_context),
            )
        else:
            logger.info("ideate_prd step=3 elicitation=skipped feature=%s", feature_name)

        # Step 4 — structured details form
        logger.debug("ideate_prd step=4 action=elicit_details feature=%s", feature_name)
        details_result = await ctx.elicit("Fill in the PRD details:", response_type=IdeaDetails)
        if details_result.action in ("decline", "cancel"):
            logger.info("ideate_prd cancelled step=details action=%s", details_result.action)
            return {"saved": False, "reason": "Cancelled at details step"}

        details: IdeaDetails = details_result.data  # type: ignore[union-attr]
        logger.debug(
            "ideate_prd step=4 details_received priority=%s project_path=%r",
            details.priority,
            details.project_path or "(default)",
        )

        # Step 5 — gather workspace context (used when elicitation was skipped)
        logger.debug("ideate_prd step=5 action=gather_workspace_context")
        codebase_context = _gather_workspace_context(details.project_path)
        logger.debug(
            "ideate_prd step=5 workspace_context_chars=%d", len(codebase_context)
        )

        # Step 6 — build rich idea description from all IdeaDetails fields
        idea_parts = [
            f"# {feature_name}",
            f"**Problem Statement:** {details.problem_statement}",
            f"**Target Audience:** {details.target_audience}",
            f"**Success Metrics:** {details.success_metrics}",
            f"**In Scope:** {details.scope_in}",
        ]
        if details.scope_out:
            idea_parts.append(f"**Out of Scope:** {details.scope_out}")
        idea_parts.append(f"**Priority:** {details.priority}")
        if details.constraints:
            idea_parts.append(f"**Constraints:** {details.constraints}")
        if details.dependencies:
            idea_parts.append(f"**Dependencies:** {details.dependencies}")
        if details.acceptance_criteria:
            idea_parts.append(f"**Acceptance Criteria:** {details.acceptance_criteria}")
        if details.technical_notes:
            idea_parts.append(f"**Technical Notes:** {details.technical_notes}")
        idea_str = "\n\n".join(idea_parts)

        prompt = _build_prd_prompt(idea_str, codebase_context, enriched_context)

        # Step 7 — LLM sampling with fallback to basic template
        sampling_used = False
        logger.info("llm_sampling_start tool=ideate_prd feature=%s max_tokens=4096", feature_name)
        try:
            sample_result = await ctx.sample(prompt, max_tokens=4096)
            draft = sample_result.text or _render_prd_draft(feature_name, details)
            sampling_used = True
            logger.info(
                "llm_sampling_end tool=ideate_prd status=ok feature=%s draft_chars=%d",
                feature_name,
                len(draft),
            )
            logger.debug(
                "content_preview tool=ideate_prd chars=%d preview=%r",
                min(LOG_PREVIEW_CHARS, len(draft)),
                draft[:LOG_PREVIEW_CHARS],
            )
        except Exception as exc:
            logger.warning(
                "llm_sampling_end tool=ideate_prd status=fallback feature=%s error=%r",
                feature_name,
                str(exc),
            )
            draft = _render_prd_draft(feature_name, details)

        # Persist the PRD automatically — no duplicate detected at this point.
        slug = _slugify(feature_name)
        filename = f"{slug}.md"
        prd_path = PRDS_DIR / filename
        PRDS_DIR.mkdir(parents=True, exist_ok=True)
        prd_path.write_text(draft)
        size = prd_path.stat().st_size
        logger.info(
            "prd_auto_saved feature=%s filename=%s size_bytes=%d sampling_used=%s",
            feature_name,
            filename,
            size,
            sampling_used,
        )

        result: dict = {
            "saved": True,
            "draft": draft,
            "filename": filename,
            "path": str(prd_path),
            "feature_name": feature_name,
            "sampling_used": sampling_used,
            "elicitation_used": bool(enriched_context),
        }
        try:
            _update_index(filename, "", feature_name, "⏳ Waiting for Spec", "❌ Todo")
        except Exception as exc:
            logger.warning("index_update_failed filename=%s error=%r", filename, str(exc))
            result["index_warning"] = str(exc)

        logger.info("end op=ideate_prd status=ok feature=%s saved=True", feature_name)
        return result
