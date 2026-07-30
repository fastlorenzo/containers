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

USER node
