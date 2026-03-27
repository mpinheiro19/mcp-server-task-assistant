# Prompts Reference

Prompt templates are invoked by MCP clients to produce context-rich messages ready for LLM completion. Each template reads relevant files from disk and injects their contents into the message.

---

## `prd_from_idea`

Generates a structured prompt for authoring a new PRD from a raw idea.

**Context injected automatically:**
- `copilot-instructions.md` — governance protocol
- `prd-prompt.md` (from `spec-driven-assistant/`) — PRD authoring guidelines
- Current `index.md` — existing feature inventory to avoid duplicates
- `context-{slug}.md` (optional, from `elicitations/`) — enriched technical context produced by `consolidate_technical_context`; replaces generic codebase context when provided

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `idea` | `str` | Free-form description of the feature idea. |
| `context_filename` | `str \| None` | Filename of a `context-{slug}.md` artifact in `ELICITATIONS_DIR`. Optional. When provided, must exist. |

**Recommended prior steps:**
1. Call `check_duplicate(idea)` to confirm no existing artifact covers the same feature.
2. (Optional but recommended) Run the elicitation flow: `run_expert_elicitation` → fill answers → `consolidate_technical_context` → pass the resulting `context_filename`.

**Errors:**
- `ValueError` if `context_filename` would escape `ELICITATIONS_DIR` (path traversal guard).
- `FileNotFoundError` if `context_filename` is provided but the file does not exist.

---

## `spec_from_prd`

Generates a prompt for decomposing an existing PRD into one or more Technical Specs.

**Context injected automatically:**
- `tech-spec-prompt.md` (from `spec-driven-assistant/`) — spec authoring guidelines
- Full content of the target PRD

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `prd_filename` | `str` | Filename of the PRD to decompose (e.g., `prd-user-auth.md`). |

**Errors:** `ValueError` if the PRD file does not exist.

---

## `plan_from_spec`

Generates a prompt for producing an implementation Plan from a Spec. Automatically includes a style example drawn from the first existing plan file, ensuring consistent format.

**Context injected automatically:**
- Full content of the target Spec
- First existing plan file as a style reference (if any plans exist)

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `spec_filename` | `str` | Filename of the Spec to plan (e.g., `spec-user-auth-login-flow.md`). |

**Errors:** `ValueError` if the Spec file does not exist.

---

## `review_artefact`

Generates a compliance review prompt for any artifact type.

**Context injected automatically:**
- `copilot-instructions.md` — governance protocol used as the review rubric
- Full content of the target artifact

| Parameter | Type | Valid values |
| :--- | :--- | :--- |
| `filename` | `str` | Filename of the artifact to review. |
| `artefact_type` | `str` | `"prd"` · `"spec"` · `"plan"` |

**Errors:**
- `ValueError` if `artefact_type` is not one of the valid values.
- `ValueError` if the file does not exist in the expected directory.
