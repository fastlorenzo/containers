ARG VERSION=latest

FROM docker.io/alerta/alerta-web:${VERSION}

USER root

# Copy our custom Prometheus Cluster Webhook plugin into the image
COPY ./webhook /tmp/alerta-prometheus-cluster-webhook

# Install our custom Prometheus Cluster Webhook plugin into the image
RUN /venv/bin/pip install \
      --no-cache-dir \
      /tmp/alerta-prometheus-cluster-webhook \
    && rm -rf /tmp/alerta-prometheus-cluster-webhook


USER 1001
