# syntax=docker/dockerfile:1
#
# llama-swap with a patched llama.cpp for Strix Halo (gfx1151) — see README.md.
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

# ── Web UI ────────────────────────────────────────────────────────────
# llama-server embeds tools/ui/dist at compile time and that directory is a
# build artifact, not tracked in git — so it has to be built here, exactly as
# upstream's Dockerfile does, or the server ends up without its UI.

FROM docker.io/node:${NODE_VERSION} AS web

ARG VERSION

WORKDIR /src
RUN git clone --depth 1 --branch "${VERSION}" \
    https://github.com/ggml-org/llama.cpp.git .

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

WORKDIR /src
RUN git clone --depth 1 --branch "${VERSION}" \
    https://github.com/ggml-org/llama.cpp.git .

# --verbose so the build log records which hunks moved: these are out-of-tree
# patches against a moving base, so applying with offsets is expected and fine.
# A real conflict fails the build here rather than quietly shipping an
# unpatched image that benchmarks as a null result.
COPY patches/ /patches/
RUN set -eux; \
    for p in /patches/*.patch; do \
        echo "=== applying $(basename "$p")"; \
        git apply --verbose "$p"; \
    done; \
    git diff --stat | tee /patches-applied.txt

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

USER 10001:10001
