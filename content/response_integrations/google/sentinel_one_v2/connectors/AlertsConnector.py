from __future__ import annotations
import datetime
import sys

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.base.connector import Connector
from TIPCommon.consts import DATETIME_FORMAT, TIMEOUT_THRESHOLD
from TIPCommon.data_models import BaseAlert
from TIPCommon.filters import pass_whitelist_filter
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.utils import is_empty_string_or_none, is_test_run
from EnvironmentCommon import GetEnvironmentCommonFactory as EnvCommon
from sentinel_one_v2.core.constants import (
    ALERTS_CONNECTOR_SCRIPT_NAME,
    DATE_TIME_FORMAT_UTC,
    MAX_ALERTS_TO_FETCH,
    SEVERITIES,
    SEVERITIES_FILTER_MAPPING,
    STATUS_FILTER_MAPPER,
    STORED_IDS_LIMIT,
)
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory, API_VERSION_2_1
from sentinel_one_v2.core.datamodelsV2 import Alert


class AlertsConnector(Connector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.case_name_template: str | None = None
        self.alert_name_template: str | None = None
        self.manager = None
        self.environment_common = None

    def validate_params(self) -> None:
        """Validate connector parameters."""
        self.params.max_alerts_to_fetch = self.param_validator.validate_positive(
            param_name="Max Alerts To Fetch",
            value=self.params.max_alerts_to_fetch,
        )
        if self.params.max_alerts_to_fetch > MAX_ALERTS_TO_FETCH:
            raise ValueError(
                f"'Max Alerts To Fetch' value cannot exceed {MAX_ALERTS_TO_FETCH}."
            )

        self.params.max_hours_backwards = self.param_validator.validate_positive(
            param_name="Max Hours Backwards",
            value=self.params.max_hours_backwards,
        )
        if not is_empty_string_or_none(self.params.lowest_severity_to_fetch):
            self.params.lowest_severity_to_fetch = self.param_validator.validate_ddl(
                param_name="Lowest Severity To Fetch",
                value=self.params.lowest_severity_to_fetch,
                ddl_values=SEVERITIES,
            )

    def get_severity_filter(self, lowest_severity: str | None) -> list[str]:
        """Determines the severity filter based on user input."""
        if lowest_severity:
            severity_filter = SEVERITIES_FILTER_MAPPING.get(lowest_severity.upper())
            if not severity_filter:
                raise ValueError(
                    "Invalid value for 'Lowest Severity To Fetch': "
                    f"'{lowest_severity}'. Allowed values are: "
                    f"{', '.join(SEVERITIES_FILTER_MAPPING.keys())}"
                )
            self.logger.info(f"Applying severity filter: {severity_filter.split(',')}")
            return severity_filter.split(",")

        self.logger.info(
            "No Lowest Severity provided. Ingesting alerts with all severities."
        )
        return SEVERITIES_FILTER_MAPPING.get("INFO").split(",")

    def get_status_filter(self, status_filter: str | None) -> list[str]:
        """Determines the status filter based on user input."""
        raw_statuses = [s.strip().lower() for s in status_filter.split(",")]
        invalid_statuses = [
            status for status in raw_statuses if status not in STATUS_FILTER_MAPPER
        ]
        if invalid_statuses:
            raise ValueError(
                f'Invalid value(s) for "Status Filter": {", ".join(invalid_statuses)}.'
                f' Allowed values are: {", ".join(STATUS_FILTER_MAPPER.keys())}'
            )
        statuses = [STATUS_FILTER_MAPPER[s] for s in raw_statuses]
        self.logger.info(f"Applying status filter: {statuses}")
        return statuses

    def init_managers(self) -> None:
        """Create manager instance objects"""
        self.manager = SentinelOneV2ManagerFactory(API_VERSION_2_1).get_manager(
            api_root=self.params.api_root,
            api_token=self.params.api_token,
            logger=self.logger,
            verify_ssl=self.params.verify_ssl,
        )
        self.environment_common = EnvCommon.create_environment_manager(
            siemplify=self.siemplify,
            environment_field_name=self.params.environment_field_name,
            environment_regex_pattern=self.params.environment_regex_pattern,
        )

    def get_last_success_time(self, *_) -> datetime.datetime:
        """Get last_success_time for connector from DB."""
        return super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards",
            metric="hours",
            time_format=DATETIME_FORMAT,
            date_time_format=DATE_TIME_FORMAT_UTC,
        )

    def read_context_data(self) -> None:
        """Read connector's context data from DB."""
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = read_ids(self.siemplify)

    def store_alert_in_cache(self, alert: Alert) -> None:
        """Store alert id in connector IDs cache
        Args:
            alert (Alert): Alert dataclass
        """
        self.context.existing_ids.append(alert.alert_id)

    def is_overflow_alert(self, alert_info: AlertInfo) -> bool:
        """Check if alert is overflowed
        Args:
            alert_info (AlertInfo): AlertInfo object
        Returns:
            True if alert is overflowed, False otherwise
        """
        return not self.params.disable_overflow and super().is_overflow_alert(
            alert_info
        )

    def set_last_success_time(self, all_alerts: list[Alert], *_) -> None:
        """Save last_success_time into DB
        Args:
            all_alerts ([Alert]): list of all fetched Alert dataclasses
        """
        if all_alerts:
            newest_alert_timestamp = max(
                alert.creation_time_unix_time for alert in all_alerts
            )
            self.siemplify.save_timestamp(
                new_timestamp=newest_alert_timestamp,
                datetime_format=DATE_TIME_FORMAT_UTC,
            )
        else:
            self.logger.info(
                "Last successful timestamp was not updated due to no new alerts "
                "being processed."
            )

    def write_context_data(self, all_alerts: list[Alert]) -> None:
        """Save connector context data into DB (or FileStorage)
        Args:
            all_alerts ([Alert]): list of all fetched Alert dataclasses
        """
        if all_alerts:
            self.logger.info("Saving existing ids.")
            write_ids(
                self.siemplify,
                self.context.existing_ids,
                stored_ids_limit=STORED_IDS_LIMIT,
            )

    def _drop_existing_alerts(self, alerts: list[Alert]) -> list[Alert]:
        """Dropping existing alerts that have already been processed. Only new alerts
        will be returned.

        Args:
            alerts (list[Alert]): A list of Alert dataclasses.

        Returns:
            list[Alert]: A list of alerts that are not in the existing IDs cache.
        """
        existing_ids = set(self.context.existing_ids)
        return [alert for alert in alerts if alert.alert_id not in existing_ids]

    def get_alerts(self) -> list[Alert]:
        """Fetch alerts
        Returns:
            list[Alert]: List of alerts
        """
        all_fetched_alerts = []
        current_start_time = self.context.last_success_timestamp
        severities = self.get_severity_filter(self.params.lowest_severity_to_fetch)
        statuses = self.get_status_filter(self.params.status_filter)
        fetch_limit = max(MAX_ALERTS_TO_FETCH, self.params.max_alerts_to_fetch)
        next_cursor = None
        page_count = 0

        self.logger.info(
            f"Fetching alerts from start time: {current_start_time} "
            f"with limit: {fetch_limit}"
        )
        while len(all_fetched_alerts) < fetch_limit:
            page_count += 1
            fetched_alerts, next_cursor = self.manager.get_alerts(
                start_time=current_start_time,
                severities=severities,
                statuses=statuses,
                limit=fetch_limit,
                cursor=next_cursor,
            )
            self.logger.info(
                f"Page {page_count}: Received {len(fetched_alerts)} alerts."
            )
            if not fetched_alerts:
                self.logger.info(
                    f"Page {page_count}: No new alerts found, stopping fetch."
                )
                break

            new_alerts = self._drop_existing_alerts(fetched_alerts)
            if new_alerts:
                all_fetched_alerts.extend(new_alerts)
                self.logger.info(
                    f"Page {page_count}: Found {len(new_alerts)} new alerts."
                )
            else:
                self.logger.info(f"Page {page_count}: All alerts were duplicates.")

            if not next_cursor:
                self.logger.info(
                    f"Page {page_count}: No next page/cursor; stopping fetch."
                )
                break

        return sorted(
            all_fetched_alerts[:fetch_limit],
            key=lambda _alert: _alert.creation_time_unix_time,
        )

    def pass_filters(self, alert: Alert) -> bool:
        """Check if alert passes dynamic list filter
        Args:
            alert (Alert): Alert dataclass
        Returns:
            bool: True if passes filter, False otherwise
        """
        if self.siemplify.whitelist and not pass_whitelist_filter(
            self.siemplify,
            self.params.use_dynamic_list_as_a_blocklist,
            model=alert,
            model_key="rule_name",
        ):
            return False
        return True

    def create_alert_info(self, alert: Alert) -> AlertInfo:
        """Create AlertInfo object out of and alert
        Args:
            alert (Alert): Alert dataclass
        Returns:
            AlertInfo: AlertInfo object
        """
        return alert.get_alert_info(
            alert_name_template=self.params.alert_name_template,
            case_name_template=self.params.case_name_template,
            environment_common=self.environment_common,
        )

    def process_alerts(
        self,
        filtered_alerts: list[BaseAlert],
        timeout_threshold: float = TIMEOUT_THRESHOLD,
    ) -> tuple[list[AlertInfo], list[BaseAlert]]:
        """Main alert processing loop
        Args:
            filtered_alerts ([BaseAlert]): list of filtered BaseAlert objects
            timeout_threshold (float): timeout threshold for connector execution
        Returns:
            tuple containing list of AlertInfo objects, and list of BaseAlert objects
        """
        if len(filtered_alerts) > self.params.max_alerts_to_fetch:
            self.siemplify.LOGGER.info(
                f"Limiting processed alerts from {len(filtered_alerts)} "
                f"to {self.params.max_alerts_to_fetch} "
                "based on user parameter 'Max Alerts To Fetch'."
            )
            filtered_alerts = filtered_alerts[: self.params.max_alerts_to_fetch]
        return super().process_alerts(filtered_alerts, timeout_threshold)


def main() -> None:
    """main"""
    script_name = ALERTS_CONNECTOR_SCRIPT_NAME
    is_test = is_test_run(sys.argv)
    connector = AlertsConnector(script_name, is_test)
    connector.start()


if __name__ == "__main__":
    main()
