# deeler

Serving up shared agent sessions: a nod to Heeler and a dealer.

One persistent [Herdr TUI](https://herdr.dev/tui/) server with six command-line
agents, accessed from your machines over SSH.
All agents run as the unprivileged `agent` user. Only Herdr and SSH start at
container boot; agent sessions start when you launch them.

| Agent | Command | Release source | Herdr integration |
| --- | --- | --- | --- |
| Codex | `codex` | Stable upstream | Installed |
| Claude Code | `claude` | Stable upstream | Installed |
| Gemini CLI | `gemini` | Stable upstream | Screen detection only; less tested |
| OpenCode | `opencode` | Stable upstream | Installed |
| Pi | `pi` | Stable upstream | Installed |
| GitHub Copilot CLI | `copilot` | Stable upstream | Installed |

Herdr, all six CLIs, and the naming plugin are discovered automatically. Every
image contains its exact version manifest at `/opt/deeler/versions.json`; the
repository snapshot is a local-build fallback, not a manually maintained pin.
Herdr binaries are checksum-verified and the Node base is resolved to its digest.

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
Use a compatible Herdr TUI client; check the image with `herdr --version`. If setup asks
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
into any provider. Gemini currently has screen-state detection and no built-in restore integration.

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

## Automated updates and verification

The GitHub Actions workflow checks stable upstream releases daily at **09:23 UTC**.
It builds when the versions, base-image digest, source commit, or ISO week changes.
The week change refreshes Debian packages even without agent releases. Pushes and
pull requests always test; use **Actions → Update, verify, and publish deeler →
Run workflow** to check immediately, with **force** for an unconditional rebuild.

The pipeline resolves a candidate once and shares that snapshot with native
**amd64 and arm64** runners. Both must pass:

- Exact installed versions, CLI help, and real terminal startup without credentials.
- Real SSH login, Herdr TUI attachment, foreground tab naming, and integrations.
- Disconnect/reconnect, restart persistence, and a stable SSH host identity.
- Upgrade of disposable volumes initialized by the previous passing image,
  preserving repositories and customized configuration. The first release has
  no previous image, so this gate starts with the second release.
- Source/privacy and reachable commit-identity checks. Optional extra private
  strings can be supplied through the `DEELER_PRIVATE_PATTERNS` repository secret,
  one literal per line; never commit those strings. The scanner is a guard in
  addition to the required human/agent review, not proof that arbitrary prose
  contains no identifying information.

Verified per-platform candidates are stored in GHCR under `candidate-*` tags.
They are not deployment releases. Promotion assembles those same digests into
`release-<UTC timestamp>-<run>-<attempt>`, records the multi-platform digest, moves
`previous` to the last passing digest, then updates `latest`. There is no rebuild
between verification and promotion. Keep using the digest for a fixed deployment.

Each successful workflow provides a **release-manifest** artifact and summary
with resolved versions, image digest, platforms tested, and canary status.
Manifests are retained for 90 days and also exist inside each image. Failed
updates maintain one `[deeler] Update verification failed` issue; the existing
`latest` stays in place when a verification gate fails. A later successful run
closes that issue. Registry/notification failures can still need operator action.

GitHub schedules are best-effort and may be delayed. GitHub can disable scheduled
workflows in inactive public repositories; keep the workflow enabled and check
its run history. Missing/expired baseline artifacts cause a fresh build rather
than skipping verification.

## Optional authenticated canaries

These are disabled until you set repository variable `DEELER_CANARY_AGENTS` to a
comma-separated selection such as `codex,claude`. Only selected agents run; a
missing credential for a selected agent fails promotion.

| Agent selection | Dedicated repository secret | Additional variable |
| --- | --- | --- |
| `codex` | `DEELER_CANARY_CODEX_KEY` | None |
| `claude` | `DEELER_CANARY_CLAUDE_KEY` | None |
| `gemini` | `DEELER_CANARY_GEMINI_KEY` | None |
| `opencode` | `DEELER_CANARY_OPENCODE_KEY` | `DEELER_CANARY_OPENCODE_MODEL`, an `openai/` model |
| `pi` | `DEELER_CANARY_PI_KEY` | `DEELER_CANARY_PI_MODEL`, an OpenAI model |
| `copilot` | `DEELER_CANARY_COPILOT_TOKEN` | None |

Use dedicated test credentials with provider-side spending limits. OpenCode/Pi
canary adapters currently use OpenAI API credentials. Copilot needs a dedicated
eligible token; the workflow's built-in `GITHUB_TOKEN` is not a Copilot credential.
These secrets are independent of the accounts you authenticate in production;
production session credentials are never copied into CI.

Each selected CLI receives one tiny no-tools prompt in an isolated disposable
container with a read-only root, resource limits, temporary home, and a two-minute
timeout. The expected response marker must appear and the command must succeed.
Containers are removed on success/failure/timeout. Raw responses and authentication
output are suppressed; credentials are passed at runtime, never into image builds.
These canaries check a basic authenticated request, not task quality or complete
native-conversation recovery. Set provider quotas before enabling them.

## Build locally

```sh
python3 scripts/resolve_versions.py
DEELER_IMAGE=deeler:local docker compose -f docker-compose.yaml -f docker-compose.build.yaml up -d --build
```

The image folder is `deeler/`. Local builds use its current snapshot. The
registry workflow supplies the resolved base digest and weekly refresh argument.
The Dockerfile performs time-bounded version checks for all CLIs. Tools are
updated through replacement images; startup does not self-update agent binaries.

## Deployment and rollback

The publishing workflow never connects to or restarts your running server.
Finish active work, back up both persistent volumes, then pull and recreate:

```sh
docker compose pull herdr
docker compose up -d herdr
```

Use the same Compose `-f` selection and project name throughout. To roll back,
set `DEELER_IMAGE` to the recorded previous digest (or the `previous` tag), then
pull and recreate. Restore matching volume backups if an agent changed its state
format; an image rollback cannot undo data migrations. Disconnecting a client
leaves agents running, while replacing the container ends its processes. Herdr
can resume supported conversations but cannot continue arbitrary shell commands.

Backups contain credentials and private code. `docker compose down` retains
volumes; `docker compose down -v` deletes them. Default Herdr keybindings remain
unchanged. Do not share a home volume between simultaneously running servers.

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
