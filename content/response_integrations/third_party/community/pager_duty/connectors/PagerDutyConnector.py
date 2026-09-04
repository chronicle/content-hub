from __future__ import annotations

import sys
from typing import Any
from urllib.parse import urlparse

from SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.base.connector import Connector
from TIPCommon.consts import DATETIME_FORMAT
from TIPCommon.filters import filter_old_alerts
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.utils import is_test_run

from ..core.constants import INTEGRATION_NAME
from ..core.datamodels import PagerDutyIncident
from ..core.PagerDutyManager import PagerDutyManager


class PagerDutyConnector(Connector):
    def __init__(self, _is_test: bool) -> None:
        super().__init__(INTEGRATION_NAME, _is_test)
        self.manager: PagerDutyManager | None = None

    def validate_params(self) -> None:
        """Validate connector params."""
        self.params.max_hours_backwards = self.param_validator.validate_integer(
            param_name="Max Hours Backwards", value=self.params.max_hours_backwards
        )
        self.params.max_incidents_to_fetch = self.param_validator.validate_integer(
            param_name="Max Incidents To Fetch",
            value=self.params.max_incidents_to_fetch,
        )
        if self.params.acknowledge and not self.params.requester_email:
            raise ValueError("Requester Email is required when Acknowledge is enabled.")

    def read_context_data(self) -> None:
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = read_ids(self.siemplify)

    def init_managers(self) -> None:
        self.manager = PagerDutyManager(
            api_key=self.params.api_key,
            verify_ssl=self.params.verify_ssl,
            from_email=self.params.requester_email
        )
        
        if self.params.proxy_server_address:
            proxy_address = self.params.proxy_server_address
            if "://" not in proxy_address:
                proxy_address = "http://" + proxy_address
            server_url = urlparse(proxy_address)
            scheme: str = server_url.scheme
            hostname: str | None = server_url.hostname
            port: int | None = server_url.port
            credentials: str = ""
            if (
                self.params.proxy_username
                and self.params.proxy_password
                and str(self.params.proxy_username).lower() != "null"
                and str(self.params.proxy_password).lower() != "null"
            ):
                credentials = (
                    f"{self.params.proxy_username}:{self.params.proxy_password}@"
                )
            proxy_str: str = f"{scheme}://{credentials}{hostname}"
            if port:
                proxy_str += f":{port}"
            self.manager.requests_session.proxies = {
                "http": proxy_str,
                "https": proxy_str,
            }

    def get_last_success_time(self, **kwargs) -> str:
        return super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards",
            time_format=DATETIME_FORMAT,
            date_time_format="%Y-%m-%dT%H:%M:%SZ",
            **kwargs,
        )

    def get_alerts(self) -> list[PagerDutyIncident]:
        params: dict[str, Any] = {
            "since": self.context.last_success_timestamp,
            "limit": self.params.max_incidents_to_fetch
        }
        
        self.logger.info(f"PagerDuty get_alerts params: {params}")
        
        incidents_list: list[dict[str, Any]] = self.manager.list_filtered_incidents(
            params=params
        )
        
        if incidents_list is None:
            self.logger.info(
                "No events were retrieved for the specified timeframe from PagerDuty"
            )
            return []
            
        self.logger.info(f"Retrieved {len(incidents_list)} events from PagerDuty")
        
        alerts = []
        for incident in incidents_list:
            alert_id = incident["id"]
            alerts.append(PagerDutyIncident(incident, alert_id))
            
        return alerts

    def filter_alerts(
        self, fetched_alerts: list[PagerDutyIncident]
    ) -> list[PagerDutyIncident]:
        return filter_old_alerts(
            self.siemplify, fetched_alerts, self.context.existing_ids, "alert_id"
        )

    def max_alerts_processed(self, processed_alerts: list[AlertInfo]) -> bool:
        if len(processed_alerts) >= self.params.max_incidents_to_fetch:
            return True
        return False

    def store_alert_in_cache(self, processed_alert: PagerDutyIncident) -> None:
        self.context.existing_ids.append(processed_alert.alert_id)

    def create_alert_info(self, processed_alert: PagerDutyIncident) -> AlertInfo:
        return processed_alert.get_alert_info(self.env_common)

    def write_context_data(self, alerts: list[PagerDutyIncident]) -> None:
        if not alerts:
            return
        self.logger.info("Saving existing ids.")
        write_ids(self.siemplify, self.context.existing_ids)

    def set_last_success_time(self, alerts: list[PagerDutyIncident], **kwargs) -> None:
        """Set connector's last success time."""
        super().set_last_success_time(
            alerts=alerts,
            timestamp_key="created_at",
            convert_a_string_timestamp_to_unix=True,
            **kwargs
        )

    def process_alert(self, alert: PagerDutyIncident) -> PagerDutyIncident:
        if self.params.acknowledge:
            try:
                self.manager.acknowledge_incident(alert.raw_data["id"])
                self.logger.info(
                    f"Incident {alert.raw_data['id']} acknowledged in PagerDuty"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to acknowledge incident {alert.raw_data['id']} "
                    "in PagerDuty"
                )
                self.logger.exception(e)
        return alert


if __name__ == "__main__":
    is_test = is_test_run(sys.argv)
    connector = PagerDutyConnector(is_test)
    connector.start()
