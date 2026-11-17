# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim

ARG HERDR_VERSION=0.9.5
ARG CODEX_VERSION=0.169.0
ARG CLAUDE_VERSION=2.1.326
ARG GEMINI_VERSION=0.68.0
ARG OPENCODE_VERSION=2.3.0
ARG PI_VERSION=0.73.1
ARG COPILOT_VERSION=1.0.113
ARG RENAME_REF=a99754357fdea3119c430fd0cad822eef9047895
ARG TARGETARCH

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates curl git openssh-server supervisor gosu \
    jq ripgrep procps python3 python3-venv build-essential less libsecret-1-0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1001 --shell /bin/bash agent \
    && passwd -d agent \
    && rm -f /etc/ssh/ssh_host_* \
    && mkdir -p /run/sshd /var/lib/herdr-ssh /opt/herdr-defaults

# Release checksums from https://herdr.dev/latest.json, verified against GitHub.
RUN case "$TARGETARCH" in \
      amd64) herdr_arch=x86_64; herdr_sha=14d9e8bc8b4a9e0118d77c32266f76d461f09b40342eb23752960bd89f59929d ;; \
      arm64) herdr_arch=aarch64; herdr_sha=17d7536f2da50859523680ef279dffcac8e4a235f4e46fe8da6c2ec44141897c ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac \
    && test "$HERDR_VERSION" = 0.9.5 \
    && curl -fsSL --retry 3 "https://github.com/herdrdev/herdr/releases/download/v${HERDR_VERSION}/herdr-linux-${herdr_arch}" -o /usr/local/bin/herdr \
    && echo "$herdr_sha  /usr/local/bin/herdr" | sha256sum -c - \
    && chmod 755 /usr/local/bin/herdr \
    && herdr --version

# Binaries live outside the persistent home so image upgrades replace them.
ENV NPM_CONFIG_PREFIX=/opt/agent-tools HOME=/home/agent
RUN mkdir -p /opt/agent-tools && chown agent:agent /opt/agent-tools
USER agent
RUN npm install -g \
    "@openai/codex@${CODEX_VERSION}" \
    "@anthropic-ai/claude-code@${CLAUDE_VERSION}" \
    "@google/gemini-cli@${GEMINI_VERSION}" \
    "@opencode/cli@${OPENCODE_VERSION}" \
    "@mariozechner/pi-coding-agent@${PI_VERSION}" \
    "@github/copilot@${COPILOT_VERSION}"
USER root
ENV PATH="/opt/agent-tools/bin:${PATH}"
RUN chown -R root:root /opt/agent-tools \
    && for agent_cli in codex claude gemini opencode pi copilot; do \
         ln -s "/opt/agent-tools/bin/$agent_cli" "/usr/local/bin/$agent_cli"; \
       done \
    && git init /opt/herdr-automatic-rename \
    && git -C /opt/herdr-automatic-rename remote add origin https://github.com/qu8n/herdr-automatic-rename.git \
    && git -C /opt/herdr-automatic-rename fetch --depth=1 origin "$RENAME_REF" \
    && git -C /opt/herdr-automatic-rename checkout --detach FETCH_HEAD \
    && test "$(git -C /opt/herdr-automatic-rename rev-parse HEAD)" = "$RENAME_REF" \
    && gosu agent codex --version \
    && gosu agent claude --version \
    && gosu agent gemini --version \
    && gosu agent opencode --version \
    && gosu agent pi --version \
    && gosu agent copilot --version

ENV HOME=/home/agent SHELL=/bin/bash TERM=xterm-256color \
    HERDR_PROCESS_DETECTION=child-groups DISABLE_AUTOUPDATER=1
COPY config.toml bashrc /opt/herdr-defaults/
COPY sshd_config /etc/ssh/sshd_config
COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY entrypoint.sh /usr/local/bin/container-entrypoint
RUN chmod 755 /usr/local/bin/container-entrypoint
WORKDIR /home/agent/projects
EXPOSE 22
ENTRYPOINT ["/usr/local/bin/container-entrypoint"]
