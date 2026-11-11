from __future__ import annotations

import copy
import sys

from google_threat_intelligence.core.api_manager import ApiManager
from google_threat_intelligence.core.auth_manager import AuthManager, AuthManagerParams
from google_threat_intelligence.core.constants import (
    DEFAULT_DEVICE_VENDOR,
    DEFAULT_HOURS_BACKWARDS,
    DEFAULT_NOTIFICATIONS_LIMIT,
    LIVEHUNT_CONNECTOR,
    LIVEHUNT_CONNECTOR_DEFAULT_DEVICE_PRODUCT,
    STORED_IDS_LIMIT,
)
from google_threat_intelligence.core.data_models import Notification
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.base.connector import Connector
from TIPCommon.consts import TIMEOUT_THRESHOLD, UNIX_FORMAT
from TIPCommon.data_models import BaseAlert
from TIPCommon.filters import pass_whitelist_filter
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.transformation import dict_to_flat
from TIPCommon.utils import is_test_run


class LivehuntConnector(Connector):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.manager: ApiManager | None = None

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
        self.params.max_hours_backwards = self.param_validator.validate_positive(
            param_name="Max Hours Backwards",
            value=self.params.max_hours_backwards,
            default_value=DEFAULT_HOURS_BACKWARDS,
        )

        self.params.max_notifications_to_fetch = self.param_validator.validate_positive(
            param_name="Max Notifications To Fetch",
            value=self.params.max_notifications_to_fetch,
            default_value=DEFAULT_NOTIFICATIONS_LIMIT,
        )

        self.params.entity_type_filter = self.param_validator.validate_csv(
            param_name="Entity Type Filter",
            csv_string=self.params.entity_type_filter,
            print_value=True,
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

    def get_last_success_time(self, *_) -> int:
        """Get last_success_time for connector from DB (or FileStorage)."""
        last_success_time = super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards",
            metric="hours",
            time_format=UNIX_FORMAT,
        )
        last_success_time = last_success_time // 1000

        return last_success_time

    def read_context_data(self) -> None:
        """Read connector's context data from DB (or FileStorage)."""
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = list(read_ids(self.siemplify))

    def store_alert_in_cache(self, alert: Notification) -> None:
        """Store alert id in connector IDs cache

        Args:
            alert (Notification): Notification dataclass

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

    def set_last_success_time(self, all_alerts: list[Notification], *_) -> None:
        """Save last_success_time into DB (or FileStorage)

        Args:
            all_alerts (list[Notification]): list of all Notification dataclasses

        """
        super().set_last_success_time(alerts=all_alerts, timestamp_key="timestamp")

    def write_context_data(self, all_alerts: list[Notification]) -> None:
        """Save connector context data into DB (or FileStorage)

        Args:
            all_alerts (list[Notification]): list of all Notification dataclasses

        """
        if all_alerts:
            self.logger.info("Saving existing ids.")

            write_ids(
                self.siemplify,
                self.context.existing_ids,
                stored_ids_limit=STORED_IDS_LIMIT,
            )

    def get_alerts(self) -> list[Notification]:
        """Fetch new alerts

        Returns:
            list[Notification]: List of Notification dataclasses

        """
        filters = {
            "date": f"{self.context.last_success_timestamp}+",
            "source_type": "hunting_ruleset",
        }
        if self.params.entity_type_filter:
            filters["entity_type"] = [
                entity_type.lower() for entity_type in self.params.entity_type_filter
            ]

        fetched_alerts = self.manager.get_ioc_stream(
            limit=self.params.max_notifications_to_fetch,
            siemplify=self.siemplify,
            existing_ids=self.context.existing_ids,
            filters=filters,
        )

        self.logger.info(f"Number of fetched alerts: {len(fetched_alerts)}")
        return fetched_alerts

    def pass_filters(self, alert: Notification) -> bool:
        """Check if alert passes dynamic list filter

        Args:
            alert (Notification): Notification dataclass

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

    def build_events_data(self, alert: Notification) -> list[dict[str, str]]:
        """Build events data out of alert

        Args:
            alert (Notification): Notification dataclass

        Returns:
            list[dict[str, str]]: list of flattened event dicts

        """
        return [self.build_main_event(alert)]

    @staticmethod
    def build_main_event(alert: Notification) -> dict[str, str]:
        """Build main event data out of alert

        Args:
            alert (Notification): Notification dataclass

        Returns:
            dict[str, str]: main event flat dict

        """
        alert_data = copy.deepcopy(alert.raw_data)
        return dict_to_flat(alert_data)

    def create_alert_info(self, alert: Notification) -> AlertInfo:
        """Create AlertInfo object out of an alert

        Args:
            alert (Notification): Notification dataclass

        Returns:
            AlertInfo: AlertInfo object

        """
        alert_info = AlertInfo()

        alert_info.ticket_id = alert.alert_id
        alert_info.display_id = alert.alert_id
        alert_info.name = (
            alert.meaningful_name if alert.meaningful_name else alert.rule_name
        )
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = (
            alert.raw_flat_data.get(self.params.device_product_field)
            or LIVEHUNT_CONNECTOR_DEFAULT_DEVICE_PRODUCT
        )
        alert_info.priority = alert.get_severity()
        alert_info.rule_generator = alert.rule_name
        alert_info.source_grouping_identifier = alert.rule_name
        alert_info.start_time = alert.timestamp
        alert_info.end_time = alert.timestamp
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
            filtered_alerts (list[BaseAlert]): list of filtered BaseAlert objects
            timeout_threshold (float): timeout threshold for connector execution

        Returns:
            tuple containing list of AlertInfo objects, and list of BaseAlert objects

        """
        processed_alerts, all_alerts = super().process_alerts(
            filtered_alerts, timeout_threshold
        )

        return processed_alerts, all_alerts


def main() -> None:
    """Main"""
    script_name = LIVEHUNT_CONNECTOR
    is_test = is_test_run(sys.argv)
    connector = LivehuntConnector(script_name, is_test)
    connector.start()


if __name__ == "__main__":
    main()
