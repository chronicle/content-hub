from __future__ import annotations

import datetime
import sys
from typing import Any

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import (
    convert_string_to_unix_time,
    dict_to_flat,
    output_handler,
)
from TIPCommon.types import SingleJson

from ..core.constants import SEVERITY_HIGH, SEVERITY_LOW
from ..core.PagerDutyManager import PagerDutyManager

CONNECTOR_NAME = "PagerDuty"
VENDOR = "PagerDuty"
PRODUCT = "PagerDuty"


@output_handler
def main(is_test_run: bool) -> None:
    processed_alerts: list[AlertInfo] = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******',
        )

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_key: str = siemplify.extract_connector_param(param_name="apiKey")
    acknowledge_enabled: str = siemplify.extract_connector_param(
        param_name="acknowledge"
    )
    max_hours_backwards: int = siemplify.extract_connector_param(
        param_name="Max Hours Backwards",
        input_type=int,
        default_value=24,
    )
    services: str = siemplify.extract_connector_param(param_name="Services")
    proxy_address: str = siemplify.extract_connector_param(
        param_name="Proxy Server Address"
    )
    proxy_username: str = siemplify.extract_connector_param(param_name="Proxy Username")
    proxy_password: str = siemplify.extract_connector_param(param_name="Proxy Password")

    siemplify.LOGGER.info("------------------- Main - Started -------------------")
    manager = PagerDutyManager(
        api_key=api_key,
    )

    if proxy_address:
        if "://" not in proxy_address:
            proxy_address = "http://" + proxy_address
        from urllib.parse import urlparse
        server_url = urlparse(proxy_address)
        scheme: str = server_url.scheme
        hostname: str | None = server_url.hostname
        port: int | None = server_url.port
        credentials: str = ""
        if proxy_username and proxy_password:
            credentials = f"{proxy_username}:{proxy_password}@"
        proxy_str: str = f"{scheme}://{credentials}{hostname}"
        if port:
            proxy_str += f":{port}"
        manager.requests_session.proxies = {"http": proxy_str, "https": proxy_str}

    try:
        time_diff: datetime.timedelta = datetime.timedelta(hours=max_hours_backwards)
        since: str = (
            datetime.datetime.now(datetime.timezone.utc) - time_diff
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        params: dict[str, Any] = {"since": since}
        if services:
            params["service_ids[]"] = [
                s.strip() for s in services.split(",") if s.strip()
            ]
        incidents_list: list[SingleJson] = manager.list_filtered_incidents(
            params=params
        )
        if incidents_list is None:
            siemplify.LOGGER.info(
                "No events were retrieved for the specified timeframe from PagerDuty",
            )
            return
        siemplify.LOGGER.info(f"Retrieved {len(incidents_list)} events from PagerDuty")
        for incident in incidents_list:
            alert_id: str = incident.get("incident_key", "")

            severity: str | None = get_siemplify_mapped_severity(
                incident.get("urgency", "low")
            )

            siemplify_alert: AlertInfo = build_alert_info(siemplify, incident, severity)

            if siemplify_alert:
                processed_alerts.append(siemplify_alert)
                siemplify.LOGGER.info(f"Added incident {alert_id} to package results")

                if acknowledge_enabled:
                    incident_got = manager.acknowledge_incident(incident["id"])
                    siemplify.LOGGER.info(
                        f"Incident {incident_got} acknowledged in PagerDuty",
                    )
    except Exception as e:
        siemplify.LOGGER.error(
            "There was an error fetching or acknowledging incidents in PagerDuty",
        )
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def get_siemplify_mapped_severity(severity: str) -> str | None:
    severity_map: dict[str, str] = {"high": SEVERITY_HIGH, "low": SEVERITY_LOW}
    return severity_map.get(severity.lower()) if severity else None


def build_alert_info(
    siemplify: SiemplifyConnectorExecution, incident: SingleJson, severity: str | None
) -> AlertInfo:
    """Returns an alert, which is an aggregation of basic events."""
    alert_info: AlertInfo = AlertInfo()
    alert_info.display_id = incident["id"]
    alert_info.ticket_id = incident["id"]
    alert_info.name = f"PagerDuty Incident: {incident['title']}"
    alert_info.rule_generator = (
        incident.get("first_trigger_log_entry", {}).get("summary", "No Summary")
    )
    alert_info.start_time = convert_string_to_unix_time(incident["created_at"])
    alert_info.end_time = alert_info.start_time
    alert_info.severity = severity
    alert_info.device_vendor = VENDOR
    alert_info.device_product = PRODUCT
    alert_info.environment = siemplify.context.connector_info.environment
    alert_info.events.append(dict_to_flat(incident))

    return alert_info


if __name__ == "__main__":
    is_test_run = len(sys.argv) > 2 and sys.argv[1] == "True"
    main(is_test_run)
