FROM docker.io/library/alpine:3.19

ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG VERSION
ARG CHANNEL

SHELL ["/bin/sh", "-o", "pipefail", "-c"]

USER root
WORKDIR /app

#hadolint ignore=DL3018 ignore=DL3059
RUN apk add --no-cache \
    ca-certificates \
    py3-pip \
    && pip install mktxp=="${VERSION}" --break-system-packages \
    && chown -R root:root /usr/bin/mktxp \
    && chmod -R 755 /usr/bin/mktxp \
    && ln -s /usr/bin/mktxp /app/mktxp \
    && rm -rf /tmp/*

EXPOSE 49090
COPY ./apps/mktxp/entrypoint.sh /entrypoint.sh
CMD ["/entrypoint.sh"]

LABEL org.opencontainers.image.source="https://github.com/akpw/mktxp"
