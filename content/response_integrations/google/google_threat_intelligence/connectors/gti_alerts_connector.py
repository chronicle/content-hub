from __future__ import annotations

import datetime
import sys
from collections.abc import Callable
from typing import Any

import requests
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.base.connector import Connector
from TIPCommon.consts import DATETIME_FORMAT
from TIPCommon.filters import filter_old_alerts, pass_whitelist_filter
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.transformation import dict_to_flat
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_empty_string_or_none, is_test_run

from google_threat_intelligence.core.api_manager import ApiManager
from google_threat_intelligence.core.auth_manager import AuthManager, AuthManagerParams
from google_threat_intelligence.core.constants import (
    GTI_ALERTS_CONNECTOR_SCRIPT_NAME,
    GTI_ALERTS_DEFAULT_DEVICE_PRODUCT,
    GTI_ALERTS_DEFAULT_LIMIT,
    GTI_ALERTS_MAX_LIMIT,
    GTI_ALERTS_SEVERITIES,
    INTEGRATION_IDENTIFIER,
    SEVERITY_MAPPING,
    STORED_IDS_LIMIT,
)
from google_threat_intelligence.core.data_models import GTIAlert
from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceExceptions
from google_threat_intelligence.core.utils import parse_entity_filters, prepare_entity_filter


