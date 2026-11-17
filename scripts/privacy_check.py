#!/usr/bin/env python3
"""Source and metadata guard; never print a matched private value."""
import ipaddress
import os
from pathlib import Path
import re
import subprocess
import sys

RULES = {
    'personal filesystem path': re.compile(r'/(?:Users|home)/(?!runner(?:/|\b)|agent(?:/|\b))[A-Za-z0-9_.-]+/'),
    'private machine name': re.compile(r'\b[\w-]+\.(?:local|lan|internal)\b', re.I),
    'private key': re.compile(r'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----'),
    'credential token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16})\b'),
    'provider API key': re.compile(r'\b(?:sk-[A-Za-z0-9_-]{24,}|AIza[A-Za-z0-9_-]{30,})\b'),
}

def findings(text):
    result = [label for label, pattern in RULES.items() if pattern.search(text)]
    for value in re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text):
        try:
            ip = ipaddress.ip_address(value)
        except ValueError:
            continue
        networks = map(ipaddress.ip_network, ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
        if any(ip in net and ip != net.network_address for net in networks):
            result.append('private network address')
    for host in re.findall(r'^\s*HostName\s+(\S+)', text, re.M | re.I):
        if not (host == 'example.com' or host.endswith('.example.com') or host.startswith('${')):
            result.append('non-example SSH hostname')
    for pattern in os.getenv('DEELER_PRIVATE_PATTERNS', '').splitlines():
        if pattern.strip() and pattern.strip().lower() in text.lower():
            result.append('operator-supplied private pattern')
    return sorted(set(result))

def main():
    failures = []
    paths = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z']).decode().split('\0')
    for name in filter(None, paths):
        p = Path(name)
        if p.is_file():
            failures.extend(f'{name}: {label}' for label in findings(p.read_text(errors='replace')))
    metadata = subprocess.check_output(['git', 'log', '--all', '--format=%ae%n%ce'], text=True)
    for address in metadata.splitlines():
        if not address.endswith('@users.noreply.github.com'):
            failures.append('Git metadata: non-noreply identity requires explicit review')
    if failures:
        print('\n'.join(sorted(set(failures))), file=sys.stderr)
        return 1
    print('Privacy checks passed for source and reachable commit identities.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
