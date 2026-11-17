#!/usr/bin/env python3
"""Install the exact discovered snapshot; never resolve latest during a build."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request


def run(command, timeout=120):
    subprocess.run(command, check=True, timeout=timeout)


manifest = json.loads(Path('/opt/deeler/versions.json').read_text())
arch = subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip()
key = {'amd64': 'linux-x86_64', 'arm64': 'linux-aarch64'}[arch]
asset = manifest['herdr']['assets'][key]
with urllib.request.urlopen(asset['url'], timeout=120) as response:
    data = response.read()
if hashlib.sha256(data).hexdigest() != asset['sha256']:
    raise RuntimeError('Herdr release checksum mismatch')
binary = Path('/usr/local/bin/herdr')
binary.write_bytes(data)
binary.chmod(0o755)
packages = [f'{info["package"]}@{info["version"]}' for info in manifest['agents'].values()]
run(['gosu', 'agent', 'npm', 'install', '-g', '--no-audit', '--no-fund', *packages], timeout=1200)
run(['gosu', 'agent', 'npm', 'cache', 'clean', '--force'])
run(['chown', '-R', 'root:root', '/opt/agent-tools'])
for name in manifest['agents']:
    os.symlink('/opt/agent-tools/bin/' + name, '/usr/local/bin/' + name)
plugin = '/opt/herdr-automatic-rename'
ref = manifest['rename']['ref']
run(['git', 'init', plugin])
run(['git', '-C', plugin, 'remote', 'add', 'origin', 'https://github.com/qu8n/herdr-automatic-rename.git'])
run(['git', '-C', plugin, 'fetch', '--depth=1', 'origin', ref])
run(['git', '-C', plugin, 'checkout', '--detach', 'FETCH_HEAD'])
actual = subprocess.check_output(['git', '-C', plugin, 'rev-parse', 'HEAD'], text=True).strip()
if actual != ref:
    raise RuntimeError('Plugin revision mismatch')
for name in ('herdr', *manifest['agents']):
    print(f'Checking {name}', flush=True)
    result = subprocess.check_output(['gosu', 'agent', name, '--version'], text=True, timeout=90)
    expected = manifest['herdr']['version'] if name == 'herdr' else manifest['agents'][name]['version']
    if expected not in result:
        raise RuntimeError(f'{name}: installed version does not match snapshot')
    print(f'{name}: {expected}', flush=True)
