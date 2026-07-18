# syntax=docker/dockerfile:1

FROM docker.io/library/python:3.13-alpine

RUN apk add --no-cache \
    ca-certificates \
    catatonit

COPY ./scripts/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --requirement /app/requirements.txt

COPY ./scripts/xigmanas_backup.py /app/xigmanas_backup.py

USER 65534:65534
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    HOME=/tmp

ENTRYPOINT ["/usr/bin/catatonit", "--"]
CMD ["python", "-u", "/app/xigmanas_backup.py"]
