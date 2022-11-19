FROM alpine:3.16.3@sha256:b95359c2505145f16c6aa384f9cc74eeff78eb36d308ca4fd902eeeb0a0b161b
LABEL MAINTAINER "Lorenzo Bernardi <docker@bernardi.be>"

SHELL ["/bin/sh", "-xo", "pipefail", "-c"]

ENV LANG C.UTF-8 \
    PGID=1000 \
    PUID=911 \
    NC_USER=username \
    NC_PASS=password \
    NC_INTERVAL=500 \
    NC_URL="" \
    NC_TRUST_CERT=false \
    NC_SOURCE_DIR="/media/nextcloud/" \
    NC_SILENT=false \
    NC_EXIT=false   \
    NC_HIDDEN=false

# update repositories and install nextcloud-client
RUN apk update && \
    apk add --no-cache nextcloud-client su-exec shadow && \
    rm -rf /etc/apk/cache

# Create ncsync user and group (from linuxserver.io setup)
RUN addgroup -g 911 ncsync && \
    adduser -G ncsync -D -u 911 ncsync

# add run script
COPY ./apps/nextcloud-client/entrypoint.sh /entrypoint.sh
# COPY ./entrypoint.sh /entrypoint.sh

VOLUME ["/media/nextcloud"]

ENTRYPOINT ["/entrypoint.sh"]

# LABEL org.opencontainers.image.source="https://github.com/nextcloud/docker"
