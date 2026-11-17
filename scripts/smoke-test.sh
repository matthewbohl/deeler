#!/bin/bash
# Runs only disposable containers and volumes; never authenticates any provider.
set -euo pipefail
image=${1:-deeler:smoke}
test_dir=$(mktemp -d)
test_name="deeler-smoke-$$"
test_home="$test_name-home"
test_keys="$test_name-keys"
cleanup() {
    docker logs "$test_name" 2>&1 || true
    docker rm -f "$test_name" >/dev/null 2>&1 || true
    docker volume rm "$test_home" "$test_keys" >/dev/null 2>&1 || true
    rm -rf "$test_dir"
}
trap cleanup EXIT
ssh-keygen -q -t ed25519 -N '' -f "$test_dir/client"
chmod 644 "$test_dir/client.pub"
docker run -d --init --name "$test_name" \
    --security-opt no-new-privileges:true \
    -p 127.0.0.1::22 \
    -v "$test_home:/home/agent" \
    -v "$test_keys:/var/lib/herdr-ssh" \
    --mount "type=bind,src=$test_dir/client.pub,dst=/run/herdr-authorized-keys,readonly" \
    "$image"
test_port=$(docker port "$test_name" 22/tcp | sed 's/.*://')
remote() {
    ssh -p "$test_port" -i "$test_dir/client" \
        -o BatchMode=yes -o ConnectTimeout=3 \
        -o StrictHostKeyChecking=accept-new \
        -o UserKnownHostsFile="$test_dir/known_hosts" \
        agent@127.0.0.1 "$@"
}
ready() {
    for attempt in {1..60}; do
        if remote 'herdr status server' >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done
    echo 'Container failed to become SSH/Herdr ready.' >&2
    return 1
}
ready
for agent_cli in herdr codex claude gemini opencode pi copilot; do
    remote "$agent_cli --version"
done
remote 'herdr integration status'
remote 'herdr plugin list'
remote 'test -f ~/.claude/hooks/herdr-agent-state.sh && test -f ~/.codex/herdr-agent-state.sh && test -f ~/.pi/agent/extensions/herdr-agent-state.ts && test -f ~/.copilot/hooks/herdr-agent-state.sh && test -d ~/.config/opencode/plugins'
remote 'printf persistent > ~/projects/smoke-marker'
docker restart -t 60 "$test_name"
ready
# The same known_hosts file requires SSH identity to survive the restart.
remote 'test "$(cat ~/projects/smoke-marker)" = persistent'
echo 'All agent binaries, initial integrations, SSH, and restart persistence passed.'
