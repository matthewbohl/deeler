#!/usr/bin/env python3
"""One maintained issue: sanitized stage statuses, no raw logs."""
import json
import os
from github_api import request

root = 'https://api.github.com/repos/' + os.environ['GITHUB_REPOSITORY']
title = '[deeler] Update verification failed'
states = json.loads(os.environ['JOB_RESULTS'])
failed = any(item.get('result') == 'failure' for item in states.values())
issues = json.loads(request(root + '/issues?state=open&per_page=100'))
matches = [issue for issue in issues if issue['title'] == title and 'pull_request' not in issue]
if failed:
    url = 'https://github.com/' + os.environ['GITHUB_REPOSITORY'] + '/actions/runs/' + os.environ['GITHUB_RUN_ID']
    body = ('An update failed its discovery, verification, or publication gate. '
            'The last passing image remains the deployment choice.\n\n'
            f'Workflow: {url}\n\n' + '\n'.join(f'- {name}: {item["result"]}' for name, item in states.items()))
    if matches:
        request(matches[0]['url'], {'body': body}, 'PATCH')
    else:
        request(root + '/issues', {'title': title, 'body': body}, 'POST')
elif states.get('promote', {}).get('result') == 'success':
    for issue in matches:
        request(issue['url'], {'state': 'closed', 'state_reason': 'completed'}, 'PATCH')
