from __future__ import annotations

import sys
from ..core.constants import (
    DEFAULT_DEVICE_PRODUCT,
    DEFAULT_DEVICE_VENDOR,
    SECURITY_EVENTS_CONNECTOR,
    DEFAULT_LIMIT_FOR_CONNECTOR,
    MAX_LIMIT_FOR_CONNECTOR,
    REPORT_FILE_NAME,
    STORED_IDS_LIMIT,
    MAX_EVENTS_LIMIT,
)
from ..core.ArcsightManager import ArcsightManager
from ..core.datamodels import Correlation
from ..core.exceptions import UnableToParseException
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon import (
    filter_old_alerts,
    read_ids,
    write_ids,
    is_test_run,
    pass_whitelist_filter,
    read_content,
    write_content,
    dict_to_flat,
)
from TIPCommon.base.connector import Connector


class SecurityEventsConnector(Connector):
    def __init__(self, *args, **kwargs):
        super(SecurityEventsConnector, self).__init__(*args, **kwargs)
        self.vars.all_issues = []
        self.vars.processed_issues = []

    def validate_params(self) -> None:
        if self.params.lowest_priority_to_fetch:
            self.params.lowest_severity = self.param_validator.validate_range(
                param_name="Lowest Priority To Fetch",
                value=self.params.lowest_priority_to_fetch,
                min_limit=1,
                max_limit=10,
            )
        else:
            self.params.lowest_severity = ""

        self.params.fetch_limit = self.param_validator.validate_range(
            param_name="Max Events To Fetch",
            value=self.params.max_events_to_fetch,
            min_limit=1,
            max_limit=MAX_LIMIT_FOR_CONNECTOR,
            default_value=DEFAULT_LIMIT_FOR_CONNECTOR,
        )

    def init_managers(self) -> None:
        self.manager = ArcsightManager(
            server_ip=self.params.api_root,
            username=self.params.username,
            password=self.params.password,
            verify_ssl=self.params.verify_ssl,
            logger=self.logger,
        )
        self.manager.login()

    def read_context_data(self) -> None:
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = read_ids(self.siemplify)
        self.context.report_id = read_content(
            self.siemplify, REPORT_FILE_NAME, self.params.report_name
        )

    def store_alert_in_cache(self, alert: Correlation):
        self.context.existing_ids.append(alert.event_id)

    def write_context_data(self, processed_alerts) -> None:
        self.logger.info("Saving existing ids.")
        write_ids(
            self.siemplify, self.context.existing_ids, stored_ids_limit=STORED_IDS_LIMIT
        )
        write_content(
            self.siemplify,
            self.context.report_id,
            REPORT_FILE_NAME,
            self.params.report_name,
        )

    def get_alerts(self) -> list[Correlation]:
        if not self.context.report_id:
            report_data = self.manager.get_reports_info_by_name(self.params.report_name)
            self.context.report_id = report_data[0].get("reference", {}).get("id")

        download_token = self.manager.get_report_download_token(
            report_id=self.context.report_id
        )

        return self.manager.get_correlations_from_report(download_token=download_token)

    def filter_alerts(self, alerts: list[Correlation]) -> list[Correlation]:
        return filter_old_alerts(
            self.siemplify, alerts, self.context.existing_ids, "event_id"
        )

    def pass_filters(self, alert: Correlation) -> bool:
        if not pass_whitelist_filter(
            self.siemplify, self.params.use_dynamic_list_as_a_blocklist, alert, "name"
        ):
            return False

        if not self.pass_severity_filter(alert):
            return False

        return True

    def max_alerts_processed(self, processed_alerts) -> bool:
        if len(processed_alerts) >= self.params.fetch_limit:
            return True

    def create_alert_info(self, alert: Correlation) -> AlertInfo:
        self.logger.info(f"Creating alert info for alert {alert.event_id}")
        alert_info = AlertInfo()
        alert_info.ticket_id = alert.event_id
        alert_info.display_id = f"ArcSight_{alert.event_id}"
        alert_info.name = alert.name
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = (
            alert.flat_raw_data.get(self.params.device_product_field)
            or DEFAULT_DEVICE_PRODUCT
        )
        alert_info.priority = alert.get_siemplify_priority()
        alert_info.rule_generator = alert.name
        alert_info.source_grouping_identifier = alert.name
        alert_info.start_time = alert.start_time_ms
        alert_info.end_time = alert.end_time_ms

        if self.params.fetch_base_events:
            events, error_message = self.manager.get_security_events(
                [alert.event_id], MAX_EVENTS_LIMIT
            )
            flat_events = [dict_to_flat(event) for event in events]
        else:
            flat_events = [
                dict_to_flat(event)
                for event in self.manager._get_security_events_single_level(
                    [alert.event_id]
                )
            ]

        first_correlation = next(
            (
                ev
                for ev in flat_events
                if ev.get("eventAnnotation_eventId") == alert.event_id
            ),
            None,
        )
        alert_info.environment = self.env_common.get_environment(first_correlation)

        try:
            flat_events = self.manager.completely_remove_invalid_values(flat_events)
        except Exception as e:
            self.logger.error("Unable to remove invalid values from events")
            self.logger.exception(e)

        try:
            self.manager.parse_ip_addresses(flat_events)
        except UnableToParseException as e:
            key = str(e.key)
            value = str(e.value)
            self.logger.info(
                f"Value - '{value}' in key '{key}' wasn't converted to the IP address"
            )

        alert_info.events = flat_events

        return alert_info

    def pass_severity_filter(self, alert):
        # severity filter
        if self.params.lowest_severity and alert.priority < self.params.lowest_severity:
            self.logger.info(
                "Alert with priority: {} did not pass filter. Lowest risk score to fetch is "
                "{}.".format(alert.priority, self.params.lowest_severity)
            )
            return False
        return True

    def finalize(self) -> None:
        self.manager.logout()


def main() -> None:
    """main"""
    script_name = SECURITY_EVENTS_CONNECTOR
    is_test = is_test_run(sys.argv)
    connector = SecurityEventsConnector(script_name, is_test)
    connector.start()


if __name__ == "__main__":
    main()
