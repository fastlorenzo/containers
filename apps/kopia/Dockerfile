# syntax=docker/dockerfile:1

FROM docker.io/library/alpine:3.24
ARG TARGETARCH
ARG ARCH=${TARGETARCH/amd64/x64}
ARG VERSION

ENV KOPIA_CONFIG_PATH="/config/repository.config" \
    KOPIA_LOG_DIR="/config/logs" \
    KOPIA_CACHE_DIRECTORY="/config/cache" \
    KOPIA_PERSIST_CREDENTIALS_ON_CONNECT="false" \
    KOPIA_CHECK_FOR_UPDATES="false" \
    RCLONE_CONFIG="/config/rclone/rclone.conf"

# Kopia runs as root deliberately: it reads and restores files across arbitrary
# bind mounts and must preserve their ownership.
# hadolint ignore=DL3002
USER root
WORKDIR /app

RUN \
    apk add --no-cache \
    bash \
    ca-certificates \
    curl \
    jq \
    rclone \
    && \
    wget -q https://github.com/kopia/kopia/releases/download/v${VERSION}/kopia-${VERSION}-linux-${ARCH}.tar.gz \
    -O /tmp/kopia.tar.gz \
    && tar --strip-components=1 -xzf /tmp/kopia.tar.gz -C /bin kopia-${VERSION}-linux-${ARCH}/kopia \
    && chmod +x /bin/kopia \
    && rm -rf /tmp/*

COPY scripts/ /scripts/
RUN chmod +x /scripts/*.sh

CMD ["kopia"]
