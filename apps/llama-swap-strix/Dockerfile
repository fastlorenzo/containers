# syntax=docker/dockerfile:1
#
# llama-swap with a custom llama.cpp build for Strix Halo (gfx1151) — see README.md.
#
# LLAMA_REPO/LLAMA_REF select what gets compiled: upstream at a bNNNNN tag, or a
# fork at a pinned commit. Everything else — flags, graft, layout — is identical
# either way, which is what keeps an A/B down to one variable.
#
# The build stages are a deliberate COPY of ggml-org/llama.cpp's own
# .devops/vulkan.Dockerfile (same ubuntu base, same package list, same cmake
# flags) with one addition: everything in patches/ is applied to the checked out
# release tag first. Matching upstream's flags matters more than tidying them —
# GGML_BACKEND_DL + GGML_CPU_ALL_VARIANTS decide which artifacts land in /app,
# and a mismatch would leave a half-swapped set of shared objects behind.
#
# The final stage grafts the result onto the llama-swap image that ai-box
# already runs, replacing only llama-server and the ggml backends. llama-swap
# itself, the entrypoint, the runtime libraries and every path stay as they
# were, so an A/B against BASE_IMAGE measures the patches and nothing else.
#
# NOTE the Vulkan flash-attention code being patched lives in
# libggml-vulkan.so, NOT in the llama-server binary. Copying only the binary
# would produce an image that benchmarks exactly like stock.

ARG UBUNTU_VERSION=26.04
ARG NODE_VERSION=24
ARG VERSION
ARG BASE_IMAGE
ARG LLAMA_REPO=https://github.com/ggml-org/llama.cpp.git
# Tag (bNNNNN) or full 40-char commit SHA. A SHA is mandatory for anything that
# is not an immutable upstream tag: a moving branch silently invalidates every
# benchmark taken against it.
ARG LLAMA_REF

# ── Web UI ────────────────────────────────────────────────────────────
# llama-server embeds tools/ui/dist at compile time and that directory is a
# build artifact, not tracked in git — so it has to be built here, exactly as
# upstream's Dockerfile does, or the server ends up without its UI.

FROM docker.io/node:${NODE_VERSION} AS web

ARG VERSION
ARG LLAMA_REPO
ARG LLAMA_REF

WORKDIR /src
RUN git init -q . \
    && git remote add origin "${LLAMA_REPO}" \
    && git fetch --depth 1 -q origin "${LLAMA_REF}" \
    && git checkout -q FETCH_HEAD \
    && git log -1 --format='%H %cI %s' | tee /llama-source.txt

WORKDIR /src/tools/ui
RUN npm ci && LLAMA_BUILD_NUMBER="${VERSION#b}" npm run build

# ── Build ─────────────────────────────────────────────────────────────

FROM docker.io/ubuntu:${UBUNTU_VERSION} AS build

ARG VERSION

RUN apt-get update && apt-get install -y --no-install-recommends \
        git build-essential cmake wget xz-utils \
        libssl-dev curl ca-certificates \
        libxcb-xinput0 libxcb-xinerama0 libxcb-cursor-dev \
        libvulkan-dev glslc spirv-headers \
    && rm -rf /var/lib/apt/lists/*

ARG LLAMA_REPO
ARG LLAMA_REF

WORKDIR /src
RUN git init -q . \
    && git remote add origin "${LLAMA_REPO}" \
    && git fetch --depth 1 -q origin "${LLAMA_REF}" \
    && git checkout -q FETCH_HEAD \
    && git log -1 --format='%H %cI %s' | tee /llama-source.txt

# Out-of-tree patches, if any. --verbose so the build log records which hunks
# moved: these apply against a moving base, so offsets are expected and fine. A
# real conflict fails the build here rather than quietly shipping an unpatched
# image that benchmarks as a null result.
#
# An EMPTY patches/ is a legitimate state — building a fork needs no patches —
# so the loop tolerates no matches, but only that. Anything that is present and
# does not apply still fails the build.
COPY patches/ /patches/
RUN set -eux; \
    for p in /patches/*.patch; do \
        [ -e "$p" ] || continue; \
        echo "=== applying $(basename "$p")"; \
        git apply --verbose "$p"; \
    done; \
    git diff --stat > /patches-applied.txt; \
    cat /llama-source.txt >> /patches-applied.txt; \
    cat /patches-applied.txt

COPY --from=web /src/tools/ui/dist tools/ui/dist

RUN cmake -B build \
        -DGGML_NATIVE=OFF \
        -DGGML_VULKAN=ON \
        -DLLAMA_BUILD_TESTS=OFF \
        -DGGML_BACKEND_DL=ON \
        -DGGML_CPU_ALL_VARIANTS=ON \
    && cmake --build build --config Release -j"$(nproc)" \
    && mkdir -p /out/lib \
    && find build -name "*.so*" -exec cp -P {} /out/lib \; \
    && cp build/bin/llama-server /out/llama-server \
    && ls -la /out /out/lib

# ── Graft onto the llama-swap image ai-box runs ───────────────────────

FROM ${BASE_IMAGE}

USER root

# Fail loudly if the base ever stops using the /app layout the whole stack
# assumes — llama-swap's model map and ai-bench both exec /app/llama-server.
RUN test -f /app/llama-server && test -f /app/llama-swap \
    || (echo "base image is not the expected /app layout" >&2; exit 1)

COPY --from=build --chown=10001:10001 /out/lib/ /app/
COPY --from=build --chown=10001:10001 /out/llama-server /app/llama-server
COPY --from=build --chown=10001:10001 /patches-applied.txt /app/patches-applied.txt
COPY --from=build --chown=10001:10001 /llama-source.txt /app/llama-source.txt

USER 10001:10001
