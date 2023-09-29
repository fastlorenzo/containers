FROM ghcr.io/fastlorenzo/alpine:rolling@sha256:0fa6798f7f353916f4ce849b43d43b3f892010521350904305ac3adca6cbc46e

ARG TARGETPLATFORM
ARG VERSION
ARG CHANNEL

#hadolint ignore=DL3018
RUN apk add --no-cache ca-certificates
#hadolint ignore=DL3059
RUN \
    case "${TARGETPLATFORM}" in \
    'linux/amd64') export ARCH='amd64' ;; \
    'linux/arm64') export ARCH='arm64' ;; \
    esac \
    && \
    curl -fsSL "https://github.com/Unpackerr/unpackerr/releases/download/v${VERSION}/unpackerr.${ARCH}.linux.gz" \
    -o /tmp/unpackerr.gz \
    && gzip -dc < /tmp/unpackerr.gz > /app/unpackerr \
    && chown -R root:root /app \
    && chmod -R 755 /app \
    && rm -rf /tmp/*

USER kah
COPY ./apps/unpackerr/entrypoint.sh /entrypoint.sh
CMD ["/entrypoint.sh"]

LABEL org.opencontainers.image.source="https://github.com/Unpackerr/unpackerr"
