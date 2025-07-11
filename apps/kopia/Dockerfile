# syntax=docker/dockerfile:1

FROM docker.io/library/alpine:3.22
ARG VERSION
USER root

ENV KOPIA_CONFIG_PATH="/config/repository.config" \
    KOPIA_LOG_DIR="/config/logs" \
    KOPIA_CACHE_DIRECTORY="/config/cache" \
    KOPIA_PERSIST_CREDENTIALS_ON_CONNECT="false" \
    KOPIA_CHECK_FOR_UPDATES="false" \
    RCLONE_CONFIG="/config/rclone/rclone.conf"

RUN \
    apk add --no-cache \
        bash \
        ca-certificates \
        curl \
        jq \
        kopia \
        rclone \
    && rm -rf /tmp/*

CMD ["kopia"]
