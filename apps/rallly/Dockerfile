FROM --platform=linux/amd64 public.ecr.aws/docker/library/node:16-alpine as builder

WORKDIR /tmp/rallly
#hadolint ignore=DL3018
RUN apk add --no-cache git \
    && git clone --depth 1 https://github.com/lukevella/rallly . \
    && cp sample.env .env \
    && cp prisma/schema.prisma . \
    && yarn --frozen-lockfile \
    && yarn build


FROM ghcr.io/onedr0p/alpine:rolling@sha256:da2846e0398d55a5178448f7cb9ee1eeeeee13830fba40289152798595f78c8a
COPY --from=builder /tmp/rallly .
RUN apk add --no-cache yarn
USER kah
CMD sh -c "yarn start"
LABEL org.opencontainers.image.source="https://github.com/lukevella/rallly"
