# Resources Reference

MCP resources expose read-only filesystem state as URIs. Clients can fetch them by URI at any time without side effects.

All resources use the `flow://` scheme.

---

## Static Resources

### `flow://index`

Full content of `index.md` as a string.

Returns `"index.md não encontrado."` if the file does not exist.

---

### `flow://copilot-instructions`

Full content of `copilot-instructions.md` — the governance protocol document.

Returns `"copilot-instructions.md não encontrado."` if the file does not exist.

---

### `flow://projects`

JSON array of directory names under the configured `CODES_ROOT`.

**Example response:** `["mcp-assistant", "copilot-assistants", "my-project"]`

---

### `flow://prds`

JSON array of `*.md` filenames in the `prds/` directory, sorted alphabetically.

Returns `[]` if the directory does not exist.

---

### `flow://specs`

JSON array of `*.md` filenames in the `specs/` directory, sorted alphabetically.

---

### `flow://plans`

JSON array of `*.md` filenames in the `plans/` directory, sorted alphabetically.

---

## Parameterized Resources

### `flow://prd/{filename}`

Content of a specific PRD file.

| Parameter | Description |
| :--- | :--- |
| `filename` | Exact filename, e.g., `prd-user-authentication.md` |

**Errors:** `ValueError` if the file does not exist.

---

### `flow://spec/{filename}`

Content of a specific Spec file.

**Errors:** `ValueError` if the file does not exist.

---

### `flow://plan/{filename}`

Content of a specific Plan file.

**Errors:** `ValueError` if the file does not exist.
