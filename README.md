# Notion Add-a-Task Integration

A platform integration action that appends a checkable to-do item to a Notion page via the Notion REST API.

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

The credential is a Notion internal integration token (`notion_token`), sent as an `Authorization: Bearer <token>` header — plus the pinned `Notion-Version: 2022-06-28` — to `PATCH /v1/blocks/{page_id}/children` with a single `to_do` block. A page *is* a block, so the page ID works directly as the parent.

The URL is built from `action['endpoint']` (`https://api.notion.com/v1/blocks`) rather than hardcoded, so changing the action's endpoint changes where the call goes.

## Prerequisites

1. notion.so/my-integrations → **New integration** → Internal. Copy the token (`ntn_…`).
2. **Share your to-do page with the integration**: open the page → ••• → Connections → add it. A valid token grants zero access on its own; skipping this gives `404 object_not_found` on every call.
3. The page ID is the 32-char hex string in the page's URL (dashes optional).

## Running it locally

```bash
cd Notion_Integration
cp .env.example .env      # add your NOTION_TOKEN and NOTION_PAGE_ID
pip install requests
python test.py
```

`test.py` mocks the platform's injected scope, executes `notionArbCode.py` unmodified, and prints the returned `result`. On success a fresh ☐ item appears at the bottom of the page.

Token sanity check, no service involved — `200` plus a `bot` user means the token is good, `401` means it's wrong or revoked:

```bash
curl https://api.notion.com/v1/users/me \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H "Notion-Version: 2022-06-28"
```

## Wiring it into the service

All paths are prefixed with `BASE_URL/v1` (locally `http://localhost:8000/v1`). Identity comes entirely from headers — a `404` right after creating something is almost always a mismatched `workspace-id`.

### 1 · Create the integration definition
`POST /organization/integrations` — headers: `organization-id`, `workspace-id`

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

Returns `id` (integration_id) and `latest_version_id` (**integration_version_id** — everything below attaches to it).

### 2 · Add the credential
`POST /organization/integrations/v/{integration_version_id}/credentials` — headers: `workspace-id`, `organization-id`

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

Returns the **credential_version_id**. The `variable_name` (`notion_token`) is the same key the code reads via `credential_value.get('notion_token')` and the same key used in `credential_data` at connect time — all three must match.

### 3 · Add the action
`POST /organization/integrations/v/{integration_version_id}/actions` — header: `organization-id`

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

Returns the **action_version_id**. To change only the code later: `PATCH /v1/actions/{action_version_id}/arb-code`.

The declared `outputs` must match the keys the code returns — extra keys get dropped by the consumer.

### 4 · Connect it into a workspace
`POST /integrations/credentials/connect` — headers: `user-id`, `organization-id`, `workspace-ids`

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

Returns `active_integration_id`, `active_integration_version_id`, `active_credential_id`, `test_passed`. Note `action_version_id` is **singular** (some older docs say `action_version_ids` — that's wrong), and `group_id` is just another name for `workspace_id`.

### 5 · Run it
`POST /integrations/active/{active_integration_id}/v/{active_integration_version_id}/execute` — header: `user-id`

```json
{
  "action_version_id": "…",
  "input_data": {
    "page_id": "your_shared_page_id",
    "task": "Follow up with the team"
  }
}
```

## Troubleshooting

| Symptom | Likely cause & fix |
| --- | --- |
| `401 unauthorized` | Token wrong or revoked. Re-copy it; check the `credential_data` key is `notion_token`. |
| `404 object_not_found` | Page not shared with the integration, or wrong ID. In Notion: ••• → Connections → add it. |
| Task never appears | You may have passed a database ID. Append works on a *page* — use a page's ID. |
| `429 too many requests` | Notion caps ~3 req/sec. Back off and retry. |
| `test_passed: false` | Bad secret, or `credential_data` key doesn't match the credential's `variable_name`. |
| `404` from the service | Right after creating → `workspace-id` / `organization-id` headers don't match where you created it. |

## Notes

`.env` holds the real token and is gitignored — only `.env.example` is committed. Never hardcode the token in `arb_code`; read it from `credential_value`.
