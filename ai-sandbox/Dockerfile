ARG RUNTIME_IMAGE=node:24-bookworm-slim
FROM ${RUNTIME_IMAGE}

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates curl git jq make openssl procps sudo tini vim-tiny \
    && rm -rf /var/lib/apt/lists/* \
    && if getent passwd 1000 >/dev/null; then userdel "$(getent passwd 1000 | cut -d: -f1)"; fi \
    && if getent group 1000 >/dev/null; then groupdel "$(getent group 1000 | cut -d: -f1)"; fi \
    && groupadd --gid 1000 agent \
    && useradd --uid 1000 --gid agent --create-home --shell /bin/bash agent \
    && echo 'agent ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/agent \
    && chmod 0440 /etc/sudoers.d/agent \
    && mkdir -p /home/agent/workspace /home/agent/.local/bin \
    && chown -R agent:agent /home/agent \
    && touch /etc/sandbox-persistent.sh

COPY demo.bashrc /etc/demo.bashrc

ENV PATH="/home/agent/.local/bin:/home/agent/.speedscale:${PATH}" \
    BASH_ENV=/etc/sandbox-persistent.sh \
    SPEEDSCALE_APP_URL=dev.speedscale.com
LABEL com.docker.sandboxes="templates" com.docker.sandboxes.flavor="shell"
USER agent
WORKDIR /home/agent/workspace
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["bash"]
