# deeler

Serving up shared agent sessions: a nod to Heeler and a dealer.

One persistent [Herdr TUI](https://herdr.dev/tui/) server with six command-line
agents, accessed from your machines over SSH.
All agents run as the unprivileged `agent` user. Only Herdr and SSH start at
container boot; agent sessions start when you launch them.

| Agent | Command | Pinned version | Herdr integration |
| --- | --- | --- | --- |
| Codex | `codex` | 0.169.0 | Installed |
| Claude Code | `claude` | 2.1.326 | Installed |
| Gemini CLI | `gemini` | 0.68.0 | Screen detection only; less tested |
| OpenCode | `opencode` | 2.3.0 | Installed |
| Pi | `pi` | 0.73.1 | Installed |
| GitHub Copilot CLI | `copilot` | 1.0.113 | Installed |

Herdr TUI is pinned to 0.9.5, with verified release checksums for amd64 and arm64.
Automatic tab naming is bundled at commit
`a99754357fdea3119c430fd0cad822eef9047895`. Node/Debian packages refresh on rebuild.

## Pull the published image

Image address: `ghcr.io/YOUR_GITHUB_USER/deeler:latest`. Replace
`YOUR_GITHUB_USER` with the publishing account and set `DEELER_IMAGE` in your
stack environment before starting Compose.
The initial registry build/publication must succeed before this address can be
pulled. For unattended deployments, pin a published `sha-<full commit>` tag or
image digest instead of following `latest`.

On your server, you only need `docker-compose.yaml` and an `authorized_keys` file;
the image build folder is not needed. Put them beside your existing Compose
file. Add public SSH keys from each authorized client, one per line:

```sh
cp /path/to/your/public-key.pub authorized_keys
chmod 644 authorized_keys
docker compose -f compose.yaml -f docker-compose.yaml config --quiet
docker compose -f compose.yaml -f docker-compose.yaml pull herdr
docker compose -f compose.yaml -f docker-compose.yaml up -d herdr
```

Either keep using both `-f` arguments or merge `services.herdr` and the two
volume entries into your existing Compose file. If the main file has a different
name, substitute it above. Relative paths resolve from the first Compose file.
There is no top-level project name. Add optional values from `.env.example` to
your existing `.env`; do not overwrite your stack's environment file.

The image contains code and tools, with no provider credentials or SSH keys.
If the GHCR package remains private, your server must log into GHCR to pull it. A
public package allows anonymous pulls.

## Published port and client setup

The service publishes **TCP 2222 on your server → TCP 22 inside the container**,
bound to all IPv4 host interfaces by default. Allow TCP 2222 through the host's
firewall from the client networks you intend to use. You can bind just its
LAN/VPN address with `HERDR_BIND_ADDRESS`; `HERDR_SSH_PORT` changes the host
port if 2222 is already occupied. No HTTP, TLS reverse proxy, or additional
Herdr TCP port is involved: Herdr's local socket is reached over SSH.

Add this SSH alias on each client machine:

```sshconfig
Host deeler-server
    HostName agents.example.com
    Port 2222
    User agent
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    ServerAliveInterval 30
    ServerAliveCountMax 3
```

Use a key whose public half is listed in `authorized_keys`. Check SSH first,
then connect your Herdr TUI client:

```sh
ssh deeler-server 'herdr --version'
herdr --remote deeler-server
```

To keep your server in your local Herdr sidebar, register its default session:

```sh
herdr machine add deeler-server --label deeler --remote-session default
herdr
```

This follows the [official SSH machine connection workflow](https://herdr.dev/tui/docs/connecting-machines/).
Use compatible Herdr TUI clients; 0.9.5 matches the pinned server. If setup asks
to replace the remote binary, update/rebuild the image deliberately instead.
All clients should select the same default session to share workspaces.

You can also render the TUI entirely inside an ordinary SSH session:

```sh
ssh -t deeler-server 'cd ~/projects && exec herdr'
```

Remote Herdr clients use local UI preferences: merge the `[ui]` section from
`config.toml` into each client's config for the expanded sidebar and no tab-name
prompt. Preserve unrelated local settings. The SSH-hosted TUI uses the
container's UI settings directly. Default command keys are retained.

Compare the container's SSH host-key fingerprint when first connecting:

```sh
docker compose exec herdr ssh-keygen -lf /var/lib/herdr-ssh/ssh_host_ed25519_key.pub
```

SSH permits public-key authentication only; password and root login are disabled.

## Authenticate only the agents you use

Connect to a shell inside the container:

```sh
docker compose exec --user agent herdr bash -l
```

Then launch the agents you want:

| Agent | First-time setup |
| --- | --- |
| Codex | `codex login --device-auth` |
| Claude Code | Run `claude` and follow login prompts |
| Gemini CLI | Run `gemini` and choose its authentication method |
| OpenCode | Run `opencode`, then `/connect` and `/models` |
| Pi | Run `pi`, then `/login` and `/model` |
| Copilot | Run `copilot`, then `/login` |

Use each provider's eligible account or API credentials. Tools that offer free
or local models may run without a paid login when explicitly selected; deeler
itself never launches them or makes model calls at startup. Separate agent
settings, credentials, and histories all live in the persistent home volume.
Herdr installs integrations into pre-created config directories without logging
into any provider. Gemini has no built-in restore integration in this Herdr pin.

Codex settings: `~/.codex/config.toml`. Claude settings:
`~/.claude/settings.json`. Configure MCP servers, skills, and permissions in the
agent that will use them. Nothing from your desktop account is imported.

Clone repositories into `~/projects` and start agents from Herdr panes in their
project directories. Use separate Git worktrees when agents edit concurrently.
All six agents share one Unix account; this is a single-operator environment.
Herdr supplies session visibility, not a durable cross-machine task queue, and
does not import existing ChatGPT or Claude UI conversations.

## Herdr preferences and persistence

Following [Quan Nguyen's suggestions](https://www.qu8n.com/posts/better-herdr-config),
deeler uses the default server, starts with the sidebar expanded, disables new
tab name prompts, installs agent integrations, and enables automatic naming.
**Default keybindings remain unchanged**, including the `Ctrl+b` prefix.

The first boot seeds `~/.config/herdr/config.toml`; subsequent boots preserve
edits. Run `herdr server reload-config` after editing it. Integrations and the
bundled naming-plugin link are refreshed at startup. The Bash hook and
`HERDR_PROCESS_DETECTION=child-groups` support automatic naming in containers.

The `herdr-agent-home` volume holds repositories, settings, credentials, and
history. `herdr-ssh-host-keys` preserves the SSH identity. `authorized_keys` is
mounted read-only; restart the container after changing it.

Disconnecting clients leaves processes running. Container restart ends those
processes; Herdr can restore layout and supported agent conversations. Arbitrary
shell commands do not automatically resume. Back up both volumes while stopped
before upgrades; home backups contain credentials and private code. Keep the
same Compose project/volume names. `docker compose down` retains volumes;
`docker compose down -v` deletes them. For rollback, select the old image digest
and restore matching volume backups if state formats changed.

## Build locally

The optional build override retains a local development path:

```sh
docker compose -f docker-compose.yaml -f docker-compose.build.yaml up -d --build
```

The Dockerfile and its supporting files are in `deeler/`. Agent version pins
are build arguments; changing Herdr also requires updating both binary
checksums. The Docker build verifies every CLI's `--version` as `agent`.

## Publish through GitHub Actions

The workflow in `.github/workflows/publish.yaml`:

1. Builds an amd64 test image and runs `scripts/smoke-test.sh`.
2. Checks all six binaries, initial integrations, real SSH authentication,
   home persistence, and stable SSH identity across a restart without provider login.
3. On successful main/tag/manual builds, publishes a multi-platform
   `linux/amd64` + `linux/arm64` image to GHCR using `GITHUB_TOKEN`.

Pull requests test without publishing. Main publishes `latest`; every published
build receives `sha-<full commit>`; a Git tag such as `v0.1.0` also publishes
`0.1.0`. Both architectures execute version checks during the image build;
the SSH/runtime smoke test runs on amd64. Workflows use pinned Action commits.

No registry secret is required for Actions: the publish job requests
`packages: write`. If organization policy blocks it, enable the required
Actions/package permissions for this repository. After the first push, make the
`deeler` GHCR package public in its package settings if you want anonymous pulls.
Repository visibility alone does not make a new package public.

To update your server after a successful publication:

```sh
docker compose pull herdr
docker compose up -d herdr
```

Finish active work before replacing the running container. The desktop
preparation environment has no Docker; CI is the initial build/runtime proof.
Provider authentication and native conversation restore still require your
own account-based acceptance test after deployment.

## References

- [Herdr agents](https://herdr.dev/tui/docs/agents/) and
  [integrations](https://herdr.dev/tui/docs/integrations/)
- [Pi Herdsman Compose](https://github.com/boadij/pi-herdsman/blob/main/compose.yaml)
- [Claude Docker development environment](https://github.com/ajsutton/claude-docker)
- [GitHub container publishing](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)
- [OpenCode](https://opencode.ai/docs/),
  [Gemini CLI](https://github.com/google-gemini/gemini-cli),
  [Pi](https://github.com/earendil-works/pi/tree/main/packages/coding-agent),
  [Copilot CLI](https://docs.github.com/en/copilot/concepts/copilot-surfaces/copilot-cli)
