FROM ghcr.io/fastlorenzo/alpine:rolling@sha256:2472a2b578478cb15c16af9d91095ad36187ecba7d944c806b74e69df5813b10

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
ENTRYPOINT ["/app/mktxp"]
CMD ["export"]

LABEL org.opencontainers.image.source="https://github.com/akpw/mktxp"
