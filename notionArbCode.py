# Credential (decrypted) — key matches the credential's variable_name
token = credential_value.get('notion_token')

# Inputs — handle both the plain value and the {"value": ...} wrapper
def _val(key, default=''):
    v = input_data.get(key, default)
    return v.get('value', default) if isinstance(v, dict) else v

page_id = _val('page_id')
task = _val('task')

if not token:
    result = {'success': False, 'error': 'Missing notion_token in credentials'}
elif not page_id or not task:
    result = {'success': False, 'error': 'page_id and task are required'}
else:
    # A page is a block, so children are appended at /v1/blocks/{page_id}/children
    url = f"{action['endpoint']}/{page_id}/children"
    try:
        response = requests.patch(
            url,
            headers={
                'Authorization': f'Bearer {token}',
                'Notion-Version': '2022-06-28',
                'Content-Type': 'application/json',
            },
            json={'children': [{
                'object': 'block',
                'type': 'to_do',
                'to_do': {
                    'rich_text': [{'type': 'text', 'text': {'content': task}}],
                    'checked': False,
                },
            }]},
            timeout=30,
        )
        if response.status_code // 100 == 2:
            body = response.json()
            result = {'success': True, 'result': {
                'object': body.get('object', ''),
                'results': body.get('results', []),
            }}
        else:
            result = {'success': False,
                      'error': f'Notion API error: {response.status_code} - {response.text}'}
    except Exception as e:
        result = {'success': False, 'error': f'Request failed: {str(e)}'}
