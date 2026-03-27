import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib  # noqa: F401
else:
    try:
        import tomllib  # noqa: F401
    except ImportError:
        import tomli as tomllib  # type: ignore[no-reparse-import]  # noqa: F401

from fastmcp import Context, FastMCP
from pydantic import BaseModel

from mcp_assistant.config import ELICITATION_MAX_DEPTH, ELICITATIONS_DIR, PROJECT_ROOT
from mcp_assistant.logging_config import LOG_PREVIEW_CHARS, log_operation
from mcp_assistant.utils import _slugify

logger = logging.getLogger(__name__)

_IGNORE_DIRS = frozenset(
    {
        "node_modules",
        ".git",
        "__pycache__",
        "venv",
        ".venv",
        "dist",
        "build",
        ".tox",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "coverage",
    }
)

_MANIFEST_FILES = (
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "requirements.txt",
    "setup.cfg",
    "setup.py",
)

_STACK_KEYWORDS: dict[str, list[str]] = {
    "Python": ["python", "fastmcp", "fastapi", "django", "flask", "pydantic"],
    "FastMCP": ["fastmcp"],
    "Node.js": ["node", "express", "next", "react", "vue", "typescript"],
    "PostgreSQL": ["psycopg", "asyncpg", "postgres", "pg"],
    "SQLite": ["sqlite"],
    "Redis": ["redis"],
    "Docker": ["dockerfile", "docker-compose"],
    "Rust": ["cargo.toml", "[package]"],
    "Go": ["go.mod"],
}

_PATTERN_KEYWORDS: dict[str, list[str]] = {
    "Clean Architecture": ["domain", "use_case", "repository", "entity"],
    "DDD": ["aggregate", "value_object", "bounded_context", "domain_event"],
    "MVC": ["controller", "view", "model"],
    "Repository Pattern": ["repository"],
    "Event-Driven": ["event", "publisher", "subscriber", "queue"],
}


class RepositoryContext(BaseModel):
    root: str
    tree: list[str]
    manifests: dict[str, str]
    detected_stack: list[str]
    detected_patterns: list[str]


def _walk_limited(root: Path, max_depth: int) -> tuple[list[str], dict[str, str]]:
    """Walk directory tree up to max_depth. Returns (tree_paths, manifests)."""
    tree: list[str] = []
    manifests: dict[str, str] = {}

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        depth = len(current.relative_to(root).parts)
        if depth >= max_depth:
            dirnames.clear()
            continue

        dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS]

        for fname in filenames:
            rel = (current / fname).relative_to(root)
            tree.append(str(rel))
            if fname in _MANIFEST_FILES:
                full_path = current / fname
                try:
                    manifests[fname] = full_path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    manifests[fname] = ""

    return tree, manifests


def _infer_stack_and_patterns(
    tree: list[str], manifests: dict[str, str]
) -> tuple[list[str], list[str]]:
    combined = " ".join(manifests.values()).lower() + " " + " ".join(tree).lower()

    detected_stack = [
        name for name, keywords in _STACK_KEYWORDS.items() if any(kw in combined for kw in keywords)
    ]
    detected_patterns = [
        name
        for name, keywords in _PATTERN_KEYWORDS.items()
        if any(kw in combined for kw in keywords)
    ]
    return detected_stack, detected_patterns


def _build_elicitation_prompt(
    feature_name: str,
    prd_draft: str,
    repo_ctx: RepositoryContext,
    num_questions: int,
) -> str:
    return f"""You are a senior software architect reviewing a PRD draft.
Given the repository context below, generate exactly {num_questions} targeted technical questions
that must be answered before implementation can begin. Focus on:
- Architectural fit with the existing stack
- Integration points and breaking changes
- Data model decisions
- Edge cases not addressed in the PRD

## Repository Context
- Root: {repo_ctx.root}
- Detected Stack: {', '.join(repo_ctx.detected_stack) or 'Unknown'}
- Detected Patterns: {', '.join(repo_ctx.detected_patterns) or 'None identified'}

## PRD Draft
{prd_draft}

## Output Format
Return ONLY a numbered list, one question per line:
1. <question>
2. <question>
...
"""


def _parse_questions(text: str, expected: int) -> list[str]:
    """Extract numbered questions from LLM output.

    Expects lines matching: '<number>. <text>'
    Falls back to _default_questions if fewer than 3 valid lines found.
    """
    lines = [
        re.sub(r"^\d+\.\s*", "", line.strip())
        for line in text.splitlines()
        if re.match(r"^\d+\.", line.strip())
    ]
    if len(lines) < 3:
        return _default_questions("", expected)
    return lines[:expected]


