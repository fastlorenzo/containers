FROM ghcr.io/fastlorenzo/alpine:rolling@sha256:4502ff33fba31b46e9e067b5dc635a899b2f73b0f2290ee6f8104b6a5f2b2a73

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
