# syntax=docker/dockerfile:1
ARG BASE_IMAGE=node:24-bookworm-slim
FROM ${BASE_IMAGE}

# Weekly cache invalidation refreshes Debian packages even without CLI releases.
ARG OS_REFRESH=local
RUN test -n "$OS_REFRESH" \
    && apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates curl git openssh-server supervisor gosu \
    jq ripgrep procps python3 python3-venv build-essential less libsecret-1-0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1001 --shell /bin/bash agent \
    && passwd -d agent \
    && rm -f /etc/ssh/ssh_host_* \
    && mkdir -p /run/sshd /var/lib/herdr-ssh /opt/herdr-defaults /opt/agent-tools /opt/deeler \
    && chown agent:agent /opt/agent-tools

ENV NPM_CONFIG_PREFIX=/opt/agent-tools HOME=/home/agent
COPY versions.json install_tools.py /opt/deeler/
RUN python3 /opt/deeler/install_tools.py

ENV PATH="/opt/agent-tools/bin:${PATH}" SHELL=/bin/bash TERM=xterm-256color \
    HERDR_PROCESS_DETECTION=child-groups DISABLE_AUTOUPDATER=1
COPY config.toml bashrc /opt/herdr-defaults/
COPY sshd_config /etc/ssh/sshd_config
COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY entrypoint.sh /usr/local/bin/container-entrypoint
RUN chmod 755 /usr/local/bin/container-entrypoint
WORKDIR /home/agent/projects
EXPOSE 22
ENTRYPOINT ["/usr/local/bin/container-entrypoint"]
