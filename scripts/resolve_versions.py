#!/usr/bin/env python3
"""Resolve upstream stable releases once; images consume this immutable snapshot."""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import urllib.error
import urllib.request

PACKAGES = {
    'codex': '@openai/codex', 'claude': '@anthropic-ai/claude-code',
    'gemini': '@google/gemini-cli', 'opencode': '@opencode/cli',
    'pi': '@mariozechner/pi-coding-agent', 'copilot': '@github/copilot',
}


def fetch(url, headers=None):
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def github(path):
    headers = {'User-Agent': 'deeler-release-discovery'}
    if os.getenv('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    return fetch('https://api.github.com/' + path, headers)


def fingerprint(manifest):
    stable = {k: v for k, v in manifest.items() if k != 'resolved_at'}
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()


def resolve():
    now = dt.datetime.now(dt.timezone.utc)
    manifest = {'schema': 1, 'resolved_at': now.isoformat(),
                'os_refresh': now.strftime('%G-W%V'), 'agents': {}}
    for command, package in PACKAGES.items():
        info = fetch('https://registry.npmjs.org/' + package + '/latest')
        version = info['version']
        if info['name'] != package or not re.fullmatch(r'\d+\.\d+\.\d+', version):
            raise ValueError(f'{command}: latest is not a stable release')
        manifest['agents'][command] = {'package': package, 'version': version}
    herdr = github('repos/herdrdev/herdr/releases/latest')
    herdr_version = herdr['tag_name'].removeprefix('v')
    if not re.fullmatch(r'\d+\.\d+\.\d+', herdr_version):
        raise ValueError('Herdr latest is not a stable release')
    manifest['herdr'] = {'version': herdr_version, 'assets': {}}
    for arch in ('x86_64', 'aarch64'):
        key = 'linux-' + arch
        asset = next(a for a in herdr['assets'] if a['name'] == 'herdr-' + key)
        url = asset['browser_download_url']
        sha = (asset.get('digest') or '').removeprefix('sha256:')
        if not url.startswith('https://github.com/herdrdev/herdr/releases/download/'):
            raise ValueError('Unexpected Herdr download host')
        if not re.fullmatch(r'[a-f0-9]{64}', sha):
            raise ValueError('Invalid Herdr checksum')
        manifest['herdr']['assets'][key] = {'url': url, 'sha256': sha}
    try:
        release = github('repos/qu8n/herdr-automatic-rename/releases/latest')
        ref = release['tag_name']
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        ref = 'main'  # Upstream has no stable releases; snapshot its default branch.
    commit = github('repos/qu8n/herdr-automatic-rename/commits/' + ref)['sha']
    if not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise ValueError('Invalid plugin revision')
    manifest['rename'] = {'ref': commit, 'channel': ref}
    token = fetch('https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/node:pull')['token']
    request = urllib.request.Request(
        'https://registry-1.docker.io/v2/library/node/manifests/24-bookworm-slim',
        headers={'Authorization': 'Bearer ' + token,
                 'Accept': 'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json'})
    with urllib.request.urlopen(request, timeout=45) as response:
        digest = response.headers['Docker-Content-Digest']
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', digest):
        raise ValueError('Invalid base image digest')
    manifest['base_image'] = 'node:24-bookworm-slim@' + digest
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='deeler/versions.json')
    parser.add_argument('--previous')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    manifest = resolve()
    changed = True
    if args.previous and os.path.isfile(args.previous):
        with open(args.previous) as source:
            changed = fingerprint(manifest) != fingerprint(json.load(source))
        release_path = os.path.join(os.path.dirname(args.previous), 'release.json')
        if os.getenv('GITHUB_SHA') and os.path.isfile(release_path):
            with open(release_path) as source:
                changed |= json.load(source)['source_sha'] != os.environ['GITHUB_SHA']
    with open(args.output, 'w') as target:
        json.dump(manifest, target, indent=2, sort_keys=True)
        target.write('\n')
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as target:
            target.write(f'build={str(changed or args.force).lower()}\n')
            target.write(f'base={manifest["base_image"]}\n')
            target.write(f'os_refresh={manifest["os_refresh"]}\n')
    print('Resolved stable releases; ' + ('build required.' if changed or args.force else 'no changes.'))


if __name__ == '__main__':
    main()
