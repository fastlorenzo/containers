from setuptools import setup


setup(
    name="alerta-prometheus-cluster-webhook",
    version="0.2.0",
    description=(
        "Map Prometheus cluster labels to Alerta environments and "
        "normalize Prometheus severities to Alerta's alarm model"
    ),
    py_modules=["alerta_prometheus_cluster"],
    install_requires=[],
    entry_points={
        "alerta.webhooks": [
            (
                "prometheus-cluster = "
                "alerta_prometheus_cluster:PrometheusClusterWebhook"
            ),
        ],
    },
)
