#!/bin/bash
# Runs only disposable containers and volumes; never authenticates any provider.
set -euo pipefail
image=${1:-deeler:candidate}
previous=${2:-}
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
launch() {
docker run -d --init --name "$test_name" \
    --security-opt no-new-privileges:true \
    -p 127.0.0.1::22 \
    -v "$test_home:/home/agent" \
    -v "$test_keys:/var/lib/herdr-ssh" \
    --mount "type=bind,src=$test_dir/client.pub,dst=/run/herdr-authorized-keys,readonly" \
    "$1"
}
start_image="$image"
if [[ -n "$previous" ]]; then
    docker pull "$previous"
    start_image="$previous"
fi
launch "$start_image"
test_port=$(docker port "$test_name" 22/tcp | sed 's/.*://')
remote() {
    ssh -p "$test_port" -i "$test_dir/client" \
        -o BatchMode=yes -o ConnectTimeout=3 \
        -o StrictHostKeyChecking=accept-new \
        -o UserKnownHostsFile="$test_dir/known_hosts" -o HostKeyAlias=deeler-test \
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
if [[ -n "$previous" ]]; then
    remote 'printf persistent > ~/projects/smoke-marker; printf "\n# upgrade sentinel\n" >> ~/.config/herdr/config.toml'
    docker stop -t 60 "$test_name"
    docker rm "$test_name"
    launch "$image"
    test_port=$(docker port "$test_name" 22/tcp | sed 's/.*://')
    ready
    remote 'test "$(cat ~/projects/smoke-marker)" = persistent && grep -q "# upgrade sentinel" ~/.config/herdr/config.toml'
    echo 'Upgrade from previous verified image preserved configuration, data, and SSH identity.'
fi
for agent_cli in herdr codex claude gemini opencode pi copilot; do
    remote "timeout 90s $agent_cli --version"
    remote "timeout 60s $agent_cli --help >/dev/null"
    if [[ "$agent_cli" != herdr ]]; then
        python3 scripts/terminal_probe.py -- docker exec -it --user agent "$test_name" "$agent_cli"
    fi
done
python3 scripts/terminal_probe.py --herdr -- ssh -tt -p "$test_port" -i "$test_dir/client" -o BatchMode=yes -o UserKnownHostsFile="$test_dir/known_hosts" -o HostKeyAlias=deeler-test agent@127.0.0.1 herdr
created=$(remote 'herdr workspace create --cwd /home/agent/projects --label verification --no-focus')
workspace=$(printf '%s' "$created" | jq -er '.result.workspace.workspace_id // .result.workspace.id')
pane=$(printf '%s' "$created" | jq -er '.result.root_pane.pane_id // .result.root_pane.id')
remote "herdr pane run '$pane' 'sleep 20'" >/dev/null
renamed=false
for attempt in {1..15}; do
    if remote "herdr tab list --workspace '$workspace'" | jq -er '.result.tabs[] | (.name // .title // .label // "")' | grep -q sleep; then
        renamed=true
        break
    fi
    sleep 1
done
[[ "$renamed" == true ]] || { echo 'Automatic foreground tab naming failed.' >&2; exit 1; }
remote "herdr workspace close '$workspace'" >/dev/null
remote 'herdr integration status'
remote 'herdr plugin list'
remote 'test -f ~/.claude/hooks/herdr-agent-state.sh && test -f ~/.codex/herdr-agent-state.sh && test -f ~/.pi/agent/extensions/herdr-agent-state.ts && test -f ~/.copilot/hooks/herdr-agent-state.sh && test -d ~/.config/opencode/plugins'
remote 'printf persistent > ~/projects/smoke-marker'
docker restart -t 60 "$test_name"
test_port=$(docker port "$test_name" 22/tcp | sed 's/.*://')
ready
# The same known_hosts file requires SSH identity to survive the restart.
remote 'test "$(cat ~/projects/smoke-marker)" = persistent'
echo 'Native binaries, CLI help, terminal startup, Herdr attachment/naming, SSH, upgrade, and persistence passed.'
