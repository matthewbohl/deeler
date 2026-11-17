#!/usr/bin/env python3
"""Read only manifests from successful publications, never failed candidates."""
import io
import json
import os
from pathlib import Path
import zipfile
from github_api import request as get


root = 'https://api.github.com/repos/' + os.environ['GITHUB_REPOSITORY']
runs = json.loads(get(root + '/actions/workflows/publish.yaml/runs?status=success&branch=main&per_page=15'))
Path('previous').mkdir(exist_ok=True)
for run in runs['workflow_runs']:
    artifacts = json.loads(get(run['artifacts_url']))
    matches = [a for a in artifacts['artifacts'] if a['name'] == 'release-manifest' and not a['expired']]
    if not matches:
        continue
    archive = zipfile.ZipFile(io.BytesIO(get(matches[0]['archive_download_url'])))
    # Fixed names only: never extract arbitrary archive paths.
    for name in ('versions.json', 'release.json'):
        Path('previous', name).write_bytes(archive.read(name))
    release = json.loads(Path('previous/release.json').read_text())
    with open(os.environ['GITHUB_OUTPUT'], 'a') as target:
        target.write('image=' + release['image'] + '\n')
    print('Previous passing release found.')
    break
else:
    print('No previous release manifest; initial release/upgrade baseline unavailable.')
