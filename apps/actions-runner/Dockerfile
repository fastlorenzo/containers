# syntax=docker/dockerfile:1

ARG VERSION
FROM ghcr.io/actions/actions-runner:${VERSION}
ARG TARGETARCH

ENV HOMEBREW_NO_ANALYTICS=1 \
    HOMEBREW_NO_ENV_HINTS=1 \
    HOMEBREW_NO_INSTALL_CLEANUP=1

USER root

# build-essential/procps/file are Homebrew-on-Linux's documented requirements
# (https://docs.brew.sh/Homebrew-on-Linux#requirements). Bare gcc is not enough:
# `brew install homeport/tap/dyff` has no prebuilt bottle, so brew compiles it
# from source and aborts with "No developer tools installed" without make and
# the C headers. build-essential also pulls in libatomic1, which Node >= 24
# links against — without it `mise install` dies on `node -v`.
#
# Installed on every arch, not just amd64: an arm64 runner hits the same Node
# libatomic failure, and gating it made the image's contents arch-dependent for
# no benefit. Homebrew below stays amd64-only — it does not support ARM Linux.
RUN \
    apt-get -qq update \
    && \
    apt-get -qq install -y --no-install-recommends --no-install-suggests \
        build-essential \
        ca-certificates \
        file \
        jo \
        moreutils \
        postgresql-client \
        procps \
        python3 \
        wget \
        zstd \
    && \
    curl -fsSL "https://github.com/mikefarah/yq/releases/latest/download/yq_linux_${TARGETARCH}" -o /usr/local/bin/yq \
        && chmod +x /usr/local/bin/yq \
    && \
    install -d -m 755 /etc/apt/keyrings \
        && out=$(mktemp) && curl -fsSL -o "$out" https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        && cat "$out" | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
        && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
        && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
        && apt-get update \
        && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

USER runner

# rustup with no toolchain: each job installs whatever its rust-toolchain.toml
# pins (`rustup show active-toolchain || rustup toolchain install`), so the
# image never carries a toolchain that goes stale. Version pinned, binary
# checked against the .sha256 published next to it.
# renovate: datasource=github-tags depName=rust-lang/rustup
ARG RUSTUP_VERSION=1.29.1
ENV PATH="/home/runner/.cargo/bin:${PATH}"

# One RUN for rustup and Homebrew: hadolint fails on DL3059 (consecutive RUNs).
RUN \
    case "${TARGETARCH}" in \
        'amd64') triple=x86_64-unknown-linux-gnu ;; \
        'arm64') triple=aarch64-unknown-linux-gnu ;; \
    esac \
    && url="https://static.rust-lang.org/rustup/archive/${RUSTUP_VERSION}/${triple}/rustup-init" \
    && tmp=$(mktemp -d) \
    && curl -fsSL -o "${tmp}/rustup-init" "${url}" \
    && echo "$(curl -fsSL "${url}.sha256" | cut -d' ' -f1)  ${tmp}/rustup-init" | sha256sum -c - \
    && chmod +x "${tmp}/rustup-init" \
    && "${tmp}/rustup-init" -y --no-modify-path --default-toolchain none --profile minimal \
    && rm -rf "${tmp}" \
    && \
    case "${TARGETARCH}" in \
        'amd64') /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)" ;; \
    esac
