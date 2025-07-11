# syntax=docker/dockerfile:1

FROM docker.io/library/alpine:3.22
ARG TARGETARCH
ARG VERSION

ENV KOPIA_CONFIG_PATH="/config/repository.config" \
    KOPIA_LOG_DIR="/config/logs" \
    KOPIA_CACHE_DIRECTORY="/config/cache" \
    KOPIA_PERSIST_CREDENTIALS_ON_CONNECT="false" \
    KOPIA_CHECK_FOR_UPDATES="false" \
    RCLONE_CONFIG="/config/rclone/rclone.conf"

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
        wget https://github.com/kopia/kopia/releases/download/v${VERSION}/kopia-${VERSION}-linux-${TARGETARCH}.tar.gz \
        -O /tmp/kopia.tar.gz \
    && tar -xzf /tmp/kopia.tar.gz -C /bin kopia \
    && chmod +x /bin/kopia \
    && rm -rf /tmp/*

CMD ["kopia"]
