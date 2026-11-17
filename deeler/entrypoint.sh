#!/bin/bash
set -euo pipefail

if [[ ! -s /run/herdr-authorized-keys ]]; then
    echo 'Mount a nonempty authorized_keys file at /run/herdr-authorized-keys.' >&2
    exit 1
fi
# Check public-key syntax without printing key contents.
ssh-keygen -l -f /run/herdr-authorized-keys >/dev/null
install -d -m 755 /etc/ssh/authorized_keys
install -m 644 /run/herdr-authorized-keys /etc/ssh/authorized_keys/agent
mkdir -p /run/sshd /var/lib/herdr-ssh
chmod 700 /var/lib/herdr-ssh
if [[ ! -f /var/lib/herdr-ssh/ssh_host_ed25519_key ]]; then
    ssh-keygen -q -t ed25519 -N '' -f /var/lib/herdr-ssh/ssh_host_ed25519_key
fi
chown agent:agent /home/agent
install -d -o agent -g agent -m 700 /home/agent/projects

gosu agent bash <<'BOOTSTRAP'
set -euo pipefail
umask 077
mkdir -p "$HOME/.config/herdr" "$HOME/projects" \
    "$HOME/.claude" "$HOME/.codex" "$HOME/.gemini" \
    "$HOME/.config/opencode" "$HOME/.pi/agent" "$HOME/.copilot"
if [[ ! -f "$HOME/.config/herdr/config.toml" ]]; then
    cp /opt/herdr-defaults/config.toml "$HOME/.config/herdr/config.toml"
fi
if [[ ! -f "$HOME/.bashrc" ]]; then
    cp /opt/herdr-defaults/bashrc "$HOME/.bashrc"
elif ! grep -Fq '/opt/herdr-defaults/bashrc' "$HOME/.bashrc" && ! grep -Fq '/opt/herdr-automatic-rename/shell/hook.bash' "$HOME/.bashrc"; then
    printf '\nsource /opt/herdr-defaults/bashrc\n' >> "$HOME/.bashrc"
fi
if [[ ! -f "$HOME/.bash_profile" ]]; then
    printf '[[ -f ~/.bashrc ]] && source ~/.bashrc\n' > "$HOME/.bash_profile"
fi
for integration in claude codex opencode pi copilot; do
    herdr integration install "$integration"
done
# Gemini has screen-state detection but no built-in integration in Herdr 0.9.5.
herdr plugin link --enabled /opt/herdr-automatic-rename
BOOTSTRAP

/usr/sbin/sshd -t
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
