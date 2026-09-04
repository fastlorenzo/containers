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

# qmd removed 2026-07-26. It only supports local GGUF inference (tobi/qmd#229,
# #521, #620), so it ran a second embedding stack — embeddinggemma-300M, a
# reranker and a 1.7B query-expansion model, 2.2G of weights on the PVC —
# on CPU in a pod with no GPU. Recall now goes through the ai-box gateway's
# Qwen3-Embedding-4B via the obsidian-bridge MCP server, so there is one
# embedding model and one place to tune retrieval.

# Obsidian Headless (ob) CLI for headless vault sync (https://obsidian.md/help/sync/headless)
# renovate: datasource=npm depName=obsidian-headless
ARG OBSIDIAN_HEADLESS_VERSION=0.0.14
RUN npm install -g obsidian-headless@${OBSIDIAN_HEADLESS_VERSION} && \
    npm cache clean --force

# Since the 2026.8.x upstream base (Node 24 / npm 12) the global install no
# longer runs better-sqlite3's install script, so obsidian-headless shipped
# without its native binding and `ob sync` died with "Could not locate the
# bindings file" (2026-09-04). Fetch the prebuilt binary explicitly (fall back
# to a source build) and fail the image build if the module cannot load.
WORKDIR /usr/local/lib/node_modules/obsidian-headless/node_modules/better-sqlite3
RUN (npx --no-install prebuild-install || npm run build-release) && \
    node -e "new (require('/usr/local/lib/node_modules/obsidian-headless/node_modules/better-sqlite3'))(':memory:').close()" && \
    rm -rf /root/.npm /tmp/*
WORKDIR /app

USER node
