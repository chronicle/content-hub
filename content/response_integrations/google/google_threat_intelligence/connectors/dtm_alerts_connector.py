from __future__ import annotations

import copy
import datetime
import sys
import uuid

from google_threat_intelligence.core.api_manager import ApiManager
from google_threat_intelligence.core.auth_manager import AuthManager, AuthManagerParams
from google_threat_intelligence.core.constants import (
    DEFAULT_DEVICE_PRODUCT,
    DEFAULT_DEVICE_VENDOR,
    DTM_ALERTS_CONNECTOR,
    DTM_DATE_TIME_FORMAT,
    EVENTS_LIMIT,
    INTEGRATION_PREFIX,
    MAIN_ALERT_EVENT_TYPE,
    MAX_LIMIT,
    SEVERITIES,
    SEVERITY_MAPPING,
    STORED_IDS_LIMIT,
)
from google_threat_intelligence.core.data_models import DTMAlert
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.base.connector import Connector
from TIPCommon.consts import DATETIME_FORMAT, TIMEOUT_THRESHOLD
from TIPCommon.data_models import BaseAlert
from TIPCommon.filters import filter_old_alerts, pass_whitelist_filter
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.transformation import (
    convert_comma_separated_to_list,
    convert_list_to_comma_string,
    dict_to_flat,
)
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_empty_string_or_none, is_test_run

from google_threat_intelligence.core.utils import (
    anonymize_compromised_credentials,
    parse_entity_filters,
    prepare_entity_filter,
)


