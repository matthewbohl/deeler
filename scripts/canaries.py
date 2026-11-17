#!/usr/bin/env python3
"""Optional bounded CLI requests. Never print model output or credentials."""
import os
import subprocess
import sys

image = sys.argv[1]
selected = [x.strip() for x in os.environ.get('DEELER_CANARY_AGENTS', '').split(',') if x.strip()]
prompt = 'Reply with exactly DEELER_CANARY_OK. Do not use tools or change any files.'
adapters = {
    'codex': ('CODEX_API_KEY', ['codex', 'exec', '--skip-git-repo-check', '--sandbox', 'read-only', prompt]),
    'claude': ('ANTHROPIC_API_KEY', ['claude', '-p', prompt, '--max-turns', '1']),
    'gemini': ('GEMINI_API_KEY', ['gemini', '-p', prompt]),
    'opencode': ('OPENCODE_CANARY_KEY', ['opencode', 'run', prompt]),
    'pi': ('PI_CANARY_KEY', ['pi', '--provider', 'openai', '--print', prompt]),
    'copilot': ('COPILOT_GITHUB_TOKEN', ['copilot', '-p', prompt]),
}
if not selected or any(name not in adapters for name in selected):
    sys.exit('Select supported canary agents explicitly.')
for name in selected:
    key, command = adapters[name]
    if not os.getenv(key):
        sys.exit(f'{name}: required dedicated canary credential is missing')
    env = os.environ.copy()
    container_key = key
    if name in ('pi', 'opencode'):
        model = os.getenv(name.upper() + '_CANARY_MODEL')
        if not model:
            sys.exit(f'{name}: select a small canary model explicitly')
        command += ['--model', model]
        container_key = 'OPENAI_API_KEY'
        env[container_key] = env[key]
        if name == 'opencode' and not model.startswith('openai/'):
            sys.exit('opencode: this canary adapter requires an openai/ model')
    container_name = f'deeler-canary-{os.getpid()}-{name}'
    args = ['docker', 'run', '--rm', '--name', container_name, '--read-only', '--user', 'agent',
            '--cap-drop=ALL', '--security-opt=no-new-privileges:true',
            '--memory=2g', '--cpus=1', '--pids-limit=256',
            '--tmpfs', '/tmp:rw,mode=1777',
            '--tmpfs', '/home/agent:rw,uid=1001,gid=1001,mode=0700',
            '--workdir', '/tmp', '-e', container_key,
            '--entrypoint', '/usr/local/bin/' + command[0], image, *command[1:]]
    try:
        result = subprocess.run(args, env=env, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        sys.exit(f'{name}: canary timed out; output suppressed')
    finally:
        subprocess.run(['docker', 'rm', '-f', container_name], capture_output=True, timeout=30)
    if result.returncode or b'DEELER_CANARY_OK' not in result.stdout:
        sys.exit(f'{name}: canary failed; private output suppressed')
    print(f'{name}: authenticated CLI request passed')
