from __future__ import annotations

import copy
import json
import sys

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time, unix_now

from TIPCommon.base.connector import Connector
from TIPCommon.filters import filter_old_alerts, pass_whitelist_filter
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.transformation import dict_to_flat, string_to_multi_value
from TIPCommon.utils import is_empty_string_or_none, is_test_run

from google_threat_intelligence.core.api_manager import ApiManager
from google_threat_intelligence.core.auth_manager import AuthManager, AuthManagerParams
from google_threat_intelligence.core.constants import (
    ASM_ISSUE_SEVERITY_MAPPING,
    ASM_ISSUES_CONNECTOR_NAME,
    ASM_ISSUES_TIME_FORMAT,
    DEFAULT_ASM_DEVICE_PRODUCT,
    DEFAULT_DEVICE_VENDOR,
    DEFAULT_ISSUE_STATUS_FILTER,
    ISSUE_STATUS_LIST,
    ISSUES_POSSIBLE_SEVERITIES,
    MAX_PAGE_SIZE,
    PRIORITY_MAPPING,
    STORED_IDS_LIMIT,
)
from google_threat_intelligence.core.data_models import ASMIssue


class IssuesConnector(Connector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager: ApiManager | None = None

    def extract_params(self) -> None:
        """Extract action parameters and populate them into .params container."""
        super().extract_params()

        self.params.auth_params = AuthManagerParams(
            api_root=self.params.api_root,
            api_key=self.params.api_key,
            asm_project_name=self.params.project_name,
            active_group=self.params.active_group,
            verify_ssl=self.params.verify_ssl,
        )

    def validate_params(self) -> None:
        """Validate connector parameters."""
        if not is_empty_string_or_none(self.params.lowest_severity_to_fetch):
            self.params.lowest_severity_to_fetch = self.param_validator.validate_ddl(
                param_name="Lowest Severity To Fetch",
                value=self.params.lowest_severity_to_fetch,
                ddl_values=ISSUES_POSSIBLE_SEVERITIES,
            )
        else:
            self.params.lowest_severity_to_fetch = ""

        self.params.max_hours_backwards = self.param_validator.validate_positive(
            param_name="Max Hours Backwards", value=self.params.max_hours_backwards
        )

        self.params.max_issues_to_fetch = self.param_validator.validate_positive(
            param_name="Max Issues To Fetch", value=self.params.max_issues_to_fetch
        )
        if self.params.max_issues_to_fetch > MAX_PAGE_SIZE:
            self.logger.info(
                f"Invalid parameter: Max Issues To Fetch, value provided: "
                f"{self.params.max_issues_to_fetch}, "
                f"Issue: The value can't be greater then {MAX_PAGE_SIZE}, "
                f"Max possible value {MAX_PAGE_SIZE} "
                f"will be used instead."
            )
            self.params.max_issues_to_fetch = MAX_PAGE_SIZE

        self._validate_status_filter()
        self.params.issue_name_filter = self.param_validator.validate_csv(
            param_name="Issue Type Filter",
            csv_string=self.params.issue_name_filter,
            print_value=True,
        )

    def _validate_status_filter(self) -> None:
        if is_empty_string_or_none(self.params.status_filter):
            self.params.status_filter = [DEFAULT_ISSUE_STATUS_FILTER]
            return

        status_filters: list[str] = string_to_multi_value(
            string_value=self.params.status_filter,
            only_unique=True,
        )
        if all(s.lower() in ISSUE_STATUS_LIST for s in status_filters):
            self.params.status_filter = status_filters
            return

        raise ValueError(
            "Invalid parameter: Status Filter, value provided: "
            f"{self.params.status_filter}\nPossible Values: Open, Closed."
        )

    def init_managers(self) -> None:
        """Create manager instance objects"""
        auth_manager = AuthManager(params=self.params.auth_params)
        session = auth_manager.prepare_session()

        self.manager = ApiManager(
            api_root=self.params.api_root,
            session=session,
            asm_project_name=auth_manager.asm_project_name,
            logger=self.logger,
        )
        self.manager.set_project_id(self.params.project_name)

    def get_last_success_time(self):
        """Get last_success_time for connector from DB (or FileStorage)."""
        return super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards",
            metric="hours",
            date_time_format=ASM_ISSUES_TIME_FORMAT,
        )

    def read_context_data(self) -> None:
        """Read connector's context data from DB (or FileStorage)."""
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = list(read_ids(self.siemplify))

    def store_alert_in_cache(self, alert: ASMIssue) -> None:
        """Store alert id in connector IDs cache

        Args:
            alert (Alert): Alert dataclass

        """
        self.context.existing_ids.append(alert.issue_id)

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

    def set_last_success_time(self, all_alerts: list[ASMIssue], *_) -> None:
        """Save last_success_time into DB (or FileStorage)

        When no alert was processed, the timestamp is advanced to the end of the
        last time window the manager confirmed to hold no new issues, so the
        connector keeps progressing through periods without issues.

        Args:
            all_alerts ([Alert]): list of all fetched Alert dataclasses

        """
        if all_alerts:
            super().set_last_success_time(
                alerts=all_alerts, timestamp_key="last_seen_ms"
            )
            self._log_unchanged_timestamp(all_alerts)
            return

        if not self.manager.empty_scan_end:
            return

        last_success_timestamp: int = convert_string_to_unix_time(
            self.context.last_success_timestamp
        )
        new_timestamp: int = convert_string_to_unix_time(self.manager.empty_scan_end)
        if last_success_timestamp < new_timestamp < unix_now():
            self.logger.info(
                "No new issues were found. Saving timestamp "
                f"{self.manager.empty_scan_end}"
            )
            self.siemplify.save_timestamp(new_timestamp=new_timestamp)

    def _log_unchanged_timestamp(self, all_alerts: list[ASMIssue]) -> None:
        """Explain in the log why the saved timestamp did not move forward."""
        last_success_timestamp: int = convert_string_to_unix_time(
            self.context.last_success_timestamp
        )
        if max(alert.last_seen_ms for alert in all_alerts) > last_success_timestamp:
            return

        self.logger.info(
            f"The last success timestamp stays at {self.context.last_success_timestamp}: "
            f"every processed issue ({len(all_alerts)}) was last seen at that time. It moves "
            "forward once all issues with this last seen time are ingested; the ingested ones "
            "are skipped by their ids."
        )

    def write_context_data(self, all_alerts: list[ASMIssue]) -> None:
        """Save connector context data into DB (or FileStorage)

        Args:
            all_alerts ([DTMAlert]): list of all fetched DTMAlert dataclasses

        """
        if all_alerts:
            self.logger.info("Saving existing ids.")

            write_ids(
                self.siemplify,
                self.context.existing_ids,
                stored_ids_limit=STORED_IDS_LIMIT,
            )

    def get_alerts(self) -> list[ASMIssue]:
        """Fetch new alerts

        Returns:
            List of ASMIssue dataclasses

        """
        return self.manager.get_issues(
            last_seen_after=self.context.last_success_timestamp,
            severity=ASM_ISSUE_SEVERITY_MAPPING.get(
                self.params.lowest_severity_to_fetch.lower(), ""
            ),
            limit=self.params.max_issues_to_fetch,
            siemplify=self.siemplify,
            existing_ids=self.context.existing_ids,
            status_filter=self.params.status_filter,
            issue_name_filter=set(self.params.issue_name_filter),
            connector_starting_time=self.connector_start_time,
            python_process_timeout=self.params.python_process_timeout,
        )

    def filter_alerts(self, alerts: list[ASMIssue]) -> list[ASMIssue]:
        """Filter fetched alerts to exclude already fetched ones

        Args:
            alerts ([DTMAlert]): list of DTMAlert dataclasses

        Returns:
            [Alert]: list of filtered Alert dataclasses sorted by alert.created_at

        """
        return sorted(
            filter_old_alerts(
                self.siemplify,
                alerts=alerts,
                existing_ids=set(self.context.existing_ids),
                id_key="issue_id",
            ),
            key=lambda _alert: _alert.last_seen_ms,
        )

    def pass_filters(self, alert: ASMIssue) -> bool:
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
            model_key="category",
        ):
            return False

        return True

    def max_alerts_processed(self, processed_alerts) -> bool:
        """Return True if reached the maximum alerts to process limit in
        the connector execution.

        Args:
            processed_alerts: A list of processed alerts.

        Returns:
            True if the maximum alerts to process limit has been reached,
            False otherwise.

        """
        if len(processed_alerts) >= self.params.max_issues_to_fetch:
            return True
        return False

    def process_alert(self, alert: ASMIssue) -> ASMIssue:
        """Extensive alert processing

        Args:
            alert: The alert to process.

        Returns:
            The processed alert.

        """
        return self.manager.get_issue_details(issue_id=alert.issue_id)

    @staticmethod
    def build_events_data(alert: ASMIssue) -> list[dict]:
        """Build events data out of alert

        Args:
            alert (ASMIssue): ASMIssue dataclass

        Returns:
            [dict]: list of flattened event dicts

        """
        event_data = copy.deepcopy(alert.raw_data)

        identifiers = event_data.get("identifiers")
        if not identifiers:
            identifiers = []

        identifier_count = {}
        for identifier in identifiers:
            if not event_data.get(identifier.get("type")):
                identifier_count[identifier.get("type")] = 1
            else:
                identifier_count[identifier.get("type")] += 1

            event_data[
                (
                    f"{identifier.get('type')}_"
                    f"{identifier_count.get(identifier.get('type'))}"
                )
            ] = identifier.get("name")

        event_data[event_data.get("entity_type")] = event_data.get("entity_name")

        return [dict_to_flat(event_data)]

    def create_alert_info(self, alert: ASMIssue) -> AlertInfo:
        """Create AlertInfo object out of and alert

        Args:
            alert (ASMIssue): ASMIssue dataclass

        Returns:
            AlertInfo: AlertInfo object

        """
        self.logger.info(f"Creating alert info for alert {alert.issue_id}")
        alert_info = AlertInfo()
        alert_info.ticket_id = alert.issue_id
        alert_info.display_id = f"GTI_{alert.issue_id}"
        alert_info.name = alert.pretty_name
        if isinstance(alert.proof, str):
            alert_info.reason = alert.proof
        else:
            alert_info.reason = json.dumps(alert.proof)
        alert_info.description = alert.description
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = (
            alert.raw_flat_data.get(self.params.device_product_field)
            or DEFAULT_ASM_DEVICE_PRODUCT
        )
        alert_info.priority = PRIORITY_MAPPING.get(alert.severity, -1)
        alert_info.rule_generator = f"GTI:{alert.pretty_name}"
        alert_info.source_grouping_identifier = alert.category
        alert_info.start_time = convert_string_to_unix_time(alert.first_seen)
        alert_info.end_time = convert_string_to_unix_time(alert.last_seen)
        alert_info.environment = self.env_common.get_environment(alert.raw_flat_data)
        alert_info.events = self.build_events_data(alert=alert)

        return alert_info


def main() -> None:
    """Main"""
    script_name = ASM_ISSUES_CONNECTOR_NAME
    is_test = is_test_run(sys.argv)
    connector = IssuesConnector(script_name, is_test)
    connector.start()


if __name__ == "__main__":
    main()
