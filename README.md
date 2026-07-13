# Notion Add-a-Task Integration

A platform integration action that appends a checkable to-do item to a Notion page.

## Files

| File | Purpose |
| --- | --- |
| `notionArbCode.py` | The action code the platform executes (`arb_code`) |
| `input.json` | Input variable schema (`page_id`, `task`) |
| `output.json` | Output variable schema (`object`, `results`) |
| `test.py` | Local test harness |
| `.env.example` | Template for local credentials |

## How it works

The platform injects `requests`, `input_data`, the decrypted `credential_value`, and `action` into the snippet's scope, runs it, and reads back a `result` variable:

- **Success:** `{"success": True, "result": {"object": "list", "results": [...]}}`
- **Failure:** `{"success": False, "error": "..."}`

The credential is a Notion internal integration token (`notion_token`), sent as `Authorization: Bearer <token>` — plus the pinned `Notion-Version: 2022-06-28` — to `PATCH /v1/blocks/{page_id}/children` with a single `to_do` block. A page *is* a block, so the page ID works directly as the parent. The URL is built from `action['endpoint']` rather than hardcoded.

The page must be shared with the integration (••• → Connections → add it) or every call returns `404 object_not_found`, valid token or not. The page ID is the 32-char hex string in the page's URL.

## Running it locally

```bash
cp .env.example .env      # add your NOTION_TOKEN and NOTION_PAGE_ID
pip install requests
python test.py
```

`test.py` mocks the platform's injected scope, executes `notionArbCode.py` unmodified, and prints the returned `result`. On success a fresh ☐ item appears at the bottom of the page.

## Wiring it into the service

All paths prefixed with `BASE_URL/v1`. Identity comes from headers on every request.

**1 · Define** — `POST /organization/integrations` (headers: `organization-id`, `workspace-id`)

```json
{
  "name": "Notion",
  "icon": "https://www.notion.so/images/favicon.ico",
  "category": ["collaboration_tools"],
  "description": "Add a task to a Notion page",
  "required_plan": "core",
  "status": "active"
}
```

Returns `latest_version_id` — the **integration_version_id** the next two calls attach to.

**2 · Credential** — `POST /organization/integrations/v/{integration_version_id}/credentials`

```json
{
  "name": "Notion Internal Token",
  "auth_type": "access_token",
  "inputs": {
    "notion_token": {
      "display_name": "Internal Integration Token",
      "variable_name": "notion_token",
      "type": "str",
      "is_secret": true,
      "order": 1,
      "placeholder": "ntn_..."
    }
  }
}
```

Returns the **credential_version_id**. `notion_token` is the same key the code reads and the same key used in `credential_data` below — all three must match.

**3 · Action** — `POST /organization/integrations/v/{integration_version_id}/actions`

```json
{
  "name": "Add a Task",
  "description": "Add a checkable to-do item to a Notion page",
  "endpoint": "https://api.notion.com/v1/blocks",
  "inputs":  { "page_id": "str", "task": "str" },
  "outputs": { "object": "str", "results": "array" },
  "arb_code": "…contents of notionArbCode.py as a JSON string…"
}
```

Returns the **action_version_id**. To update just the code later: `PATCH /v1/actions/{action_version_id}/arb-code`.

**4 · Connect** — `POST /integrations/credentials/connect` (headers: `user-id`, `organization-id`, `workspace-ids`)

```json
{
  "name": "My Notion Workspace",
  "integration_version_id": "…",
  "action_version_id": "…",
  "credential_version_id": "…",
  "credential_data": { "notion_token": "ntn_your_real_token" },
  "group_id": "…"
}
```

Returns the **active_integration_id** and `active_integration_version_id`. Note `action_version_id` is singular, and `group_id` means `workspace_id`.

**5 · Run** — `POST /integrations/active/{aid}/v/{avid}/execute` (header: `user-id`)

```json
{
  "action_version_id": "…",
  "input_data": {
    "page_id": "your_shared_page_id",
    "task": "Follow up with the team"
  }
}
```

## Notes

`.env` holds the real token and is gitignored — only `.env.example` is committed. Never hardcode the token in `arb_code`; read it from `credential_value`.
