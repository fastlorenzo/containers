FROM ghcr.io/fastlorenzo/alpine:rolling@sha256:17bd4ab7ae494bd90d5f81bd6a50e25a4ebd904ed4118e57803c68fa930ccf93

ARG TARGETPLATFORM
ARG VERSION
ARG CHANNEL

ENV KOPIA_CONFIG_PATH="/config/repository.config" \
    KOPIA_LOG_DIR="/config/logs" \
    KOPIA_CACHE_DIRECTORY="/config/cache" \
    KOPIA_PERSIST_CREDENTIALS_ON_CONNECT="false" \
    KOPIA_CHECK_FOR_UPDATES="false" \
    RCLONE_CONFIG="/config/rclone/rclone.conf"

#hadolint ignore=DL3018
RUN apk add --no-cache ca-certificates rclone
#hadolint ignore=DL3059
RUN \
    case "${TARGETPLATFORM}" in \
    'linux/amd64') export ARCH='x64' ;; \
    'linux/arm64') export ARCH='arm64' ;; \
    esac \
    && \
    curl -fsSL "https://github.com/kopia/kopia/releases/download/v${VERSION}/kopia-${VERSION}-linux-${ARCH}.tar.gz" \
    | tar xzf - -C /usr/bin/ --strip-components=1 \
    && rm -rf /tmp/*

CMD ["kopia"]

LABEL org.opencontainers.image.source="https://github.com/kopia/kopia"
