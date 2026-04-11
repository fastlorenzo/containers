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
    && rm -rf /var/lib/apt/lists/*

USER node
