ARG VERSION=latest

FROM ghcr.io/openclaw/openclaw:${VERSION}

USER root

# System packages missing from the upstream image
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ca-certificates \
      unzip \
      jq \
      python3 \
      golang-go \
      openssh-client \
      vim \
    && rm -rf /var/lib/apt/lists/*

# qmd memory search sidecar for OpenClaw (https://docs.openclaw.ai/concepts/memory-qmd/)
# renovate: datasource=npm depName=@tobilu/qmd
ARG QMD_VERSION=2.5.3
RUN npm install -g @tobilu/qmd@${QMD_VERSION} && \
    npm cache clean --force

USER node
