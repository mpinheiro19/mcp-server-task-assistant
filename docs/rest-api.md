# REST API Reference

MCP Assistant exposes its artifact lifecycle operations over HTTP via a FastAPI layer. This enables browser-based access, third-party integrations, and scripted clients without an MCP-aware host.

---

## Running the Server

```bash
uv run mcp-assistant-api
```

The server starts on `http://0.0.0.0:8000` by default.

### Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `API_HOST` | `0.0.0.0` | Bind address |
| `API_PORT` | `8000` | Port |
| `API_RELOAD` | `false` | Enable hot-reload (dev only) |
| `CORS_ORIGINS` | _(empty)_ | Comma-separated allowed origins |
| `ENABLE_OAUTH2` | `false` | Enable OAuth2 authentication |
| `OAUTH2_CLIENT_ID` | _(empty)_ | OAuth2 provider client ID |
| `OAUTH2_CLIENT_SECRET` | _(empty)_ | OAuth2 provider client secret |
| `OAUTH2_AUTHORIZE_URL` | GitHub authorize URL | Provider authorization endpoint |
| `OAUTH2_TOKEN_URL` | GitHub token URL | Provider token endpoint |
| `OAUTH2_USERINFO_URL` | GitHub user API | Provider userinfo endpoint |
| `OAUTH2_CALLBACK_URL` | `http://localhost:8000/auth/callback` | Registered redirect URI |
| `OAUTH2_REDIRECT_AFTER_LOGIN` | `/` | Where to redirect after login |
| `SESSION_SECRET_KEY` | `change-me-in-production` | Signing key for session cookies |

---

## CORS Setup

CORS is opt-in. No wildcard default is used, so cross-origin requests are blocked unless configured:

```bash
CORS_ORIGINS="http://localhost:3000,https://app.example.com" uv run mcp-assistant-api
```

---

## Authentication

Authentication is feature-flagged behind `ENABLE_OAUTH2=true`. When the flag is off, all `/api/v1/*` routes are publicly accessible.

### Auth Flow

```
Browser                    API                     GitHub
  |                         |                          |
  |-- GET /auth/login ------>|                          |
  |<-- 302 redirect ---------|                          |
  |                          |-- POST /login/oauth -->  |
  |<---------- code ---------|                          |
  |-- GET /auth/callback --->|                          |
  |                          |-- POST token exchange -> |
  |                          |<-- access_token ---------|
  |                          |-- GET /user -----------> |
  |                          |<-- user info ------------|
  |<-- 302 + session cookie--|                          |
```

The session is stored as a signed `itsdangerous` cookie (httponly, samesite=lax, 24h TTL). To migrate to a different OIDC provider (Google, Auth0, Keycloak), update only the `OAUTH2_*` env vars.

### Auth Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/auth/login` | Redirect to provider (or `{"enabled":false}`) |
| `GET` | `/auth/callback` | Exchange code, set session cookie |
| `GET` | `/auth/me` | Return current user info |
| `POST` | `/auth/logout` | Clear session cookie |

---

## OpenAPI

Interactive docs are always available (no auth required):

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

---

## Health Check

```
GET /health
```

Response:
```json
{"status": "ok"}
```

Always returns 200. No authentication required.

---

## Endpoints

All v1 endpoints are prefixed with `/api/v1/`.

### Artifacts

#### Create PRD

```
POST /api/v1/artifacts/prds
```

Request body:
```json
{
  "feature_name": "My Feature",
  "content": "# PRD content here"
}
```

Response `201`:
```json
{
  "filename": "prd-my-feature.md",
  "path": "/home/user/Codes/copilot-assistants/prds/prd-my-feature.md"
}
```

Error `409` — duplicate filename.

---

#### Create Spec

```
POST /api/v1/artifacts/specs
```

Request body:
```json
{
  "feature_name": "Sub Feature",
  "prd_filename": "prd-my-feature.md",
  "content": "# Spec content"
}
```

Response `201`:
```json
{
  "filename": "spec-my-feature-sub-feature.md",
  "path": "..."
}
```

