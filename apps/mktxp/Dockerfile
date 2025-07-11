# syntax=docker/dockerfile:1

FROM docker.io/library/alpine:3.22
ARG VERSION
USER root

RUN \
    apk add --no-cache \
        bash \
        ca-certificates \
        catatonit \
        py3-pip \
    && pip install mktxp=="${VERSION}" --break-system-packages \
    && chown -R root:root /usr/bin/mktxp \
    && chmod -R 755 /usr/bin/mktxp \
    && rm -rf /tmp/*

EXPOSE 49090
COPY ./entrypoint.sh /entrypoint.sh
USER nobody:nogroup

ENTRYPOINT ["/usr/bin/catatonit", "--", "/entrypoint.sh"]
