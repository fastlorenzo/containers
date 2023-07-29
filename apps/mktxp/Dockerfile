FROM ghcr.io/fastlorenzo/alpine:rolling@sha256:1c325150682b776ee1493be67d591e8c6d3a317bab79db111d1ce9ccb48867d7

ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG VERSION
ARG CHANNEL

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

#hadolint ignore=DL3018
RUN apk add --no-cache ca-certificates py3-pip

RUN pip install mktxp=="${VERSION}"
#hadolint ignore=DL3059
RUN chown -R root:root /usr/bin/mktxp \
    && chmod -R 755 /usr/bin/mktxp \
    && ln -s /usr/bin/mktxp /app/mktxp \
    && rm -rf /tmp/*

USER kah

EXPOSE 49090
COPY ./apps/mktxp/entrypoint.sh /entrypoint.sh
CMD ["/entrypoint.sh"]

LABEL org.opencontainers.image.source="https://github.com/akpw/mktxp"