---

#### Create Plan

```
POST /api/v1/artifacts/plans
```

Request body:
```json
{
  "feature_name": "Deploy Pipeline",
  "content": "# Plan content"
}
```

Response `201`:
```json
{
  "filename": "plan-deploy-pipeline.prompt.md",
  "path": "..."
}
```

---

#### List Artifacts

```
GET /api/v1/artifacts?type=prd|spec|plan|all
```

Query param `type` (default: `all`).

Response `200`:
```json
{
  "items": [
    {
      "filename": "prd-my-feature.md",
      "size_bytes": 1024,
      "modified_at": "2026-03-21T10:00:00",
      "type": "prd"
    }
  ],
  "total": 1
}
```

---

### Workflow

#### Get Status

```
GET /api/v1/workflow/status
```

Response `200`:
```json
{
  "features": [
    {
      "prd": "prd-foo.md",
      "spec": "spec-foo.md",
      "feature": "Foo Feature",
      "plan_status": "🟢 Done",
      "implementation": "✅ Concluído"
    }
  ],
  "summary": {
    "done": 1,
    "in_progress": 0,
    "todo": 0
  }
}
```

---

#### Update Index

```
PUT /api/v1/workflow/index
```

Request body:
```json
{
  "prd_filename": "prd-foo.md",
  "spec_filename": "spec-foo.md",
  "feature_name": "Foo Feature",
  "plan_status": "🟢 Done",
  "implementation_status": "✅ Concluído"
}
```

Adds a new row or updates an existing row matched by `prd_filename`.

Response `200`:
```json
{"content": "...updated index.md content..."}
```

---

#### Advance Stage

```
PATCH /api/v1/workflow/features/{feature_name}/stage
```

Request body:
```json
{
  "plan_status": "🟢 Done",
  "implementation_status": "✅ Concluído"
}
```

Valid `plan_status` values: `⏳ Waiting for Spec`, `🟡 Spec Draft`, `🟡 Pending`, `🟢 Done`

Valid `implementation_status` values: `❌ Todo`, `🔄 In Progress`, `✅ Concluído`

Response `200`:
```json
{"content": "...updated index.md content..."}
```

Errors:
- `404` — index.md not found
- `409` — feature not found or invalid status value

---

#### Check Duplicate

```
GET /api/v1/workflow/duplicates?feature_name=My+Feature
```

Response `200`:
```json
{
  "has_duplicate": true,
  "matches": [
    "/home/user/Codes/copilot-assistants/prds/prd-my-feature.md"
  ]
}
```

---

### Resources

Read-only access to artifact files and lists.

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/resources/index` | Contents of `index.md` |
| `GET` | `/api/v1/resources/projects` | List of projects in `~/Codes` |
| `GET` | `/api/v1/resources/prds` | List of PRD filenames |
| `GET` | `/api/v1/resources/specs` | List of Spec filenames |
| `GET` | `/api/v1/resources/plans` | List of Plan filenames |
| `GET` | `/api/v1/resources/prds/{filename}` | Contents of a specific PRD |
| `GET` | `/api/v1/resources/specs/{filename}` | Contents of a specific Spec |
| `GET` | `/api/v1/resources/plans/{filename}` | Contents of a specific Plan |

List response shape:
```json
{"items": ["prd-foo.md", "prd-bar.md"], "total": 2}
```

File response shape:
```json
{"filename": "prd-foo.md", "content": "# PRD content..."}
```

Error `404` — file not found.

---

## Error Format

All errors use a consistent JSON format:

```json
{
  "error": "conflict",
  "detail": "PRD 'prd-foo.md' já existe.",
  "status_code": 409
}
```

| Status | Meaning |
| :--- | :--- |
| `401` | Not authenticated (ENABLE_OAUTH2=true, no session) |
| `404` | Resource not found |
| `409` | Conflict (duplicate artifact, feature not found, invalid status) |
| `422` | Validation error (invalid request body or query param) |
| `500` | Unexpected server error |