class DTMAlertsConnector(Connector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager: ApiManager | None = None
        self.allow_event_types: set[str] = set()
        self.block_event_types: set[str] = set()

    def extract_params(self) -> None:
        """Extract action parameters and populate them into .params container."""
        super().extract_params()

        self.params.auth_params = AuthManagerParams(
            api_root=self.params.api_root,
            api_key=self.params.api_key,
            asm_project_name=None,
            verify_ssl=self.params.verify_ssl,
        )

    def validate_params(self) -> None:
        """Validate connector parameters."""
        self.params.max_alerts_to_fetch = self.param_validator.validate_positive(
            param_name="Max Alerts To Fetch", value=self.params.max_alerts_to_fetch
        )
        self.params.max_alerts_to_fetch = self.param_validator.validate_upper_limit(
            param_name="Max Alerts To Fetch",
            value=self.params.max_alerts_to_fetch,
            limit=MAX_LIMIT,
            default_value=MAX_LIMIT,
        )
        self.params.max_hours_backwards = self.param_validator.validate_positive(
            param_name="Max Hours Backwards", value=self.params.max_hours_backwards
        )
        if not is_empty_string_or_none(self.params.lowest_severity_to_fetch):
            self.params.lowest_severity_to_fetch = self.param_validator.validate_ddl(
                param_name="Lowest Severity To Fetch",
                value=self.params.lowest_severity_to_fetch,
                ddl_values=SEVERITIES,
            )
        self.params.event_type_filter = self.param_validator.validate_csv(
            param_name="Event Type Filter",
            csv_string=self.params.event_type_filter,
            print_value=True,
        )
        self.allow_event_types, self.block_event_types = parse_entity_filters(
            self.params.event_type_filter
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

    def get_last_success_time(self, *_) -> datetime.datetime:
        """Get last_success_time for connector from DB (or FileStorage)."""
        return super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards",
            metric="hours",
            time_format=DATETIME_FORMAT,
            date_time_format=DTM_DATE_TIME_FORMAT,
        )

    def read_context_data(self) -> None:
        """Read connector's context data from DB (or FileStorage)."""
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = list(read_ids(self.siemplify))

    def store_alert_in_cache(self, alert: DTMAlert) -> None:
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

    def set_last_success_time(self, all_alerts: list[DTMAlert], *_) -> None:
        """Save last_success_time into DB (or FileStorage)

        Args:
            all_alerts ([Alert]): list of all fetched Alert dataclasses

        """
        super().set_last_success_time(alerts=all_alerts, timestamp_key="created_at")

    def write_context_data(self, all_alerts: list[DTMAlert]) -> None:
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

    def get_alerts(self) -> list[DTMAlert]:
        """Fetch new alerts

        Returns:
            List of DTMAlert dataclasses

        """
        fetched_alerts = self.manager.get_dtm_alerts(
            timestamp=self.context.last_success_timestamp,
            lowest_severity=self.params.lowest_severity_to_fetch,
            monitor_ids=convert_comma_separated_to_list(self.params.monitor_id_filter),
            monitor_names=convert_comma_separated_to_list(
                self.params.monitor_name_filter
            ),
            limit=self.params.max_alerts_to_fetch,
            existing_ids=set(self.context.existing_ids),
            alert_types=(
                self.siemplify.whitelist
                if not self.params.use_dynamic_list_as_a_blocklist
                else None
            ),
            siemplify=self.siemplify,
        )

        self.logger.info(f"Number of fetched alerts: {len(fetched_alerts)}")
        return fetched_alerts

    def filter_alerts(self, alerts: list[DTMAlert]) -> list[DTMAlert]:
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
                id_key="alert_id",
            ),
            key=lambda _alert: _alert.created_at,
        )

    def pass_filters(self, alert: DTMAlert) -> bool:
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
            model_key="alert_type",
        ):
            return False

        return True

    def build_events_data(self, alert: DTMAlert) -> list[dict]:
        """Build events data out of alert

        Args:
            alert (DTMAlert): DTMAlert dataclass

        Returns:
            [dict]: list of flattened event dicts

        """
        events = [self.build_main_event(alert)]
        events.extend(self.build_topic_events(alert))
        return events

    def build_main_event(self, alert: DTMAlert) -> SingleJson:
        """Build main event data out of alert.

        Args:
            alert: DTMAlert dataclass.

        Returns:
            Main event flat dict.

        """
        alert_data = copy.deepcopy(alert.raw_data)

        if self.params.anonymize_passwords:
            anonymize_compromised_credentials(alert_data)

        alert_data.get("doc", {}).pop("body", None)
        alert_data.pop("topics", [])
        alert_data["event_type"] = MAIN_ALERT_EVENT_TYPE
        alert_data["labels"] = convert_list_to_comma_string(
            [label.get("label") for label in alert_data.get("labels", [])]
        )

        return dict_to_flat(alert_data)

    def build_topic_events(self, alert: DTMAlert) -> list[dict]:
        """Build events data out of alert topics, applying event type filters.

        Args:
            alert (DTMAlert): DTMAlert dataclass

        Returns:
            [dict]: list of topic events flat dicts

        """
        topics_data = copy.deepcopy([topic.raw_data for topic in alert.topics])
        topic_events = []

        topic_event_type_filter = prepare_entity_filter(
            extractor=lambda topic: topic.get("type"),
            allow_list=self.allow_event_types,
            block_list=self.block_event_types,
        )

        for topic in filter(topic_event_type_filter, topics_data):
            topic["event_type"] = topic.get("type")
            topic["timestamp"] = alert.raw_data.get("created_at")
            topic[topic.get("type")] = topic.get("value")

            topic_events.append(dict_to_flat(topic))

        return topic_events

    def create_alert_info(self, alert: DTMAlert) -> AlertInfo:
        """Create AlertInfo object out of and alert

        Args:
            alert (DTMAlert): DTMAlert dataclass

        Returns:
            AlertInfo: AlertInfo object

        """
        alert_info = AlertInfo()

        alert_info.ticket_id = alert.alert_id
        alert_info.display_id = f"{INTEGRATION_PREFIX}{alert.alert_id}"
        alert_info.name = alert.title
        alert_info.description = alert.alert_summary
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = (
            alert.raw_flat_data.get(self.params.device_product_field)
            or DEFAULT_DEVICE_PRODUCT
        )
        alert_info.priority = SEVERITY_MAPPING.get(alert.severity, -1)
        alert_info.rule_generator = f"{DEFAULT_DEVICE_VENDOR}: {alert.alert_type}"
        alert_info.source_grouping_identifier = (
            alert.aggregated_under_id or alert.monitor_name
        )
        alert_info.start_time = alert.created_at
        alert_info.end_time = alert.created_at
        alert_info.environment = self.env_common.get_environment(alert.raw_flat_data)
        alert_info.events = self.build_events_data(alert=alert)

        return alert_info

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
        processed_alerts, all_alerts = super().process_alerts(
            filtered_alerts, timeout_threshold
        )

        processed_alerts = self.split_processed_alerts(processed_alerts)

        return processed_alerts, all_alerts

    @staticmethod
    def split_processed_alerts(processed_alerts: [AlertInfo]):
        """Split processed alerts to contain EVENTS_LIMIT amount events per each alert

        Args:
            processed_alerts ([AlertInfo]): list of AlertInfo objects

        Returns:
            ([AlertInfo]): list of split AlertInfo objects

        """
        split_alerts = []

        for processed_alert in processed_alerts:
            if len(processed_alert.events) > EVENTS_LIMIT:
                main_event = copy.deepcopy(processed_alert.events[0])

                for split_events in [
                    processed_alert.events[i : i + EVENTS_LIMIT - 1]
                    for i in range(1, len(processed_alert.events), EVENTS_LIMIT - 1)
                ]:
                    new_alert = copy.deepcopy(processed_alert)
                    new_alert.events = [main_event] + split_events
                    new_alert.display_id = f"{new_alert.display_id}_{uuid.uuid4()!s}"
                    split_alerts.append(new_alert)
            else:
                processed_alert.display_id = (
                    f"{processed_alert.display_id}_{uuid.uuid4()!s}"
                )
                split_alerts.append(processed_alert)

        return split_alerts


def main() -> None:
    """Main"""
    script_name = DTM_ALERTS_CONNECTOR
    is_test = is_test_run(sys.argv)
    connector = DTMAlertsConnector(script_name, is_test)
    connector.start()


if __name__ == "__main__":
    main()
