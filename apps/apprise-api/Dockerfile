FROM ghcr.io/onedr0p/alpine:rolling@sha256:da2846e0398d55a5178448f7cb9ee1eeeeee13830fba40289152798595f78c8a

ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG VERSION
ARG CHANNEL

ENV \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CRYPTOGRAPHY_DONT_BUILD_RUST=1

ENV APPRISE_CONFIG_DIR=/config

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN \
    curl -fsSL "https://github.com/caronc/apprise-api/archive/refs/tags/v${VERSION}.tar.gz" \
        | tar xzf - -C /app --strip-components=1 \
    && chown -R root:root /app \
    && chmod -R 755 /app \
    && rm -rf /tmp/*

#hadolint ignore=DL3018,DL3013
RUN apk add --no-cache \
        ca-certificates \
        py3-pip \
        python3 \
        uwsgi \
        uwsgi-python \
    && \
    apk add --no-cache --virtual=.build-deps \
        cargo \
        g++ \
        gcc \
        libffi-dev \
        openssl-dev \
        python3-dev \
    && \
    pip install --upgrade pip wheel \
    && \
    pip install --requirement /app/requirements.txt \
    && apk del --purge .build-deps \
    && rm -rf \
        /root/.cache \
        /root/.cargo \
        /tmp/*

USER kah
COPY ./apps/apprise-api/entrypoint.sh /entrypoint.sh
CMD ["/entrypoint.sh"]

LABEL org.opencontainers.image.source="https://github.com/caronc/apprise-api"