def _default_questions(feature_name: str, n: int) -> list[str]:
    defaults = [
        "What are the main integration points with the existing codebase?",
        "Are there any backward compatibility constraints to be observed?",
        "What is the expected error handling strategy for this module?",
        "Are any new external dependencies required? If so, how will they be managed?",
        "How will test coverage be ensured? Which scenarios are critical?",
        "What is the expected behavior under partial failure conditions?",
        "Are there any performance or resource limit considerations to define?",
    ]
    return defaults[:n]


def _build_consolidation_prompt(
    prd_draft: str,
    answers: list[str],
    repo_ctx: RepositoryContext,
) -> str:
    formatted_answers = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(answers))
    return f"""You are a senior software architect. Given the original PRD draft,
the developer's answers to architectural questions, and the repository context,
produce a structured Technical Context document in Markdown.

The document must include:
- ## Summary: A concise paragraph synthesizing the feature and its architectural fit
- ## Architectural Decisions: Key decisions derived from the answers
- ## Integration Points: Which modules/files will be affected
- ## Constraints & Risks: Any constraints or risks identified
- ## Recommended Approach: High-level implementation direction

## Repository Context
- Stack: {', '.join(repo_ctx.detected_stack) or 'Unknown'}
- Patterns: {', '.join(repo_ctx.detected_patterns) or 'None identified'}
- Root: {repo_ctx.root}

## PRD Draft
{prd_draft}

## Developer Answers
{formatted_answers}

Generate ONLY the Technical Context Markdown. Do NOT call any tool.
"""


def _extract_answers(content: str) -> list[str]:
    """Extract non-empty answers from the '## 📝 Answers' section."""
    in_section = False
    answers = []
    for line in content.splitlines():
        if line.strip() == "## 📝 Answers":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.startswith(">"):
            answer_text = line[1:].strip()
            if answer_text:
                answers.append(answer_text)
    return answers


def _extract_prd_draft(content: str) -> str:
    """Extract content between '## 🔍 Original PRD Draft' and next '##' section."""
    lines: list[str] = []
    in_section = False
    for line in content.splitlines():
        if line.strip() == "## 🔍 Original PRD Draft":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            lines.append(line.lstrip("> "))
    return "\n".join(lines).strip()


def _render_fallback_context(
    prd_draft: str,
    answers: list[str],
    repo_ctx: RepositoryContext,
) -> str:
    """Render a basic context document without LLM sampling."""
    answers_md = "\n".join(f"- {a}" for a in answers)
    return f"""## Summary
Context consolidated from elicitation answers (sampling unavailable).

## Architectural Decisions
{answers_md}

## Repository Context
- Stack: {', '.join(repo_ctx.detected_stack)}
- Patterns: {', '.join(repo_ctx.detected_patterns)}
- Root: {repo_ctx.root}

## PRD Draft Reference
{prd_draft}
"""


def _update_elicitation_index(
    slug: str,
    feature_name: str,
    filename: str,
    status: str,
) -> None:
    """Upsert a row in ELICITATIONS_DIR/index.md. Best-effort — exceptions are silenced."""
    try:
        ELICITATIONS_DIR.mkdir(parents=True, exist_ok=True)
        index_path = ELICITATIONS_DIR / "index.md"
        header = "| Feature | File | Status |\n| :--- | :--- | :--- |"
        new_row = f"| {feature_name} | {filename} | {status} |"

        if not index_path.exists():
            index_path.write_text(header + "\n" + new_row + "\n", encoding="utf-8")
            return

        text = index_path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        updated = False
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if (
                stripped.startswith("|")
                and filename in stripped
                and not stripped.startswith("| Feature")
                and not stripped.startswith("| :")
            ):
                new_lines.append(new_row + "\n")
                updated = True
            else:
                new_lines.append(line)

        if not updated:
            new_lines.append(new_row + "\n")

        index_path.write_text("".join(new_lines), encoding="utf-8")
    except Exception:
        pass


