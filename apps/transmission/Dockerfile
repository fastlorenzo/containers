FROM ghcr.io/onedr0p/alpine:rolling@sha256:da2846e0398d55a5178448f7cb9ee1eeeeee13830fba40289152798595f78c8a

ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG VERSION
ARG CHANNEL

ENV HOME=/config \
    XDG_CONFIG_HOME=/config \
    XDG_DATA_HOME=/config \
    TRANSMISSION__RPC_PORT=9091 \
    TRANSMISSION_WEB_HOME=/app/web

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

#hadolint ignore=DL3018
RUN apk add --no-cache ca-certificates geoip p7zip python3 transmission-cli~"${VERSION}" transmission-daemon~"${VERSION}"
#hadolint ignore=DL3059
RUN chown -R root:root /usr/bin/transmission* \
    && chmod -R 755 /usr/bin/transmission* \
    && ln -s /usr/bin/transmission-cli /app/transmission-cli \
    && ln -s /usr/bin/transmission-daemon /app/transmission-daemon \
    && ln -s /usr/share/transmission/web /app/web \
    && rm -rf /tmp/*

USER kah
COPY ./apps/transmission/settings.json.tmpl /app/settings.json.tmpl
COPY ./apps/transmission/entrypoint.sh /entrypoint.sh
CMD ["/entrypoint.sh"]

LABEL org.opencontainers.image.source="https://github.com/transmission/transmission"
