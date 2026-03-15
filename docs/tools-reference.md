# Tools Reference

All tools are registered with FastMCP and exposed over the MCP protocol. Clients call them by name.

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
      "implementation": "✅ Concluído"
    }
  ],
  "summary": { "done": 1, "in_progress": 0, "todo": 0 }
}
```

Returns `{ "features": [], "summary": { … } }` if `index.md` does not exist.

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

**Returns:** Updated content of `index.md` as a string.

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
