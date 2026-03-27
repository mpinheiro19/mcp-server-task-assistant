# Tools Reference

All tools are registered with FastMCP and exposed over the MCP protocol. Clients call them by name.

---

## Pre-PRD Elicitation

The elicitation layer sits **before** PRD creation. It scans the target repository, generates architecture-aware questions, collects developer answers, and synthesizes a structured Technical Context artifact that can be fed directly into `prd_from_idea`.

### Recommended flow

```
run_expert_elicitation → (fill answers in elicitation-{slug}.md) → consolidate_technical_context
                                                                              ↓
                                                              prd_from_idea(context_filename=…)
```

---

### `map_repository_context`

Scans a repository directory and returns its architectural context. Read-only.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `project_path` | `str` | Absolute path to the repository root. Defaults to `CODES_ROOT` when empty. |

**Returns:**
```json
{
  "root": "/abs/path/to/project",
  "tree": ["src/app.py", "pyproject.toml", "…"],
  "manifests": { "pyproject.toml": "[project]\nname = ...", "…": "…" },
  "detected_stack": ["Python", "FastMCP"],
  "detected_patterns": ["Clean Architecture"]
}
```

The tree is limited to `ELICITATION_MAX_DEPTH` levels (default: 3). Common noise directories (`node_modules`, `.git`, `__pycache__`, etc.) are excluded.

**Errors:**
- `ValueError` if `project_path` does not exist or is not a directory.

---

### `run_expert_elicitation`

Generates architecture-aware technical questions for a feature and persists an elicitation file for the developer to fill in.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `feature_name` | `str` | Human-readable feature name. Slugified to form the filename. |
| `prd_draft` | `str` | Raw text of the PRD draft (or idea) to analyse. |
| `project_path` | `str` | Path to the target repository. Defaults to `CODES_ROOT`. |
| `num_questions` | `int` | Number of questions to generate. Clamped to `[3, 7]`. Default: `5`. |

Uses `ctx.sample()` to generate questions via the LLM. Falls back to 7 built-in default questions if sampling is unavailable.

**Returns:**
```json
{
  "saved": true,
  "filename": "elicitation-my-feature.md",
  "path": "/abs/path/to/elicitations/elicitation-my-feature.md",
  "sampling_used": true,
  "questions_count": 5
}
```

Also registers the artifact in `elicitations/index.md` with status `⏳ Pending`.

---

### `consolidate_technical_context`

Reads a filled-in elicitation file and uses LLM sampling to synthesize a structured Technical Context document. The resulting `context-{slug}.md` can be passed to `prd_from_idea` via `context_filename`.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `feature_name` | `str` | Feature name (used to derive the context filename slug). |
| `elicitation_filename` | `str` | Filename of the elicitation file, e.g. `"elicitation-foo.md"`. |

**Returns (success):**
```json
{
  "saved": true,
  "context_filename": "context-my-feature.md",
  "path": "/abs/path/to/elicitations/context-my-feature.md",
  "sampling_used": true
}
```

**Returns (no answers found):**
```json
{
  "saved": false,
  "sampling_used": false,
  "reason": "No answers found in 'elicitation-foo.md'. Please fill in the '❤️ Answers' section before consolidating."
}
```

The context file includes YAML frontmatter (feature name, elicitation filename, timestamp, detected stack/patterns) followed by a Markdown body with sections: Summary, Architectural Decisions, Integration Points, Constraints & Risks, Recommended Approach.

Also updates `elicitations/index.md` status to `✅ Consolidated`.

**Errors:**
- `ValueError` if `elicitation_filename` would escape `ELICITATIONS_DIR` (path traversal guard).
- `FileNotFoundError` if the elicitation file does not exist.

---

## Artifact Creation

### `create_prd`

Creates a new PRD file in `prds/`.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `feature_name` | `str` | Human-readable feature name. Slugified to form the filename. |
| `content` | `str` | Full Markdown content of the PRD. |

**Returns:** `{ "filename": "prd-<slug>.md", "path": "<absolute path>" }`

**Errors:**
- `ValueError` if `prd-<slug>.md` already exists.

**Example:**
```
create_prd("User Authentication", "# PRD\n…")
→ { "filename": "prd-user-authentication.md", "path": "…/prds/prd-user-authentication.md" }
```

---

### `create_spec`

Creates a new Spec file in `specs/`. The filename encodes both the parent PRD and the feature being specified.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `feature_name` | `str` | Name of the specific feature being specified. |
| `prd_filename` | `str` | Filename of the parent PRD (e.g., `prd-user-authentication.md`). |
| `content` | `str` | Full Markdown content of the Spec. |

**Returns:** `{ "filename": "spec-<prd-slug>-<feature-slug>.md", "path": "…" }`

**Errors:**
- `ValueError` if the derived filename already exists.

**Example:**
```
create_spec("Login Flow", "prd-user-authentication.md", "# Spec\n…")
→ { "filename": "spec-user-authentication-login-flow.md", "path": "…" }
```

