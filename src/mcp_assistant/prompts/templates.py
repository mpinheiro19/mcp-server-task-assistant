from fastmcp.prompts import Message

from mcp_assistant.config import (
    COPILOT_INSTRUCTIONS,
    INDEX_FILE,
    PLANS_DIR,
    PRDS_DIR,
    SPEC_ASSISTANT_DIR,
    SPECS_DIR,
)

_PRD_SECTIONS_INSTRUCTION = """\
You are a senior product manager. Generate a comprehensive PRD in Markdown with \
the following sections (use these exact headings):

## Problem Statement
## Target Audience
## Success Metrics
## Scope
Include **In Scope** and **Out of Scope** sub-items.
## Priority
## User Stories
List items as "As a <persona>, I want <goal> so that <benefit>."
## Technical Impact Analysis
## Architecture / Design Suggestions
## Risks & Mitigations
Use a Markdown table with columns: Risk | Likelihood | Impact | Mitigation.
## Dependencies
## Constraints
## Acceptance Criteria
## Open Questions
Use a checklist (- [ ] …) for items that still need answers.
## Technical Notes

Generate ONLY the PRD Markdown content. Do NOT call any tool — \
the caller is responsible for persistence.\
"""


def _build_prd_prompt(idea_str: str, codebase_context: str = "") -> str:
    """Build a prompt string for LLM-based PRD generation.

    This is used by both the ``prd_from_idea`` MCP prompt and the
    ``ideate_prd`` tool (via ``ctx.sample()``).

    Args:
        idea_str: Free-form or structured description of the idea.
        codebase_context: Optional workspace context (structure, README, config).

    Returns:
        A single prompt string ready to be sent to ``ctx.sample()``
        or included in a ``Message``.
    """
    governance = ""
    if COPILOT_INSTRUCTIONS.exists():
        governance = COPILOT_INSTRUCTIONS.read_text()

    index_content = INDEX_FILE.read_text() if INDEX_FILE.exists() else "index.md does not exist yet."

    parts = [_PRD_SECTIONS_INSTRUCTION]
    if governance:
        parts.append(f"# GOVERNANCE PROTOCOL\n{governance}")
    if codebase_context:
        parts.append(f"# CODEBASE CONTEXT\n{codebase_context}")
    parts.append(f"# Current Index Status\n\n{index_content}")
    parts.append(f"# New Idea\n\n{idea_str}")
    parts.append("Please generate the corresponding PRD following the instructions above.")

    return "\n\n---\n\n".join(parts)


def register(mcp) -> None:
    @mcp.prompt()
    def prd_from_idea(idea: str) -> list[Message]:
        """Generates prompt to create a PRD from an idea, injecting governance protocol and index state."""
        prompt_text = _build_prd_prompt(idea)

        # The prompt variant tells the LLM to call create_prd after generating content.
        user_content = (
            f"{prompt_text}\n\n"
            "**IMPORTANT:** After generating the PRD content, call the MCP tool "
            "`create_prd(feature_name, content)` to persist the file and register "
            "it automatically in index.md. Do not write the file directly to the filesystem."
        )

        return [
            Message(role="user", content=user_content),
        ]

    @mcp.prompt()
    def spec_from_prd(prd_filename: str) -> list[Message]:
        """Generates prompt to create a Spec from a PRD."""
        prd_path = PRDS_DIR / prd_filename
        if not prd_path.resolve().is_relative_to(PRDS_DIR.resolve()):
            raise ValueError(f"Invalid filename: '{prd_filename}'")
        if not prd_path.exists():
            raise ValueError(f"PRD '{prd_filename}' not found.")

        prd_content = prd_path.read_text()
        tech_spec_template = (
            (SPEC_ASSISTANT_DIR / "tech-spec-prompt.md").read_text()
            if (SPEC_ASSISTANT_DIR / "tech-spec-prompt.md").exists()
            else ""
        )

        user_content = (
            f"{tech_spec_template}\n\n"
            f"---\n\n# PRD: {prd_filename}\n\n{prd_content}\n\n"
            "Please break down this PRD into Technical Specifications (Specs) following the protocol above.\n\n"
            "**IMPORTANT:** For each Spec generated, call the MCP tool "
            "`create_spec(feature_name, prd_filename, content)` to persist the file and "
            "update index.md automatically. Do not write files directly to the filesystem."
        )

        return [
            Message(role="user", content=user_content),
        ]

    @mcp.prompt()
    def plan_from_spec(spec_filename: str) -> list[Message]:
        """Generates prompt to create a Plan from a Spec."""
        spec_path = SPECS_DIR / spec_filename
        if not spec_path.resolve().is_relative_to(SPECS_DIR.resolve()):
            raise ValueError(f"Invalid filename: '{spec_filename}'")
        if not spec_path.exists():
            raise ValueError(f"Spec '{spec_filename}' not found.")

        spec_content = spec_path.read_text()

        example_plan = ""
        example_plans = sorted(PLANS_DIR.glob("*.md")) if PLANS_DIR.exists() else []
        if example_plans:
            example_plan = example_plans[0].read_text()

        user_content = (
            f"# Reference Spec: {spec_filename}\n\n{spec_content}\n\n"
            f"---\n\n# Plan Style Example\n\n{example_plan}\n\n"
            "---\n\n"
            "Please generate a Plan in the same style as the example above, based on the provided Spec.\n\n"
            "**IMPORTANT:** After generating the Plan content, call the MCP tool "
            f"`create_plan(feature_name=..., spec_filename='{spec_filename}', content=...)` "
            "to persist the file and mark plan_status as '🟢 Done' in index.md. "
            "Do not write the file directly to the filesystem."
        )

        return [
            Message(role="user", content=user_content),
        ]

    @mcp.prompt()
    def review_artefact(filename: str, artefact_type: str) -> list[Message]:
        """
        Generates a compliance review prompt for an artifact.
        artefact_type: 'prd' | 'spec' | 'plan'
        """
        dirs = {"prd": PRDS_DIR, "spec": SPECS_DIR, "plan": PLANS_DIR}
        if artefact_type not in dirs:
            raise ValueError(f"Invalid artefact_type: '{artefact_type}'")

        path = dirs[artefact_type] / filename
        if not path.resolve().is_relative_to(dirs[artefact_type].resolve()):
            raise ValueError(f"Invalid filename: '{filename}'")
        if not path.exists():
            raise ValueError(f"File '{filename}' not found in {dirs[artefact_type]}.")

        content = path.read_text()
        protocol = COPILOT_INSTRUCTIONS.read_text() if COPILOT_INSTRUCTIONS.exists() else ""

        user_content = (
            f"# Governance Protocol\n\n{protocol}\n\n"
            f"---\n\n# Artifact for Review ({artefact_type.upper()}): {filename}\n\n{content}\n\n"
            "---\n\n"
            "Please review this artifact, checking for adherence to the protocol above. "
            "Explicitly indicate each item from the compliance checklist and point out any issues if they exist."
        )

        return [
            Message(role="user", content=user_content),
        ]
