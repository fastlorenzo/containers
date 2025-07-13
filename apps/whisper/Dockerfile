# syntax=docker/dockerfile:1

FROM docker.io/library/python:3.10-slim
ARG VERSION
USER root

RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        catatonit \
    && pip install openai-whisper=="${VERSION}" --break-system-packages \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/*

# EXPOSE 49090
COPY ./entrypoint.sh /entrypoint.sh
USER nobody:nogroup

ENTRYPOINT ["/usr/bin/catatonit", "--", "/entrypoint.sh"]
