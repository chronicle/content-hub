from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.base.connector import Connector
from TIPCommon.filters import filter_old_alerts
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.utils import is_overflowed, is_test_run

from ..core import constants
from ..core.api.api_client import ApiParameters, SampleApiClient
from ..core.auth import AuthenticatedSession, SessionAuthenticationParameters, build_auth_params

if TYPE_CHECKING:
    import requests


class SimpleConnector(Connector):
    def __init__(self, is_test_connector_run: bool) -> None:
        super().__init__(constants.CONNECTOR_SCRIPT_NAME, is_test_connector_run)
        self.manager: SampleApiClient | None = None

    def validate_params(self) -> None:
        """Validate connector params with param_validator."""
        self.params.max_days_backwards = self.param_validator.validate_range(
            param_name="Max Days Backwards",
            value=self.params.max_days_backwards,
            min_limit=constants.MIN_DAYS_BACKWARDS,
            max_limit=constants.MAX_DAYS_BACKWARDS,
            print_value=True,
        )

        self.params.max_alerts_to_fetch = self.param_validator.validate_positive(
            param_name="Max Alerts To Fetch",
            value=self.params.max_alerts_to_fetch,
            print_value=True,
        )

    def init_managers(self) -> SampleApiClient:
        """Initialize API manager with authentication."""
        auth_params = build_auth_params(self.siemplify)
        authenticator: AuthenticatedSession = AuthenticatedSession()
        auth_params_for_session = SessionAuthenticationParameters(
            api_root=auth_params.api_root,
            password=auth_params.password,
            verify_ssl=auth_params.verify_ssl,
        )
        authenticator.authenticate_session(auth_params_for_session)
        authenticated_session: requests.Session = authenticator.session

        api_params: ApiParameters = ApiParameters(
            api_root=auth_params.api_root,
        )

        self.manager = SampleApiClient(
            authenticated_session=authenticated_session,
            configuration=api_params,
            logger=self.logger,
        )

    def read_context_data(self) -> None:
        """Read context data from the SOAR platform."""
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = read_ids(self.siemplify)

    def get_last_success_time(self) -> int:
        return super().get_last_success_time(
            max_backwards_param_name="max_days_backwards",
            metric="days",
        )

    def get_alerts(self) -> list[AlertInfo]:
        """Fetch alerts from the API."""
        alerts: list[AlertInfo] = []
        rate = self.manager.get_connector_rates(
            currencies=string_to_multi_value(
                string_value=self.params.currencies_to_fetch,
                only_unique=True,
            ),
            start_date=self.context.last_success_timestamp.date(),
        )
        for base_rate in rate.exchange_rates:
            alerts.extend(
                base_rate.to_alerts(
                    create_per_rate=self.params.create_alert_per_exchange_rate,
                    severity=self.params.alert_severity,
                    env_common=self.env_common,
                    attachment=self.params.add_attachment,
                )
            )

        return alerts

    def filter_alerts(self, fetched_alerts: list[AlertInfo]) -> list[AlertInfo]:
        """Filter out alerts that are already processed or overflowed."""
        return filter_old_alerts(
            self.siemplify,
            fetched_alerts,
            self.context.existing_ids,
            "alert_id",
        )

    def max_alerts_processed(self, processed_alerts: list[AlertInfo]) -> bool:
        """Check if the maximum number of alerts to process has been reached."""
        if len(processed_alerts) >= self.params.max_alerts_to_fetch:
            return True

        return False

    def pass_filters(self, alert: AlertInfo) -> bool:
        """Check if the alert passes the whitelist filter."""
        return alert.pass_filter(
            soar_connector=self.siemplify,
            create_per_rate=self.params.create_alert_per_exchange_rate,
            use_dynamic_list_as_blocklist=self.params.use_dynamic_list_as_blocklist,
        )

    def is_overflow_alert(self, alert_info: AlertInfo) -> bool:
        """Check if the alert is an overflow alert."""
        return not self.params.disable_overflow and is_overflowed(
            self.siemplify, alert_info, self.is_test_run
        )

    def store_alert_in_cache(self, processed_alert: AlertInfo) -> None:
        """Store the processed alert in the context."""
        self.context.existing_ids.append(processed_alert.alert_id)

    def create_alert_info(self, processed_alert: AlertInfo) -> AlertInfo:
        """Create an AlertInfo object from the processed alert."""
        return processed_alert

    def set_last_success_time(self, alerts: list[AlertInfo]) -> None:
        """Set connector's last success time."""
        super().set_last_success_time(alerts=alerts, timestamp_key="start_time")

    def write_context_data(self, alerts: list[AlertInfo]) -> None:
        """Write connector's context data."""
        if not alerts:
            return

        self.logger.info("Saving existing ids.")
        write_ids(self.siemplify, self.context.existing_ids)


if __name__ == "__main__":
    is_test = is_test_run(sys.argv)
    connector = SimpleConnector(is_test)
    connector.start()
