from __future__ import annotations

import json
import sys
from ..core.constants import (
    DEFAULT_DEVICE_PRODUCT,
    DEFAULT_DEVICE_VENDOR,
    ISSUES_CONNECTOR_NAME,
    POSSIBLE_SEVERITIES,
    SEVERITY_MAPPING,
    PRIORITY_MAPPING,
    TIMEOUT_THRESHOLD,
    DATETIME_FORMAT_FOR_CONNECTOR,
    DEFAULT_LIMIT_FOR_CONNECTOR,
    DEFAULT_HOURS_BACKWARDS,
)
from ..core.MandiantASMManager import MandiantASMManager
from ..core.datamodels import ConnectorIssue
from ..core.exceptions import InvalidParametersException
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon import (
    filter_old_alerts,
    read_ids,
    write_ids,
    is_test_run,
    pass_whitelist_filter,
)
from TIPCommon.base.connector import Connector
from TIPCommon.data_models import BaseAlert


class IssuesConnector(Connector):
    def __init__(self, *args, **kwargs):
        super(IssuesConnector, self).__init__(*args, **kwargs)
        self.vars.all_issues = []
        self.vars.processed_issues = []

    def validate_params(self) -> None:
        if self.params.lowest_severity_to_fetch:
            self.params.lowest_severity = self.param_validator.validate_ddl(
                param_name="Lowest Severity To Fetch",
                value=self.params.lowest_severity_to_fetch,
                ddl_values=POSSIBLE_SEVERITIES,
            )
        else:
            self.params.lowest_severity = ""

        self.params.max_hours = self.param_validator.validate_lower_limit(
            param_name="Max Hours Backwards",
            value=self.params.max_hours_backwards,
            limit=1,
            default_value=DEFAULT_HOURS_BACKWARDS,
        )

        self.params.fetch_limit = self.param_validator.validate_lower_limit(
            param_name="Max Issues To Fetch",
            value=self.params.max_issues_to_fetch,
            limit=1,
            default_value=DEFAULT_LIMIT_FOR_CONNECTOR,
        )
        if (self.params.access_key and self.params.secret_key and
                not self.params.gtiapi_key and not self.params.project_name):
            raise InvalidParametersException("Project Name should be provided, "
                                             "if you are working with "
                                             "Access Key and Secret Key.")

    def init_managers(self) -> None:
        self.manager = MandiantASMManager(
            api_root=self.params.api_root,
            access_key=self.params.access_key,
            secret_key=self.params.secret_key,
            gti_api_key=self.params.gtiapi_key,
            project_name=self.params.project_name,
            verify_ssl=self.params.verify_ssl,
            siemplify_logger=self.logger,
        )

    def get_last_success_time(self):
        return super().get_last_success_time(
            max_backwards_param_name="max_hours",
            metric="hours",
            date_time_format=DATETIME_FORMAT_FOR_CONNECTOR,
        )

    def read_context_data(self) -> None:
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = read_ids(self.siemplify)

    def store_alert_in_cache(self, alert: ConnectorIssue):
        self.context.existing_ids.append(alert.alert_id)

    def set_last_success_time(self, alerts: list[BaseAlert]):
        super().set_last_success_time(alerts=alerts, timestamp_key="first_seen_ms")

    def write_context_data(self, processed_alerts) -> None:
        self.logger.info("Saving existing ids.")
        write_ids(self.siemplify, self.context.existing_ids)

    def get_alerts(self) -> list[ConnectorIssue]:
        return self.manager.get_issues(
            first_seen_after=self.context.last_success_timestamp,
            severity=SEVERITY_MAPPING.get(self.params.lowest_severity.lower(), ""),
            limit=self.params.fetch_limit,
        )

    def filter_alerts(self, alerts: list[ConnectorIssue]) -> list[ConnectorIssue]:
        return filter_old_alerts(
            self.siemplify, alerts, self.context.existing_ids, "issue_id"
        )

    def pass_filters(self, alert: ConnectorIssue) -> bool:
        if not pass_whitelist_filter(
            self.siemplify,
            self.params.use_dynamic_list_as_a_blocklist,
            alert,
            "category",
        ):
            return False

        return True

    def max_alerts_processed(self, processed_alerts) -> bool:
        if len(processed_alerts) >= self.params.fetch_limit:
            return True

    def process_alert(self, alert: ConnectorIssue) -> ConnectorIssue:
        return self.manager.get_issue_details(issue_id=alert.issue_id)

    def process_alerts(
        self,
        filtered_alerts: list[BaseAlert],
        timeout_threshold: float = TIMEOUT_THRESHOLD,
    ) -> list[BaseAlert]:
        return super().process_alerts(filtered_alerts, timeout_threshold)

    def create_alert_info(self, alert: ConnectorIssue) -> AlertInfo:
        self.logger.info(f"Creating alert info for alert {alert.issue_id}")
        alert_info = AlertInfo()
        alert_info.ticket_id = alert.issue_id
        alert_info.display_id = f"MANDIANT_ASM_{alert.issue_id}"
        alert_info.name = alert.pretty_name
        if type(alert.proof) == str:
            alert_info.reason = alert.proof
        else:
            alert_info.reason = json.dumps(alert.proof)
        alert_info.description = alert.description
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = (
            alert.flat_raw_data.get(self.params.device_product_field)
            or DEFAULT_DEVICE_PRODUCT
        )
        alert_info.priority = PRIORITY_MAPPING.get(alert.severity, -1)
        alert_info.rule_generator = f"MASM:{alert.pretty_name}"
        alert_info.source_grouping_identifier = alert.category
        alert_info.start_time = convert_string_to_unix_time(alert.first_seen)
        alert_info.end_time = convert_string_to_unix_time(alert.last_seen)
        alert_info.environment = self.env_common.get_environment(alert.flat_raw_data)
        alert_info.events = alert.to_events()

        return alert_info


def main() -> None:
    """main"""
    script_name = ISSUES_CONNECTOR_NAME
    is_test = is_test_run(sys.argv)
    connector = IssuesConnector(script_name, is_test)
    connector.start()


if __name__ == "__main__":
    main()