class GTIAlertsConnector(Connector):
    """Google Threat Intelligence (GTI) Alerts Connector for Chronicle SOAR.

    Ingests polymorphic security alerts from Google Threat Intelligence,
    transforms them into Siemplify AlertInfo objects with child events, and handles
    deduplication, severity filtering, and overflow control.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.manager: ApiManager | None = None
        self.allow_event_types: set[str] = set()
        self.block_event_types: set[str] = set()
        self.alert_type_filter: Callable[[Any], bool] | None = None

    def extract_params(self) -> None:
        """Extract connector parameters and populate them into .params container."""
        super().extract_params()

        self.params.auth_params = AuthManagerParams(
            api_root=self.params.api_root,
            api_key=self.params.api_key,
            asm_project_name=None,
            verify_ssl=self.params.verify_ssl,
        )

    def validate_params(self) -> None:
        """Validate connector parameters."""
        if not self.params.api_root or "projects/" not in self.params.api_root:
            raise GoogleThreatIntelligenceExceptions(
                "API Root must include the Google Cloud project path "
                "(e.g., https://threatintelligence.googleapis.com/v1beta/projects/YOUR_PROJECT_ID)."
            )

        self.params.max_alerts_to_fetch = self.param_validator.validate_positive(
            param_name="Max Alerts To Fetch",
            value=self.params.max_alerts_to_fetch,
        )
        self.params.max_alerts_to_fetch = self.param_validator.validate_upper_limit(
            param_name="Max Alerts To Fetch",
            value=self.params.max_alerts_to_fetch,
            limit=GTI_ALERTS_MAX_LIMIT,
            default_value=GTI_ALERTS_DEFAULT_LIMIT,
        )
        self.params.max_hours_backwards = self.param_validator.validate_positive(
            param_name="Max Hours Backwards",
            value=self.params.max_hours_backwards,
        )
        if not is_empty_string_or_none(self.params.lowest_severity_to_fetch):
            self.params.lowest_severity_to_fetch = self.param_validator.validate_ddl(
                param_name="Lowest Severity To Fetch",
                value=self.params.lowest_severity_to_fetch,
                ddl_values=GTI_ALERTS_SEVERITIES,
            )
        self.params.alert_type_filter = self.param_validator.validate_csv(
            param_name="Alert Type Filter",
            csv_string=self.params.alert_type_filter,
            print_value=True,
        )
        self.allow_event_types, self.block_event_types = parse_entity_filters(self.params.alert_type_filter)
        if self.allow_event_types or self.block_event_types:
            self.alert_type_filter = prepare_entity_filter(
                extractor=lambda _alert: _alert.detail_type,
                allow_list=self.allow_event_types,
                block_list=self.block_event_types,
            )
        else:
            self.alert_type_filter = None

    def init_managers(self) -> None:
        """Create manager instance objects."""
        auth_manager: AuthManager = AuthManager(params=self.params.auth_params)
        session: requests.Session = auth_manager.prepare_session()

        self.manager = ApiManager(
            api_root=self.params.api_root,
            session=session,
            asm_project_name=auth_manager.asm_project_name,
            logger=self.logger,
        )

    def get_last_success_time(self, *_: Any) -> datetime.datetime:
        """Get last_success_time for connector from DB (or FileStorage)."""
        return super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards",
            metric="hours",
            time_format=DATETIME_FORMAT,
        )

    def read_context_data(self) -> None:
        """Read connector's context data from DB (or FileStorage)."""
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = list(read_ids(self.siemplify))

    def store_alert_in_cache(self, alert: GTIAlert) -> None:
        """Store alert id in connector IDs cache.

        Args:
            alert: The GTI alert to cache in memory.

        """
        self.context.existing_ids.append(alert.alert_id)

    def is_overflow_alert(self, alert_info: AlertInfo) -> bool:
        """Check if alert is overflowed.

        Args:
            alert_info: AlertInfo object to evaluate.

        Returns:
            True if alert is overflowed, False otherwise.

        """
        return not self.params.disable_overflow and super().is_overflow_alert(alert_info)

    def set_last_success_time(self, all_alerts: list[GTIAlert], *_: Any) -> None:
        """Save last_success_time into DB (or FileStorage).

        Args:
            all_alerts: List of all fetched GTIAlert instances.

        """
        super().set_last_success_time(alerts=all_alerts, timestamp_key="update_time_unix")

    def write_context_data(self, all_alerts: list[GTIAlert]) -> None:
        """Save connector context data into DB (or FileStorage).

        Args:
            all_alerts: List of all fetched GTIAlert instances.

        """
        if all_alerts:
            self.logger.info("Saving existing ids.")
            write_ids(self.siemplify, self.context.existing_ids, stored_ids_limit=STORED_IDS_LIMIT)

    def get_alerts(self) -> list[GTIAlert]:
        """Fetch new alerts.

        Returns:
            List of fetched GTI alerts.

        """
        gti_alerts: list[GTIAlert] = self.manager.get_gti_alerts(
            gti_api_key=self.params.api_key,
            lowest_severity=self.params.lowest_severity_to_fetch,
            start_time=self.context.last_success_timestamp,
            limit=self.params.max_alerts_to_fetch,
            existing_ids=set(self.context.existing_ids),
            alert_types=self.allow_event_types if self.allow_event_types else None,
        )
        self.logger.info(f"Number of fetched alerts: {len(gti_alerts)}")
        return gti_alerts

    def filter_alerts(self, alerts: list[GTIAlert]) -> list[GTIAlert]:
        """Filter fetched alerts to exclude already fetched ones.

        Args:
            alerts: List of fetched GTI alerts to filter.

        Returns:
            Filtered alerts sorted chronologically by update time.

        """
        return sorted(
            filter_old_alerts(
                self.siemplify,
                alerts=alerts,
                existing_ids=set(self.context.existing_ids),
                id_key="alert_id",
            ),
            key=lambda _alert: _alert.update_time_unix,
        )

    def pass_filters(self, alert: GTIAlert) -> bool:
        """Check if alert passes dynamic list filter and alert type filter.

        Args:
            alert: The GTI alert to evaluate against filters.

        Returns:
            True if passes filter, False otherwise.

        """
        if self.siemplify.whitelist and not pass_whitelist_filter(
            self.siemplify,
            self.params.use_dynamic_list_as_a_blocklist,
            model=alert,
            model_key="detail_type",
        ):
            return False

        if self.alert_type_filter and not self.alert_type_filter(alert):
            return False

        return True

    def build_events_data(self, alert: GTIAlert) -> list[SingleJson]:
        """Build events data out of alert.

        Args:
            alert: The GTI alert to transform into events.

        Returns:
            List of flattened event dictionaries.

        """
        return [dict_to_flat(event) for event in alert.to_events()]

    def create_alert_info(self, alert: GTIAlert) -> AlertInfo:
        """Create AlertInfo object out of an alert.

        Args:
            alert: The GTI alert to convert into AlertInfo.

        Returns:
            AlertInfo object.

        """
        alert_info: AlertInfo = AlertInfo()

        alert_info.ticket_id = alert.alert_id
        alert_info.display_id = alert.alert_id
        alert_info.name = alert.display_name
        alert_info.description = alert.summary
        alert_info.device_vendor = INTEGRATION_IDENTIFIER
        alert_info.device_product = (
            alert.raw_flat_data.get(self.params.device_product_field)
            or GTI_ALERTS_DEFAULT_DEVICE_PRODUCT
        )
        priority_key: str = (alert.priority or alert.severity).lower()
        alert_info.priority = SEVERITY_MAPPING.get(priority_key, 40)
        alert_info.rule_generator = alert.detail_type
        alert_info.source_grouping_identifier = alert.alert_id
        alert_info.start_time = alert.create_time_unix
        alert_info.end_time = alert.update_time_unix or alert.create_time_unix
        alert_info.environment = self.env_common.get_environment(alert.raw_flat_data)
        alert_info.events = self.build_events_data(alert=alert)
        alert_info.extensions = {
            "RiskScore": alert_info.priority,
            "Severity": alert.severity.capitalize(),
        }
        if cve := alert.cve:
            alert_info.extensions["CVE"] = cve

        return alert_info


def main() -> None:
    """Main entry point for the GTI Alerts Connector."""
    script_name: str = GTI_ALERTS_CONNECTOR_SCRIPT_NAME
    is_test: bool = is_test_run(sys.argv)
    connector: GTIAlertsConnector = GTIAlertsConnector(script_name, is_test)
    connector.start()


if __name__ == "__main__":
    main()
