"""Normalize CLI banners without accepting prefixes of another version."""
import re

def reported_version(output):
    plain = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', output)
    match = re.search(r'(?<![\d.])(\d+\.\d+\.\d+)(?!\d|\.\d)', plain)
    return match.group(1) if match else None