---

### `create_plan`

Creates a new Plan file in `plans/` with the `.prompt.md` extension convention.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `feature_name` | `str` | Human-readable feature name. |
| `content` | `str` | Full Markdown content of the Plan. |

**Returns:** `{ "filename": "plan-<slug>.prompt.md", "path": "…" }`

**Errors:**
- `ValueError` if the derived filename already exists.

---

### `ideate_prd`

Interactive tool that guides the user through a pre-PRD ideation journey using MCP elicitation and LLM sampling. Collects feature title and structured details (problem statement, target audience, success metrics, scope, priority, constraints, dependencies, acceptance criteria, technical notes) via two elicitation rounds, then uses `ctx.sample()` to elaborate a full PRD draft. Falls back to a template-based draft if sampling is unavailable.

No parameters (interacts with the user via `ctx.elicit()`).

**Returns:**
```json
{
  "saved": true,
  "draft": "# PRD: My Feature\n…",
  "filename": "prd-my-feature.md",
  "path": "/abs/path/to/prds/prd-my-feature.md",
  "feature_name": "My Feature",
  "sampling_used": true
}
```

When a duplicate is detected or the user cancels, returns `saved=false` with a `reason` field instead.

---

## Workflow Management

### `get_workflow_status`

Returns a structured snapshot of `index.md`. Read-only — does not modify any file.

**Returns:**
```json
{
  "features": [
    {
      "prd": "prd-foo.md",
      "spec": "spec-foo-bar.md",
      "feature": "Foo Bar",
      "plan_status": "🟢 Done",
      "elicitation": "✅ Consolidated",
      "implementation": "✅ Concluído"
    }
  ],
  "summary": { "done": 1, "in_progress": 0, "todo": 0 }
}
```

Returns `{ "features": [], "summary": { … } }` if `index.md` does not exist.

---

### `sync_index`

Reconciles the filesystem artifacts with `index.md`.

- **Pass 1** — PRD files not yet tracked in `index.md` are inserted with default statuses (`plan_status="⏳ Waiting for Spec"`, `implementation="❌ Todo"`).
- **Pass 2** — Rows with an empty spec field are updated when a matching spec file exists on disk; rows whose `plan_status` is not `"🟢 Done"` are updated when a matching plan file is found.

No parameters.

**Returns:**
```json
{ "added": ["prd-new.md"], "updated": ["prd-old.md"], "skipped": ["prd-done.md"] }
```

---

### `update_index`

Upserts a row in the `index.md` table. If a row with `prd_filename` already exists it is replaced in place; otherwise a new row is appended.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `prd_filename` | `str` | Used as the lookup key in the table. |
| `spec_filename` | `str` | Spec column value. |
| `feature_name` | `str` | Feature column value. |
| `plan_status` | `str` | See valid values below. |
| `implementation_status` | `str` | See valid values below. |
| `elicitation_status` | `str` | Elicitation column value. Default: `"—"`. |
| `force` | `bool` | Must be `true` to allow the write. Default: `false`. |

**Returns:** Updated content of `index.md` as a string.

**Errors:**
- `PermissionError` if `force=False`.

---

### `advance_stage`

Updates `plan_status` and `implementation_status` for an existing feature row, looked up by `feature_name`.

| Parameter | Type | Valid values |
| :--- | :--- | :--- |
| `plan_status` | `str` | `"⏳ Waiting for Spec"` · `"🟡 Spec Draft"` · `"🟡 Pending"` · `"🟢 Done"` |
| `implementation_status` | `str` | `"❌ Todo"` · `"🔄 In Progress"` · `"✅ Concluído"` |

**Returns:** Updated content of `index.md`.

**Errors:**
- `ValueError` if either status value is not in the valid set.
- `ValueError` if `feature_name` is not found in the table.
- `FileNotFoundError` if `index.md` does not exist.

---

## Inspection

### `check_duplicate`

Checks whether any PRD, Spec, or Plan file already exists for a given feature name. Read-only.

Matching strategy:
1. Exact slug match (`prd-<slug>*.md`)
2. Token match — each slug token ≥ 4 characters is searched independently to catch partial overlaps and camelCase naming variants.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `feature_name` | `str` | Feature name to check. |

**Returns:**
```json
{ "has_duplicate": false, "matches": [] }
```
or
```json
{ "has_duplicate": true, "matches": ["/abs/path/to/prd-…md"] }
```

---

### `list_artefacts`

Lists artifacts with metadata (size, last-modified timestamp).

| Parameter | Type | Valid values |
| :--- | :--- | :--- |
| `artefact_type` | `str` | `"prd"` · `"spec"` · `"plan"` · `"all"` |

**Returns:** Array of objects:
```json
[
  {
    "filename": "prd-user-auth.md",
    "size_bytes": 1024,
    "modified_at": "2026-03-15T14:22:00"
  }
]
```
When `artefact_type` is `"all"`, each object includes an additional `"type"` field (`"prd"`, `"spec"`, or `"plan"`).
