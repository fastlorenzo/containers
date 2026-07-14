from copy import deepcopy
from typing import Any, Dict, List

from alerta.exceptions import ApiError
from alerta.models.alert import Alert
from alerta.webhooks import WebhookBase
from alerta.webhooks.prometheus import parse_prometheus


class PrometheusClusterWebhook(WebhookBase):
    """
    Prometheus Alertmanager webhook that maps the Prometheus `cluster`
    label to the Alerta `environment` field.
    """

    def incoming(
        self,
        path: str,
        query_string: Any,
        payload: Any,
    ) -> List[Alert]:
        if not isinstance(payload, dict):
            raise ApiError("invalid Alertmanager webhook payload", 400)

        source_alerts = payload.get("alerts")

        if not isinstance(source_alerts, list) or not source_alerts:
            raise ApiError(
                "no alerts in Prometheus notification payload",
                400,
            )

        external_url = payload.get("externalURL")
        parsed_alerts: List[Alert] = []

        for source_alert in source_alerts:
            if not isinstance(source_alert, dict):
                raise ApiError("invalid alert in webhook payload", 400)

            # Do not mutate the original HTTP payload.
            transformed_alert: Dict[str, Any] = deepcopy(source_alert)

            labels = transformed_alert.get("labels")
            if not isinstance(labels, dict):
                raise ApiError(
                    'Prometheus alert is missing a valid "labels" object',
                    400,
                )

            # Alertmanager groups several alerts into one notification; a 400
            # here would reject the whole batch (and dead-man style alerts
            # built on absent()/vector(1) legitimately carry no cluster
            # label). When the label is missing, inject nothing and let
            # parse_prometheus fall back to DEFAULT_ENVIRONMENT.
            cluster = labels.get("cluster")
            if isinstance(cluster, str) and cluster.strip():
                # Let the standard Alerta Prometheus parser handle the rest.
                labels["environment"] = cluster.strip()

            parsed_alerts.append(
                parse_prometheus(transformed_alert, external_url)
            )

        return parsed_alerts
