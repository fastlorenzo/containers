FROM ghcr.io/onedr0p/alpine:rolling@sha256:dd504f02473c176a0e68e4550ccaf6f6c0f14e9f64c08a59877f9c6153bf48a9

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