def map_repository_context(project_path: str = "") -> dict:
    """Scan a repository directory and return its architectural context.

    Builds a RepositoryContext by walking the directory tree up to
    ELICITATION_MAX_DEPTH levels, reading manifest files, and inferring
    the tech stack and architecture patterns from their contents.

    Args:
        project_path: Absolute path to the repository root. Defaults to
            CODES_ROOT when empty or not provided.

    Returns:
        RepositoryContext serialized as a dict with keys:
        - root (str): Resolved project root path.
        - tree (list[str]): Relative paths found within depth limit.
        - manifests (dict[str, str]): Manifest filename → raw content.
        - detected_stack (list[str]): Inferred technology names.
        - detected_patterns (list[str]): Inferred architectural patterns.
    """
    root = Path(project_path).resolve() if project_path else PROJECT_ROOT.resolve()
    if not root.is_dir():
        raise ValueError(f"project_path does not exist or is not a directory: {project_path}")

    logger.debug("map_repository_context root=%s max_depth=%d", root, ELICITATION_MAX_DEPTH)
    tree, manifests = _walk_limited(root, ELICITATION_MAX_DEPTH)
    detected_stack, detected_patterns = _infer_stack_and_patterns(tree, manifests)

    logger.info(
        "map_repository_context root=%s tree_files=%d manifests=%s stack=%s patterns=%s",
        root,
        len(tree),
        list(manifests.keys()),
        detected_stack,
        detected_patterns,
    )
    logger.debug("map_repository_context tree=%s", tree)

    return RepositoryContext(
        root=str(root),
        tree=tree,
        manifests=manifests,
        detected_stack=detected_stack,
        detected_patterns=detected_patterns,
    ).model_dump()


async def run_expert_elicitation(
    ctx: Context,
    feature_name: str,
    prd_draft: str,
    project_path: str = "",
    num_questions: int = 5,
) -> dict:
    """Generate and persist a technical elicitation file for a feature.

    Scans the repository context, then uses LLM sampling (ctx.sample()) to
    generate architecture-aware questions about the feature. Persists the
    elicitation file and registers it in the elicitations index.

    Args:
        ctx: FastMCP context for sampling.
        feature_name: Human-readable feature name (used for slug and artifact title).
        prd_draft: Raw text of the PRD draft to analyse.
        project_path: Path to the target repository. Defaults to CODES_ROOT.
        num_questions: Number of questions to generate. Clamped to [3, 7].

    Returns:
        {
            "saved": bool,
            "filename": str,         # "elicitation-{slug}.md" (only if saved=True)
            "path": str,             # Absolute path (only if saved=True)
            "sampling_used": bool,
            "questions_count": int,
            "reason": str,           # Error message (only if saved=False)
        }
    """
    num_questions = max(3, min(num_questions, 7))
    logger.info(
        "start op=run_expert_elicitation feature=%s num_questions=%d", feature_name, num_questions
    )

    repo_ctx_dict = map_repository_context(project_path)
    repo_ctx = RepositoryContext(**repo_ctx_dict)

    sampling_used = False
    questions: list[str] = []

    logger.info(
        "llm_sampling_start tool=run_expert_elicitation feature=%s", feature_name
    )
    try:
        result = await ctx.sample(
            _build_elicitation_prompt(feature_name, prd_draft, repo_ctx, num_questions)
        )
        questions = _parse_questions(result.text, num_questions)
        sampling_used = True
        logger.info(
            "llm_sampling_end tool=run_expert_elicitation status=ok feature=%s questions=%d",
            feature_name, len(questions),
        )
    except Exception as exc:
        logger.warning(
            "llm_sampling_end tool=run_expert_elicitation status=fallback feature=%s error=%r",
            feature_name, str(exc),
        )
        questions = _default_questions(feature_name, num_questions)

    slug = _slugify(feature_name)
    questions_list = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
    answers_section = "\n\n".join(f"**{i + 1}.** {q}\n>" for i, q in enumerate(questions))

    content = f"""# Technical Elicitation: {feature_name}

## Identified Architectural Context
- **Stack:** {', '.join(repo_ctx.detected_stack) or 'Unknown'}
- **Patterns:** {', '.join(repo_ctx.detected_patterns) or 'None identified'}
- **Root:** {repo_ctx.root}

## 🔍 Original PRD Draft
> {prd_draft}

## Pending Questions
{questions_list}

## 📝 Answers
<!-- Fill in each answer below the corresponding question -->

{answers_section}
"""

    ELICITATIONS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = ELICITATIONS_DIR / f"{slug}.md"
    file_path.write_text(content, encoding="utf-8")
    size = file_path.stat().st_size
    logger.info(
        "elicitation_written feature=%s filename=%s size_bytes=%d questions=%d",
        feature_name, file_path.name, size, len(questions),
    )
    logger.debug(
        "content_preview tool=run_expert_elicitation chars=%d preview=%r",
        min(LOG_PREVIEW_CHARS, len(content)),
        content[:LOG_PREVIEW_CHARS],
    )

    _update_elicitation_index(slug, feature_name, file_path.name, "⏳ Pending")

    logger.info(
        "end op=run_expert_elicitation status=ok feature=%s saved=True sampling_used=%s",
        feature_name, sampling_used,
    )
    return {
        "saved": True,
        "filename": file_path.name,
        "path": str(file_path),
        "sampling_used": sampling_used,
        "questions_count": len(questions),
    }


