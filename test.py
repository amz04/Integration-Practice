# test.py — run the arb_code snippet the way the platform does
import os
import requests


def load_env(path=".env"):
    """Minimal .env loader (no external dependency). Existing os.environ wins."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


load_env()

notion_token = os.environ.get("NOTION_TOKEN")
page_id = os.environ.get("NOTION_PAGE_ID")

if not notion_token or notion_token == "YOUR_NOTION_TOKEN":
    raise SystemExit("Set NOTION_TOKEN in your .env file (see .env.example).")
if not page_id or page_id == "YOUR_PAGE_ID":
    raise SystemExit("Set NOTION_PAGE_ID in your .env file (see .env.example).")

# 1) Fake what the platform injects at execute time
env = {
    "requests": requests,
    "input_data": {
        "page_id": page_id,
        "task": "Follow up with the team",
    },
    "credential_value": {"notion_token": notion_token},
    "credential": {},                                  # the schema; not needed here
    "credential_type": "access_token",
    "action": {"endpoint": "https://api.notion.com/v1/blocks"},
}

# 2) Load the snippet exactly as-is and run it the way the platform does
with open("notionArbCode.py") as f:
    exec(f.read(), env)

# 3) Read the variable the platform would read
print("result:", env.get("result"))
