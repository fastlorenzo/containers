FROM ghcr.io/onedr0p/alpine:rolling@sha256:01db2e6ff88bf0ce692fb6552ab68f4eb3f77d16ba5d3402e8a7de3f4f8873f1

ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG VERSION
ARG CHANNEL

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

#hadolint ignore=DL3018
RUN apk add --no-cache ca-certificates
#hadolint ignore=DL3059
RUN \
    case "${TARGETPLATFORM}" in \
        'linux/amd64') export ARCH='stash-linux' ;; \
        'linux/arm64') export ARCH='stash-linux-arm64v8' ;; \
    esac \
    && \
    curl -fsSL -o /app/stash \
        "https://github.com/stashapp/stash/releases/download/v${VERSION}/${ARCH}" \
    && chown -R root:root /app \
    && chmod -R 755 /app \
    && rm -rf /tmp/*

USER kah
COPY ./apps/stash/entrypoint.sh /entrypoint.sh
CMD ["/entrypoint.sh"]

LABEL org.opencontainers.image.source="https://github.com/stashapp/stash"