async def consolidate_technical_context(
    ctx: Context,
    feature_name: str,
    elicitation_filename: str,
) -> dict:
    """Fuse elicitation answers with repository context and persist enriched context.

    Reads an elicitation file, validates that answers have been filled in,
    then uses LLM sampling to synthesize a structured context artifact.
    The resulting context file is meant to be consumed by prd_from_idea.

    Args:
        ctx: FastMCP context for sampling.
        feature_name: Feature name (used to derive the context filename slug).
        elicitation_filename: Filename of the elicitation file, e.g. "elicitation-foo.md".

    Returns:
        {
            "saved": bool,
            "context_filename": str,  # "context-{slug}.md" (only if saved=True)
            "path": str,              # Absolute path (only if saved=True)
            "sampling_used": bool,
            "reason": str,            # Error message (only if saved=False)
        }
    """
    logger.info(
        "start op=consolidate_technical_context feature=%s elicitation=%s",
        feature_name, elicitation_filename,
    )

    elicitation_path = ELICITATIONS_DIR / elicitation_filename
    if not elicitation_path.resolve().is_relative_to(ELICITATIONS_DIR.resolve()):
        logger.warning(
            "path_traversal_blocked tool=consolidate requested=%s resolved=%s",
            elicitation_filename, elicitation_path.resolve(),
        )
        raise ValueError(f"Invalid filename: '{elicitation_filename}'")
    if not elicitation_path.exists():
        logger.warning("elicitation_not_found filename=%s", elicitation_filename)
        raise FileNotFoundError(f"Elicitation file not found: '{elicitation_filename}'")

    content = elicitation_path.read_text(encoding="utf-8")

    answers = _extract_answers(content)
    if not answers:
        logger.info(
            "consolidate_technical_context no_answers_found elicitation=%s", elicitation_filename
        )
        return {
            "saved": False,
            "sampling_used": False,
            "reason": (
                f"No answers found in '{elicitation_filename}'. "
                "Please fill in the '## 📝 Answers' section before consolidating."
            ),
        }

    logger.debug(
        "consolidate_technical_context answers_found count=%d elicitation=%s",
        len(answers), elicitation_filename,
    )

    prd_draft = _extract_prd_draft(content)

    root_match = re.search(r"\*\*Root:\*\*\s*(.+)", content)
    project_path = root_match.group(1).strip() if root_match else ""
    repo_ctx_dict = map_repository_context(project_path)
    repo_ctx = RepositoryContext(**repo_ctx_dict)

    sampling_used = False
    logger.info(
        "llm_sampling_start tool=consolidate_technical_context feature=%s", feature_name
    )
    try:
        result = await ctx.sample(_build_consolidation_prompt(prd_draft, answers, repo_ctx))
        context_content = result.text
        sampling_used = True
        logger.info(
            "llm_sampling_end tool=consolidate_technical_context status=ok feature=%s chars=%d",
            feature_name, len(context_content),
        )
    except Exception as exc:
        logger.warning(
            "llm_sampling_end tool=consolidate_technical_context status=fallback feature=%s error=%r",
            feature_name, str(exc),
        )
        context_content = _render_fallback_context(prd_draft, answers, repo_ctx)

    slug = _slugify(feature_name)
    stack_yaml = "\n".join(f"  - {s}" for s in repo_ctx.detected_stack)
    patterns_yaml = "\n".join(f"  - {p}" for p in repo_ctx.detected_patterns)
    frontmatter = f"""---
feature: {feature_name}
elicitation_file: {elicitation_filename}
consolidated_at: {datetime.now(timezone.utc).isoformat()}
stack:
{stack_yaml if stack_yaml else "  []"}
patterns:
{patterns_yaml if patterns_yaml else "  []"}
---
"""

    context_path = ELICITATIONS_DIR / f"context-{slug}.md"
    context_path.write_text(frontmatter + "\n" + context_content, encoding="utf-8")
    size = context_path.stat().st_size
    logger.info(
        "context_written feature=%s filename=%s size_bytes=%d",
        feature_name, context_path.name, size,
    )

    _update_elicitation_index(slug, feature_name, context_path.name, "✅ Consolidated")

    logger.info(
        "end op=consolidate_technical_context status=ok feature=%s saved=True sampling_used=%s",
        feature_name, sampling_used,
    )
    return {
        "saved": True,
        "context_filename": context_path.name,
        "path": str(context_path),
        "sampling_used": sampling_used,
    }


def register(mcp: FastMCP) -> None:
    mcp.tool(map_repository_context)
    mcp.tool(run_expert_elicitation)
    mcp.tool(consolidate_technical_context)
