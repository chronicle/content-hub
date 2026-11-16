# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import asyncio
import copy
import datetime
import json
import uuid
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time, utc_now
from TIPCommon.extraction import extract_connector_param
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC, NUM_OF_SEC_IN_MIN
from TIPCommon.filters import filter_old_alerts, pass_whitelist_filter
from TIPCommon.transformation import dict_to_flat
from TIPCommon.smp_time import unix_now
from TIPCommon.base.connector.async_connector import AsyncConnector
from TIPCommon.exceptions import ConnectorSetupError
from ..core import constants
from ..core.datamodels import Incident, IncidentAlert, IncidentProperties
from ..core.exceptions import (
    MicrosoftAzureSentinelError,
    TimeoutIsApproachingError,
    MicrosoftAzureSentinelIncidentNotFoundError,
)
from ..core.MicrosoftAzureSentinelCommon import (
    create_regular_alert_events,
    create_scheduled_alert_events,
    MicrosoftAzureSentinelCommon,
    read_backlog_ids,
    read_next_page_alerts,
    write_backlog_ids,
    write_next_page_alerts,
)
from ..core.MicrosoftAzureSentinelAsyncManager import MicrosoftAzureSentinelAsyncManager
from ..core.MicrosoftAzureSentinelParser import MicrosoftAzureSentinelParser
from ..core.utils import (
    convert_hours_to_milliseconds,
    dict_to_md5_hash,
    get_chunks_as_context_property,
    get_value_from_template,
    find_fallback_value,
    set_chunks_as_context_property,
    split_dict_into_chunks,
)

if TYPE_CHECKING:
    from typing import Any, TypeAlias

    from TIPCommon.types import SingleJson

    KqlLookup: TypeAlias = dict[str, SingleJson]


class IncidentTrackingConnector(AsyncConnector):
    def __init__(self) -> None:
        super().__init__(script_name=constants.INCIDENT_TRACKING_CONNECTOR_NAME)
        self.coros_limit = constants.COROS_LIMIT
        self.manager: MicrosoftAzureSentinelAsyncManager | None = None
        self.sentinel_common = MicrosoftAzureSentinelCommon(self.logger)
        self.processed_items = {}

    def extract_params(self) -> None:
        """Extract action parameters and populate them into .params container."""
        super().extract_params()

        self.params.use_same_approach = extract_connector_param(
            self.siemplify,
            param_name=(
                "Use the same approach with event creation for all alert types?"
            ),
            input_type=bool,
            print_value=True,
        )
        self.params.alerts_for_no_entities = extract_connector_param(
            self.siemplify,
            param_name=(
                "Create Chronicle SOAR Alerts for Sentinel incidents that do "
                "not have entities?"
            ),
            input_type=bool,
            print_value=True,
        )
        self.params.fallback_logic_debug = extract_connector_param(
            self.siemplify,
            param_name="Enable Fallback Logic Debug?",
            input_type=bool,
            print_value=True,
        )

        self.params.incidents_padding_period = extract_connector_param(
            self.siemplify,
            param_name="Incidents Padding Period (minutes)",
            input_type=int,
            print_value=True,
            default_value=0,
        )
        self.params.incident_creation_time_filter_days = extract_connector_param(
            self.siemplify,
            param_name="Incident Creation Time Filter (days)",
            print_value=True,
        )
        self.params.incidents_tracking_hours = extract_connector_param(
            self.siemplify,
            param_name="How many hours to track ingested incident for updates",
            is_mandatory=True,
            input_type=int,
            print_value=True,
            default_value=constants.INCIDENTS_TRACKING_DEFAULT_HOURS,
        )
        self.params.scheduled_alerts_events_limit_to_ingest = extract_connector_param(
            self.siemplify,
            param_name="Total number of Scheduled Alerts Events Limit to Ingest",
            input_type=int,
            print_value=True,
        )
        self.params.wait_for_scheduled_alerts = extract_connector_param(
            self.siemplify,
            param_name="Wait For Scheduled/NRT Alert Object",
            input_type=bool,
            print_value=True,
            default_value=False
        )

    def validate_params(self) -> None:
        """Validate connector parameters."""
        self.params.max_incidents_per_cycle = self.param_validator.validate_positive(
            param_name="Max Incidents per Cycle",
            value=self.params.max_incidents_per_cycle,
        )

        if self.params.max_incidents_per_cycle > constants.COROS_LIMIT:
            self.params.max_incidents_per_cycle = constants.COROS_LIMIT

        self.params.max_backlog_incidents_per_cycle = (
            self.param_validator.validate_positive(
                param_name="Max Backlog Incidents per cycle",
                value=self.params.max_backlog_incidents_per_cycle,
            )
        )
        if self.params.max_backlog_incidents_per_cycle > constants.COROS_LIMIT:
            self.params.max_backlog_incidents_per_cycle = constants.COROS_LIMIT

        self.params.max_hours_backwards = self.param_validator.validate_positive(
            param_name="Max Hours Backwards", value=self.params.max_hours_backwards
        )
        self.params.scheduled_alerts_events_limit_to_ingest = (
            self.param_validator.validate_positive(
                param_name="Total number of Scheduled Alerts Events Limit to Ingest",
                value=self.params.scheduled_alerts_events_limit_to_ingest,
            )
        )
        self.params.backlog_expiration_timer = self.param_validator.validate_positive(
            param_name="Backlog Expiration Timer",
            value=self.params.backlog_expiration_timer,
        )
        if self.params.incidents_padding_period is not None:
            self.params.incidents_padding_period = (
                self.param_validator.validate_non_negative(
                    param_name="Incidents Padding Period (minutes)",
                    value=self.params.incidents_padding_period,
                )
            )

        if self.params.incident_creation_time_filter_days:
            try:
                self.params.incident_creation_time_filter_days = int(
                    self.params.incident_creation_time_filter_days
                )
                self.params.incident_creation_time_filter_days = (
                    self.param_validator.validate_positive(
                        param_name="Incident Creation Time Filter (days)",
                        value=self.params.incident_creation_time_filter_days,
                    )
                )
            except ValueError:
                raise ConnectorSetupError(
                    "Incident Creation Time Filter (days) must be a valid "
                    "positive integer."
                )

        self.params.incident_statuses_to_fetch = self.param_validator.validate_csv(
            param_name="Incident Statuses to Fetch",
            csv_string=self.params.incident_statuses_to_fetch,
        )
        self.params.incidents_tags_to_ingest = self.param_validator.validate_csv(
            param_name="Incidents Tags To Ingest",
            csv_string=self.params.incidents_tags_to_ingest,
        )
        self.params.incident_severities_to_fetch = self.param_validator.validate_csv(
            param_name="Incident Severities to Fetch",
            csv_string=self.params.incident_severities_to_fetch,
        )
        self.params.start_time_fallback = self.param_validator.validate_csv(
            param_name="StartTimeFallback", csv_string=self.params.start_time_fallback
        )
        self.params.end_time_fallback = self.param_validator.validate_csv(
            param_name="EndTimeFallback", csv_string=self.params.end_time_fallback
        )
        self.params.product_field_fallback = self.param_validator.validate_csv(
            param_name="ProductFieldFallback",
            csv_string=self.params.product_field_fallback,
        )
        self.params.vendor_field_fallback = self.param_validator.validate_csv(
            param_name="VendorFieldFallback",
            csv_string=self.params.vendor_field_fallback,
        )
        self.params.event_field_fallback = self.param_validator.validate_csv(
            param_name="EventFieldFallback", csv_string=self.params.event_field_fallback
        )
        self.params.incidents_tracking_hours = self.param_validator.validate_positive(
            param_name="How many hours to track ingested incident for updates",
            value=self.params.incidents_tracking_hours,
        )

    def init_managers(self) -> None:
        self.manager = MicrosoftAzureSentinelAsyncManager(
            api_root=self.params.api_root,
            client_id=self.params.client_id,
            client_secret=self.params.client_secret,
            tenant_id=self.params.entra_id_directory_id,
            workspace_id=self.params.azure_sentinel_workspace_name,
            resource=self.params.azure_resource_group,
            subscription_id=self.params.azure_subscription_id,
            login_url=self.params.oauth2_login_endpoint_url,
            verify_ssl=self.params.verify_ssl,
            siemplify=self.siemplify,
        )

    def get_last_success_time(self, *_) -> datetime.datetime:
        """Get last_success_time for connector from DB (or FileStorage)."""
        return super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards",
            metric="hours",
            padding_period_param_name="incidents_padding_period",
            padding_period_metric="minutes",
        )

    def read_context_data(self) -> None:
        """Read connector's context data from DB (or FileStorage)."""
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = get_chunks_as_context_property(
            self.siemplify, constants.IDS_KEY
        )
        self.context.expired_existing_ids = self._get_expired_existing_ids()
        self.context.backlog_ids = read_backlog_ids(self.siemplify)
        self.context.initial_backlog = set(self.context.backlog_ids)
        self.context.next_page_link = read_next_page_alerts(self.siemplify)

    def _get_expired_existing_ids(self) -> list[str]:
        """
        Get expired existing incident ids

        Returns:
            [str]: list of expired incident ids
        """
        tracking_ms = convert_hours_to_milliseconds(
            self.params.incidents_tracking_hours
        )

        return [
            key
            for key, value in self.context.existing_ids.items()
            if value.get("ingested_time", 0) + tracking_ms <= self.connector_start_time
        ]

    def store_alert_in_cache(self, incident: Incident) -> None:
        """Store alert in connector's IDs cache.

        Args:
            incident: Incident's data model

        Returns:
            None, updates self.context.existing_ids with incident.name
        """
        self.processed_items[incident.name] = self._collect_seen_ids(
            incident, self.context.existing_ids.get(incident.name)
        )

        self.context.existing_ids.update(
            {incident.name: self.processed_items[incident.name]}
        )

        original_name = getattr(incident, "original_name", incident.name)
        if original_name != incident.name:
            self.context.existing_ids.update(
                {
                    original_name: self._collect_seen_ids(
                        incident,
                        self.context.existing_ids.get(original_name)
                    )
                }
            )

    def is_overflow_alert(self, alert_info: AlertInfo) -> bool:
        return not self.params.disable_overflow and super().is_overflow_alert(
            alert_info
        )

    def set_last_success_time(
        self, filtered_alerts: list[Incident], unprocessed_alerts: list[Incident], *_
    ) -> None:
        """Saves last_success_time into DB (or FileStorage)."""

        def after_last_success_time(inc: Incident) -> bool:
            return (
                inc.last_modified_time_ts
                > self.context.last_success_timestamp.timestamp() * NUM_OF_MILLI_IN_SEC
            )

        valid_filtered_alerts = list(filter(after_last_success_time, filtered_alerts))

        if valid_filtered_alerts:
            # Check if we hit the processing limit!
            if len(valid_filtered_alerts) >= self.params.max_incidents_per_cycle:
                super().set_last_success_time(
                    filtered_alerts=valid_filtered_alerts[:1],
                    unprocessed_alerts=[],
                    timestamp_key="last_modified_time_ts",
                )
            else:
                super().set_last_success_time(
                    filtered_alerts=valid_filtered_alerts,
                    unprocessed_alerts=[],
                    timestamp_key="last_modified_time_ts",
                )

    def write_context_data(self, filtered_alerts: list[Incident], _: Any) -> None:
        """Saves connector's context data into DB (or FileStorage)."""
        if filtered_alerts:
            self._exclude_expired_data_from_existing_ids()
            self.logger.info("Saving existing ids.")
            set_chunks_as_context_property(
                self.siemplify,
                constants.IDS_KEY,
                split_dict_into_chunks(self.context.existing_ids),
            )

            self._exclude_fetched_alerts_from_backlog(filtered_alerts)

        if getattr(self.context, "backlog_changed", False):
            self.logger.info("Saving backlog ids.")
            write_backlog_ids(self.siemplify, self.context.backlog_ids)

    def _exclude_expired_data_from_existing_ids(self):
        """
        Exclude expired data from existing ids
        """
        for incident_id, values in self.context.existing_ids.items():
            if incident_id in self.context.expired_existing_ids:
                values.pop("alerts", None)

    def _exclude_fetched_alerts_from_backlog(self, fetched_alerts: list[Incident]):
        """
        Exclude from backlog fetched alerts that were already processed
        Args:
            fetched_alerts (list[Incident]): list of fetched alerts
        """
        incident_number_lookup = {
            str(incident.properties.incident_number)
            for incident in fetched_alerts
            if (
                incident.name in self.context.existing_ids
                or f"{incident.name}_0" in self.context.existing_ids
            )
        }

        if incident_number_lookup:
            self.context.next_page_link = ""


    async def finalize(self) -> None:
        """Connector finalization coroutine."""
        if not hasattr(self.context, "next_page_link"):
            return

        write_next_page_alerts(
            self.siemplify, data_to_write=self.context.next_page_link
        )

        if self.manager is not None:
            await self.manager.async_client.aclose()

    async def _get_backlog_incidents(self) -> list[Incident]:
        """Fetch backlog incidents data from Azure Sentinel.

        Returns:
            List of Incident data models
        """
        incident_tasks = [
            asyncio.create_task(
                self.manager.get_incident_by_number(incident_number=inc_number)
            )
            for inc_number in self.context.backlog_ids
        ]

        try:
            return await self._fetch_backlog_incidents_logic(incident_tasks)
        finally:
            for future in incident_tasks:
                if not future.done():
                    future.cancel()

    async def _fetch_backlog_incidents_logic(
        self, incident_tasks: list[asyncio.Task]
    ) -> list[Incident]:
        """Fetch backlog incidents logic.

        Args:
            incident_tasks: List of asyncio tasks fetching incidents.

        Returns:
            List of Incident data models.
        """
        fetched_backlog_incidents = []

        for backlog_incident_future in asyncio.as_completed(incident_tasks):
            try:
                self.sentinel_common.raise_if_timeout(
                    self.connector_start_time,
                    self.params.python_process_timeout,
                    constants.FETCH_TIMEOUT_THRESHOLD,
                )

                if (
                    len(fetched_backlog_incidents)
                    >= self.params.max_backlog_incidents_per_cycle
                ):
                    self.logger.info(
                        "Limit of backlog id's to process per cycle is reached, "
                        "exiting ..."
                    )
                    break

                incident = await backlog_incident_future
                incident.is_from_backlog = True
                self.logger.info(
                    f"Fetched backlog incident "
                    f"{incident.properties.incident_number} ({incident.name})"
                )
                await self._fetch_events_if_needed(incident)
                fetched_backlog_incidents.append(incident)

            except TimeoutIsApproachingError as error:
                self.logger.info(str(error))
                break
            except MicrosoftAzureSentinelIncidentNotFoundError as error:
                inc_number, error_msg = error.args
                self.logger.error(
                    f"Failed to fetch {inc_number} backlog incident. "
                    f"Error: {error_msg}"
                )
            except Exception as e:
                self.logger.error(
                    f"Unexpected error when fetching backlog incident: {e}",
                    exc_info=True
                )

        return fetched_backlog_incidents

    def _build_prefilter_kql_query(
        self,
        creation_time: datetime.datetime | None
    ) -> str:
        """Build the KQL query for pre-filtering incidents.

        Args:
            creation_time: The timestamp filter for incident creation.

        Returns:
            The KQL query string.
        """
        time_format = "%Y-%m-%dT%H:%M:%SZ"
        creation_filter_line = ""
        if creation_time:
            creation_time_str = creation_time.strftime(time_format)
            creation_filter_line = (
                f"| where CreatedTime > datetime({creation_time_str})"
            )

        last_success_str = self.context.last_success_timestamp.strftime(
            time_format
        )
        updated_filter = f"datetime({last_success_str})"

        return constants.PRE_FILTER_KQL_QUERY.format(
            updated_filter=updated_filter,
            creation_filter_line=creation_filter_line,
        )

    async def _prefilter_incidents_via_kql(
        self,
        creation_time: datetime.datetime | None
    ) -> KqlLookup:
        """Pre-filter incidents using KQL query to optimize API request counts.

        Args:
            creation_time: The timestamp filter for incident creation.

        Returns:
            Dictionary containing mapped pre-filtering results.

        """
        kql_query = self._build_prefilter_kql_query(creation_time)
        kql_lookup = {}
        try:
            self.logger.info(f"Executing KQL pre-filter query: {kql_query}")
            query_result = await self.manager.run_kql_query(query=kql_query)
            if query_result:
                results_json = query_result.to_json()
                kql_lookup = {
                    row.get("IncidentName"): row
                    for row in results_json
                }
            else:
                self.logger.info("KQL query returned no results.")

        except Exception as e:
            self.logger.error(
                f"Failed to run KQL query for pre-filtering: {e}",
                exc_info=True,
            )

        return kql_lookup

    def _should_skip_via_kql_filter(
        self,
        alert: Incident,
        incident_number: str,
        kql_lookup: KqlLookup,
    ) -> bool:
        """Determine if an incident should be skipped based on pre-filter results.

        Args:
            alert: The incident object to evaluate.
            incident_number: The incident number as a string.
            kql_lookup: The lookup dictionary of pre-filtering stats.

        Returns:
            True if the incident should be skipped, otherwise False.

        """
        kql_record = kql_lookup.get(alert.name)
        if kql_record and incident_number not in self.context.backlog_ids:
            existing_record = self._get_existing_record(alert.name)
            existing_hashes = existing_record.get("entity_hashes", [])
            kql_hashes = json.loads(kql_record.get("AlertContentHashes") or "[]")
            kql_alerts_count = kql_record.get("AlertsCount") or 0
            existing_alerts_count = len(existing_record.get("alerts", {}))

            if (
                existing_alerts_count >= kql_alerts_count
                and set(kql_hashes).issubset(set(existing_hashes))
                and kql_alerts_count > 0
            ):
                self.logger.info(
                    f"Skipping incident {alert.name} ({incident_number}) "
                    f"based on KQL pre-filter. "
                    f"Existing alerts: {existing_alerts_count}, "
                    f"KQL alerts: {kql_alerts_count}. "
                    f"All {len(kql_hashes)} hashes matched."
                )
                return True
        return False

    def _get_existing_record(self, incident_name: str) -> SingleJson:
        """Get the cached existing record of an alert.

        Args:
            incident_name (str): The name/id of the incident/alert.

        Returns:
            SingleJson: The cached seen alert record, or empty dict if not found.
        """
        return (
            self.context.existing_ids.get(incident_name)
            or self.context.existing_ids.get(f"{incident_name}_0")
            or {}
        )

    def _sort_alerts(
        self,
        alerts: list[Incident],
    ) -> list[Incident]:
        """Sort alerts by last modified timestamp in ascending order."""
        return sorted(
            alerts,
            key=lambda alert: alert.last_modified_time_ts,
        )

    def _mark_incident_as_failed_filter(self, alert: Incident) -> None:
        """Mark the incident as failed filters inside context state cache."""
        self.context.existing_ids[alert.name] = {
            "status": "failed_filter",
            "last_modified": alert.properties.last_modified_time_utc,
            "alerts": {},
            "ingested_time": self.connector_start_time,
        }
        self.context.existing_ids_changed = True

    def _is_duplicate_or_seen(self, alert: Incident) -> bool:
        """Check if the incident has already been fully processed.

        Args:
            alert: The incident object to check.

        Returns:
            True if duplicate or already fully processed, otherwise False.

        """
        existing_record = self._get_existing_record(alert.name)
        if not existing_record:
            return False

        if existing_record.get("status") == "failed_filter":
            return (
                existing_record.get("last_modified")
                == alert.properties.last_modified_time_utc
            )

        return (
            existing_record.get("ingested_time")
            == alert.last_modified_time_ts
        )

    def _log_incident_event_count(self, alert: Incident, event_count: int) -> None:
        """Log event count for the incident."""
        prefix = "[Backlog] " if getattr(alert, "is_from_backlog", False) else ""
        self.logger.info(
            f"{prefix}Incident {alert.name} has total {event_count} events."
        )

    def _log_incident_slicing(self, alert: Incident, chunk_count: int) -> None:
        """Log that the incident is being sliced."""
        prefix = "[Backlog] " if getattr(alert, "is_from_backlog", False) else ""
        self.logger.info(
            f"{prefix}Incident {alert.name} exceeds the limit of "
            f"{constants.TRACKING_EVENTS_CHUNK_SIZE} events. "
            f"Slicing it into {chunk_count} separate SOAR alerts."
        )

    def _chunk_events(
        self,
        events: list[SingleJson],
    ) -> list[list[SingleJson]]:
        """Split list of events into sublist chunks."""
        chunk_size = constants.TRACKING_EVENTS_CHUNK_SIZE

        return [
            events[index : index + chunk_size]
            for index in range(0, len(events), chunk_size)
        ]

    def _build_sliced_alert(
        self,
        alert: Incident,
        chunk: list[SingleJson],
        index: int,
    ) -> Incident:
        """Create a new sliced Alert segment record by cloning base incident
        and modifying metadata.

        Args:
            alert (Incident): Incident data model.
            chunk (list[SingleJson]): List of events to be included
            in the sliced alert.
            index (int): Index of the current chunk.

        Returns:
            Incident: Sliced alert.
        """
        sliced_alert = copy.deepcopy(alert)

        sliced_alert.events_slice = chunk

        if sliced_alert.properties.additional_data is None:
            sliced_alert.properties.additional_data = {}

        sliced_alert.properties.additional_data["events_slice"] = (
            json.dumps(chunk)
        )

        sliced_alert.original_name = alert.name
        sliced_alert.name = f"{alert.name}_{index}"

        return sliced_alert

    def _slice_events_into_alerts(
        self,
        alerts: list[Incident],
    ) -> list[Incident]:
        """Slice large incidents into multiple alerts based on event chunk limits.

        Args:
            alerts: The input list of incidents.

        Returns:
            The final processed list of incidents (with slices if needed).
        """
        sliced_alerts = []

        for alert in alerts:
            all_events = self._build_events_data(
                incident=alert,
                flat_incident=alert.raw_to_flat_data(),
            )

            self._log_incident_event_count(alert, len(all_events))

            if (
                len(all_events)
                <= constants.TRACKING_EVENTS_CHUNK_SIZE
            ):
                sliced_alerts.append(alert)
                continue

            event_chunks = self._chunk_events(all_events)

            self._log_incident_slicing(alert, len(event_chunks))

            sliced_alerts.extend(
                self._build_sliced_alert(alert, chunk, index)
                for index, chunk in enumerate(event_chunks)
            )

        return sliced_alerts

    def _filters_are_active(self) -> bool:
        """Check if whitelist or tag ingestion filters are active."""
        return bool(self.siemplify.whitelist) or bool(
            self.params.incidents_tags_to_ingest
        )

    def _validate_ingestion_filters(self, alert: Incident) -> bool:
        """Validate ingestion dynamic list and tag filters, updating cache on failures.

        Args:
            alert: Incident data model to evaluate.

        Returns:
            bool: True if passes validation filters, False if failed (and marked failed).
        """
        if not self._filters_are_active():
            return True

        incident_number = str(alert.properties.incident_number)
        passed_filters = (
            self._pass_dynamic_list_filter_and_adjust_backlog(
                alert,
                incident_number,
            )
            and self._pass_tags_filter_and_adjust_backlog(
                alert,
                incident_number,
            )
        )

        if not passed_filters:
            prefix = "[Backlog] " if getattr(alert, "is_from_backlog", False) else ""
            self.logger.info(
                f"{prefix}Incident {alert.name} ({incident_number}) "
                f"failed dynamic list or tags filter. Skipping."
            )
            self._mark_incident_as_failed_filter(alert)
            return False

        prefix = "[Backlog] " if getattr(alert, "is_from_backlog", False) else ""
        self.logger.info(
            f"{prefix}Incident {alert.name} ({incident_number}) "
            f"passed dynamic list and tags filters."
        )
        return True

    def _should_skip_incident(
        self,
        alert: Incident,
        incident_number: str,
        kql_lookup: KqlLookup,
    ) -> bool:
        """Check if an incident should be skipped based on pre-filters, deduplication, or ingestion filters.

        Args:
            alert: The incident object to check.
            incident_number: The incident number as a string.
            kql_lookup: The lookup dictionary of pre-filtering stats.

        Returns:
            True if the incident should be skipped, otherwise False.
        """
        if self._should_skip_via_kql_filter(alert, incident_number, kql_lookup):
            return True

        if self._is_duplicate_or_seen(alert):
            return True

        if not self._validate_ingestion_filters(alert):
            return True

        return False

    async def _process_fetched_incident(
        self,
        alert: Incident,
        kql_lookup: KqlLookup,
    ) -> Incident | None:
        """Process a single fetched incident, applying filters and fetching events.

        Args:
            alert: The incident object to process.
            kql_lookup: The lookup dictionary of pre-filtering stats.

        Returns:
            The processed Incident if it passes all filters, otherwise None.
        """
        incident_number = str(alert.properties.incident_number)

        # Cache pre-filtering hashes onto Incident for state context storage
        kql_record = kql_lookup.get(alert.name)
        if kql_record:
            alert.alert_content_hashes = json.loads(
                kql_record.get("AlertContentHashes") or "[]"
            )

        if self._should_skip_incident(alert, incident_number, kql_lookup):
            return None

        await self._fetch_events_if_needed(alert)
        return alert

    async def get_alerts(self) -> list[Incident]:
        """Fetch new incidents from Azure Sentinel.

        Returns:
            List of Incident data models.

        """
        start_dt = datetime.datetime.fromtimestamp(
            self.connector_start_time / 1000.0, tz=datetime.timezone.utc
        )
        self.logger.info(
            f"Connector execution start time: "
            f"{start_dt.strftime('%Y-%m-%d %H:%M:%S UTC')} "
            f"(Unix: {self.connector_start_time})"
        )

        fetched_backlog_incidents = await self._get_backlog_incidents()
        self.logger.info(
            f"Fetched {len(fetched_backlog_incidents)} backlog incidents."
        )

        valid_new_incidents = []
        limit_to_process = self.params.max_incidents_per_cycle
        fetch_limit = constants.INCIDENTS_FETCH_LIMIT

        creation_time = None
        if self.params.incident_creation_time_filter_days:
            creation_time = utc_now() - datetime.timedelta(
                days=self.params.incident_creation_time_filter_days
            )
            self.logger.info(
                f"Filtering incidents created after {creation_time}"
            )

        kql_lookup = await self._prefilter_incidents_via_kql(creation_time)

        filtered_incidents_lookup = set(self.context.expired_existing_ids)
        filtered_incidents_lookup.update(
            incident.name for incident in fetched_backlog_incidents
        )

        while len(valid_new_incidents) < limit_to_process:
            try:
                (
                    fetched_incidents,
                    self.context.next_page_link,
                ) = await self.manager.get_incidents_with_new_endpoint(
                    updated_time=self.context.last_success_timestamp,
                    creation_time=creation_time,
                    statuses=self.params.incident_statuses_to_fetch,
                    severities=self.params.incident_severities_to_fetch,
                    limit=fetch_limit,
                    existing_ids=filtered_incidents_lookup,
                    next_page_link=self.context.next_page_link,
                )
            except MicrosoftAzureSentinelError:
                self.context.next_page_link = ""
                raise

            self.logger.info(
                f"Number of fetched incidents in this batch: "
                f"{len(fetched_incidents)}"
            )

            if not fetched_incidents:
                break

            for alert in fetched_incidents:
                processed_alert = await self._process_fetched_incident(
                    alert, kql_lookup
                )
                if processed_alert:
                    valid_new_incidents.append(processed_alert)
                    if len(valid_new_incidents) >= limit_to_process:
                        break

            if len(valid_new_incidents) >= limit_to_process:
                break

            if not self.context.next_page_link:
                break

        self.logger.info(
            f"Total valid new incidents found in this cycle: "
            f"{len(valid_new_incidents)}"
        )

        all_alerts = valid_new_incidents + fetched_backlog_incidents
        return self._slice_events_into_alerts(all_alerts)

    def _should_skip_backlog_incident(self, alert: Incident) -> bool:
        """Check if a backlog incident should be skipped.

        A backlog incident is skipped if:
        1. It previously failed the filters and hasn't been updated since.
        2. It currently fails the dynamic list or tags ingestion filters.

        Args:
            alert: The backlog incident.

        Returns:
            True if it should be skipped, otherwise False.
        """
        existing_record = self._get_existing_record(alert.name)
        if (
            existing_record
            and existing_record.get("status") == "failed_filter"
            and existing_record.get("last_modified")
            == alert.properties.last_modified_time_utc
        ):
            return True

        if not self._validate_ingestion_filters(alert):
            return True

        return False

    def filter_alerts(self, alerts: list[Incident]) -> list[Incident]:
        """Filter fetched incidents.

        Filter fetched incidents to exclude already fetched and those failing
        title/tags filters.

        Args:
            alerts: List of Incident data models

        Returns:
            List of filtered Incident data models sorted by last_modified_time_ts
        """
        valid_alerts = []
        for alert in alerts:
            if getattr(
                alert, "is_from_backlog", False
            ) and self._should_skip_backlog_incident(alert):
                continue
            valid_alerts.append(alert)

        new_alerts = [
            a for a in valid_alerts if not getattr(a, "is_from_backlog", False)
        ]
        backlog_alerts = [
            a for a in valid_alerts if getattr(a, "is_from_backlog", False)
        ]

        return (
            self._sort_alerts(new_alerts)
            + self._sort_alerts(backlog_alerts)
        )

    async def process_alert(self, alert: Incident) -> Incident:
        """Process alert coroutine."""
        self.logger.info(
            f"Processing incident {alert.alert_id} "
            f"with timestamps: {alert.last_modified_time_ts}"
        )

        alert = await self.manager.adjust_incidents_alerts_data(
            incident=alert,
            connector_starting_time=self.connector_start_time,
            python_process_timeout=self.params.python_process_timeout,
            scheduled_alerts_events_limit=(
                self.params.scheduled_alerts_events_limit_to_ingest
            ),
            scheduled_alerts_new_events_limit=(
                (
                    self.params.scheduled_alerts_events_limit_to_ingest
                    - self._calculate_existing_scheduled_alerts_events(alert)
                )
                if self.params.scheduled_alerts_events_limit_to_ingest
                else None
            ),
            incidents_alerts_limit_to_ingest=None,
            backlog_ids=self.context.backlog_ids,
            alerts_for_no_entities=self.params.alerts_for_no_entities,
            use_same_approach=self.params.use_same_approach,
            incident_existing_items=(self.context.existing_ids.get(alert.name, {})),
            wait_for_scheduled_alerts=self.params.wait_for_scheduled_alerts,
        )
        return alert

    async def process_alerts(
        self, filtered_alerts: list[Incident], *args, **kwargs
    ) -> tuple[list[AlertInfo], list[Incident]]:
        """Override process_alerts to process new incidents first, then backlog ones."""
        new_alerts = [
            a for a in filtered_alerts if not getattr(a, "is_from_backlog", False)
        ]
        backlog_alerts = [
            a for a in filtered_alerts if getattr(a, "is_from_backlog", False)
        ]

        processed_alerts = []
        unprocessed_alerts = []

        if new_alerts:
            self.logger.info(f"Processing {len(new_alerts)} new alerts first...")
            proc, unproc = await super().process_alerts(new_alerts, *args, **kwargs)
            processed_alerts.extend(proc)
            unprocessed_alerts.extend(unproc)

        if backlog_alerts:
            self.logger.info(f"Processing {len(backlog_alerts)} backlog alerts next...")
            proc, unproc = await super().process_alerts(backlog_alerts, *args, **kwargs)
            processed_alerts.extend(proc)
            unprocessed_alerts.extend(unproc)

        return processed_alerts, unprocessed_alerts

    def pass_filters(self, alert: Incident) -> bool:
        """Check if incident passes filters and is fully fetched.

        Args:
            alert (Incident): Incident data model

        Returns:
            bool: True if passes filter, False otherwise
        """
        _incident_number = str(alert.properties.incident_number)

        all_seen, incomplete_alerts = self._already_seen_items(alert)
        if all_seen:
            self.logger.info(
                f"Alert {alert.name} ({_incident_number}) with all related items "
                f"has already been seen. Skipping..."
            )
            return False

        return self._pass_backlog_filter_and_adjust_backlog(
            alert,
            _incident_number,
            incomplete_alerts
        )

    def _pass_dynamic_list_filter_and_adjust_backlog(
        self, alert: Incident, incident_number: str
    ) -> bool:
        """
        Check if incident passes dynamic list filter and adjust backlog based on filter

        Args:
            alert (Incident): Incident data model
            incident_number (str): Incident number

        Returns:
            bool: True if passes dynamic list filter, False otherwise
        """
        if self.siemplify.whitelist and not pass_whitelist_filter(
            siemplify=self.siemplify,
            whitelist_as_a_blacklist=self.params.use_dynamic_list_as_a_blocklist,
            model=alert,
            model_key="incident_title",
        ):
            if incident_number in self.context.backlog_ids:
                self.logger.info(
                    f"Backlog alert {alert.name} ({incident_number}) "
                    "is blacklisted, removing from backlog ..."
                )
                del self.context.backlog_ids[incident_number]

            return False

        return True

    def _pass_tags_filter_and_adjust_backlog(
        self, alert: Incident, incident_number: str
    ) -> bool:
        """
        Check if incident passes tags filter and adjust backlog based on filter

        Args:
            alert (Incident): Incident data model
            incident_number (str): Incident number

        Returns:
            bool: True if passes tags filter, False otherwise
        """
        if self.params.incidents_tags_to_ingest:
            alert.incident_labels_lower = [
                label.lower() for label in alert.incident_labels or []
            ]
            whitelist = [tag.lower() for tag in self.params.incidents_tags_to_ingest]
            if not any(tag in whitelist for tag in alert.incident_labels_lower):
                if incident_number in self.context.backlog_ids:
                    self.logger.info(
                        f"Backlog alert {alert.name} ({incident_number}) "
                        "is blacklisted by tags, removing from backlog ..."
                    )
                    del self.context.backlog_ids[incident_number]

                return False

        return True

    def _update_backlog_entry(
        self,
        incident_number: str,
        incomplete_alerts: list[IncidentAlert],
        backlog_exp_time: int,
    ) -> None:
        """Update or add incomplete alerts to the backlog entry.

        Args:
            incident_number: The incident number as a string.
            incomplete_alerts: The list of incomplete alert objects.
            backlog_exp_time: The calculated expiration timestamp.

        """
        backlog_entry = self.context.backlog_ids.get(incident_number, {})
        if not isinstance(backlog_entry, dict):
            backlog_entry = {}

        for alert in incomplete_alerts:
            aid = alert.properties.system_alert_id
            if aid not in backlog_entry:
                backlog_entry[aid] = {
                    "backlog_expiration_time": backlog_exp_time
                }

        self.context.backlog_ids[incident_number] = backlog_entry
        self.context.backlog_changed = True

        # Move to the end of the dict for round-robin pagination
        val = self.context.backlog_ids.pop(incident_number)
        self.context.backlog_ids[incident_number] = val

    def _pass_backlog_filter_and_adjust_backlog(
        self,
        alert: Incident,
        incident_number: str,
        incomplete_alerts: list[IncidentAlert],
    ) -> bool:
        """
        Check if incident passes backlog filter and adjust backlog based on filter

        Args:
            alert (Incident): Incident data model.
            incident_number (str): Incident number.
            incomplete_alerts (list[IncidentAlert]): List of incomplete alerts.

        Returns:
            bool: True if passes backlog filter, False otherwise
        """
        has_incomplete = len(incomplete_alerts) > 0

        if not has_incomplete:
            if incident_number in self.context.backlog_ids:
                self.logger.info(
                    f"Backlog incident {alert.name} ({incident_number}) "
                    f"is now fully complete."
                )
                del self.context.backlog_ids[incident_number]
                self.context.backlog_changed = True
            return True

        backlog_exp_time = self.connector_start_time + (
            self.params.backlog_expiration_timer
            * NUM_OF_SEC_IN_MIN
            * NUM_OF_MILLI_IN_SEC
        )

        if incident_number not in self.context.backlog_ids:
            reason = self._get_backlog_reason(alert)
            self.logger.info(
                f"Sending incident {alert.name} ({incident_number}) "
                f"to backlog. Reason: {reason}"
            )

            backlog_entry = {}
            for a in incomplete_alerts:
                backlog_entry[a.properties.system_alert_id] = {
                    "backlog_expiration_time": backlog_exp_time
                }

            self.context.backlog_ids[incident_number] = backlog_entry
            self.context.backlog_changed = True
        else:
            self.logger.info(
                f"Incident {alert.name} ({incident_number}) "
                f"has incomplete alerts and will stay in backlog."
            )
            self._update_backlog_entry(
                incident_number,
                incomplete_alerts,
                backlog_exp_time
            )

        if alert.properties.alerts:
            self.logger.info(
                f"Ingesting {len(alert.properties.alerts)} complete alerts "
                f"for incident {alert.name} ({incident_number}) "
                f"while tracking incomplete ones in backlog."
            )
            return True

        if self._is_backlog_incident_expired(incident_number):
            self.logger.warn(
                f"Expired backlog incident {alert.name} "
                f"({incident_number}) will be processed with available data."
            )
            if incident_number in self.context.backlog_ids:
                del self.context.backlog_ids[incident_number]
                self.context.backlog_changed = True
            return True

        return False

    def _get_backlog_reason(self, alert: Incident) -> str:
        """Get the reason why an incident is not fully fetched.

        Args:
            alert (Incident): Incident data model.

        Returns:
            str: Semicolon-separated string of reasons.
        """
        if not alert.properties.alerts:
            return "No alerts found or fetched for this incident"

        reasons = []
        for a in alert.properties.alerts:
            if a.fully_fetched:
                continue

            r = f"Alert {a.properties.system_alert_id} incomplete"

            is_scheduled = a.is_scheduled_or_nrt()
            sched_alert = a.scheduled_alert

            if is_scheduled:
                if not sched_alert:
                    r += " (Waiting for Scheduled Alert data)"
                elif not sched_alert.events:
                    r += " (No events fetched)"
            elif a.entities is None:
                r += " (Failed to fetch entities)"
            elif not a.entities and not self.params.alerts_for_no_entities:
                r += " (No entities found and Alerts For No Entities is disabled)"

            reasons.append(r)

        if reasons:
            return "; ".join(reasons)

        return (
            "Incident marked incomplete by manager (likely due to "
            "timeouts or all alerts being already processed)"
        )

    def _set_time_for_alert(
        self, alert_info: AlertInfo, incident: Incident, flat_incident: dict[str, str]
    ) -> None:
        """Try setting start and end time using fallbacks and log the process.

        Args:
            alert_info: AlertInfo object of SOAR alert
            incident: Incident data model
            flat_incident: Flat incident data to use for fallbacks fetch

        Returns:
            None, update alert_info on the spot

        """
        alert_info.start_time = self._get_alert_time_value(
            incident=incident,
            flat_incident=flat_incident,
            fallback_keys=self.params.start_time_fallback,
            fallback_logic_debug_key="StartTimeFallback",
            alert_time_key_name="start time",
        )

        alert_info.end_time = self._get_alert_time_value(
            incident=incident,
            flat_incident=flat_incident,
            fallback_keys=self.params.end_time_fallback,
            fallback_logic_debug_key="EndTimeFallback",
            alert_time_key_name="end time",
        )

    def _get_alert_time_value(
        self,
        incident: Incident,
        flat_incident: dict[str, str],
        fallback_keys: [str],
        fallback_logic_debug_key: str,
        alert_time_key_name: str,
    ) -> int:
        """Get alert time value.

        Args:
            incident (Incident): Incident data model.
            flat_incident (dict[str, str]): flat incident data.
            fallback_keys ([str]): list of keys to use for value extraction.
            fallback_logic_debug_key (str): key to set for fallback logic debug.
            alert_time_key_name (str): alert time key name.

        Returns:
            int: alert time value in unix format.

        """
        fallback = (
            self._get_fallback_value(
                flat_incident, fallback_keys, fallback_logic_debug_key
            )
            or incident.properties.created_time_utc
        )

        if fallback:
            alert_time = convert_string_to_unix_time(fallback)
            if self.params.fallback_logic_debug and not flat_incident.get(
                fallback_logic_debug_key
            ):
                flat_incident[fallback_logic_debug_key] = "CreatedTimeUTC"
        else:
            alert_time = unix_now()
            self.logger.info(
                f"Chronicle SOAR Alert's {alert_time_key_name} is set to current time,"
                f" as no values were found with the provided fallback fields."
            )
            if self.params.fallback_logic_debug:
                flat_incident[fallback_logic_debug_key] = "Current time"

        return alert_time

    def _set_product_and_vendor_for_alert(
        self, alert_info: AlertInfo, incident: Incident, flat_incident: dict[str, str]
    ) -> None:
        """Try setting Vendor and Product using fallbacks and log the process.

        Args:
            alert_info: AlertInfo object of SOAR alert
            incident: Incident data model
            flat_incident: Flat incident data to use for fallbacks fetch

        Returns:
            None, update alert_info on the spot

        """
        product_value = self._get_fallback_value(
            flat_incident, self.params.product_field_fallback, "ProductFieldFallback"
        )

        vendor_value = self._get_fallback_value(
            flat_incident, self.params.vendor_field_fallback, "VendorFieldFallback"
        )

        if incident.properties.alerts:
            source_alert: IncidentAlert = incident.properties.alerts[0]
            vendor_value = (
                source_alert.scheduled_alert.vendor_name
                if source_alert.scheduled_alert is not None
                else source_alert.properties.vendor_name
            )
            flat_events = (
                source_alert.scheduled_alert.get_events_flat()
                if source_alert.scheduled_alert is not None
                else []
            )
            source_event_flat = flat_events[0] if flat_events else {}

            product_value, _ = find_fallback_value(
                source_dicts=[
                    source_event_flat,
                    dict_to_flat(source_alert.to_event()),
                    flat_incident,
                ],
                fallbacks_list=self.params.product_field_fallback,
            )

        alert_info.device_vendor = (
            vendor_value if vendor_value else constants.DEFAULT_VENDOR_NAME
        )
        alert_info.device_product = (
            product_value if product_value else constants.DEFAULT_PRODUCT_NAME
        )

    def _get_fallback_value(
        self, data: dict, fallback_keys: [str], fallback_logic_debug_key: str
    ) -> str | None:
        """
        Get fallback value from provided data
        Args:
            data (dict): data to extract fallback value from
            fallback_keys ([str]): list of keys to use for value extraction
            fallback_logic_debug_key (str): key to set for fallback logic debug

        Returns:
            str | None: fallback value or None
        """
        fallback_value = None

        for fallback_key in fallback_keys:
            fallback_value = data.get(fallback_key)
            if fallback_value:
                if self.params.fallback_logic_debug:
                    data[fallback_logic_debug_key] = fallback_key
                break

        return fallback_value

    def _build_events_data(
        self, incident: Incident, flat_incident: dict[str, str]
    ) -> list[dict[str, str]]:
        """Build events data out of alerts for incident and return their flat data.

        Args:
            incident (Incident): Incident data model
            flat_incident (dict[str, str]): Flattened incident data

        Returns:
            list[dict[str, str]]: List of flattened event dicts
        """
        if not incident.properties.alerts:
            flat_incident["kind"] = constants.INCIDENT_EVENT_KIND
            return [flat_incident]

        events = []

        for incident_alert in incident.properties.alerts:
            start_time = (
                incident_alert.properties.start_time_utc
                if incident_alert.properties
                else None
            )
            self.logger.info(
                f"Processing Sentinel Alert: {incident_alert.name} "
                f"(StartTimeUtc: {start_time})"
            )
            if (
                incident_alert.is_scheduled_or_nrt()
                and not self.params.use_same_approach
            ):
                if not incident_alert.scheduled_alert:
                    self.logger.info(
                        f"Incident alert {incident_alert.id} is scheduled "
                        f"but has no scheduled alerts data fetched. "
                        f"Incident alert data will be used instead."
                    )
                    alert_event = incident_alert.to_event()
                    alert_event["sentinel_alert_id"] = incident_alert.name
                    events.append(alert_event)

                    regular_events = create_regular_alert_events(
                        flat_incident,
                        incident_alert,
                        self.params.create_extra_events_for_all_entities,
                        self.params.product_field_fallback,
                        self.params.fallback_logic_debug,
                    )
                    for ev in regular_events:
                        ev["sentinel_alert_id"] = incident_alert.name
                    events.extend(regular_events)
                    continue

                scheduled_events = create_scheduled_alert_events(
                    flat_incident,
                    incident_alert,
                    self.params.create_extra_events_for_all_entities,
                    self.params.product_field_fallback,
                    self.params.fallback_logic_debug,
                )
                for ev in scheduled_events:
                    ev["sentinel_alert_id"] = incident_alert.name
                events.extend(scheduled_events)

            else:
                # Use the alert itself as the event
                alert_event = incident_alert.to_event()
                alert_event["sentinel_alert_id"] = incident_alert.name
                events.append(alert_event)

                regular_events = create_regular_alert_events(
                    flat_incident,
                    incident_alert,
                    self.params.create_extra_events_for_all_entities,
                    self.params.product_field_fallback,
                    self.params.fallback_logic_debug,
                )
                for ev in regular_events:
                    ev["sentinel_alert_id"] = incident_alert.name
                events.extend(regular_events)

        return events

    def _adjust_events_data(self, alert_info: AlertInfo, incident: Incident) -> None:
        """Adjust events data with all additional fields.

        Args:
            alert_info: SOAR alert data model
            incident: Incident data model

        Returns:
            None, update alert_info.events dicts on the spot

        """
        for event in alert_info.events:
            event["properties_title"] = incident.properties.title
            event["properties_incidentNumber"] = incident.properties.incident_number
            event["properties_incidentUrl"] = incident.properties.incident_url
            event["alert_type"] = incident.type
            event["event_type"] = self._get_fallback_value(
                data=event,
                fallback_keys=self.params.event_field_fallback,
                fallback_logic_debug_key="EventFieldFallback",
            )

            event["Siemplify_Start_Time"] = event["SecOps_Start_Time"] = (
                self._get_event_time_value(
                    incident=incident,
                    event=event,
                    fallback_keys=self.params.start_time_fallback,
                    fallback_logic_debug_key="StartTimeFallback",
                )
            )

            event["Siemplify_End_Time"] = event["SecOps_End_Time"] = (
                self._get_event_time_value(
                    incident=incident,
                    event=event,
                    fallback_keys=self.params.end_time_fallback,
                    fallback_logic_debug_key="EndTimeFallback",
                )
            )

    def _get_event_time_value(
        self,
        incident: Incident,
        event: dict,
        fallback_keys: [str],
        fallback_logic_debug_key: str,
    ) -> str:
        """
        Get event time value
        Args:
            incident (Incident): Incident data model
            event (dict): event data
            fallback_keys ([str]): list of keys to use for value extraction
            fallback_logic_debug_key (str): key to set for fallback logic debug

        Returns:
            str: event time value
        """
        value = (
            self._get_fallback_value(
                data=event,
                fallback_keys=fallback_keys,
                fallback_logic_debug_key=fallback_logic_debug_key,
            )
            or incident.properties.created_time_utc
        )

        if value:
            alert_time = value
            if (
                self.params.fallback_logic_debug
                and fallback_logic_debug_key not in event
            ):
                event[fallback_logic_debug_key] = "CreatedTimeUTC"
        else:
            alert_time = utc_now().isoformat()
            if self.params.fallback_logic_debug:
                event[fallback_logic_debug_key] = "Current time"

        return alert_time

    def create_alert_info(self, incident: Incident) -> AlertInfo:
        """Create AlertInfo object out of and Incident data model.

        Args:
            incident: Incident data model

        Returns:
            AlertInfo object
        """
        flat_incident = incident.raw_to_flat_data()
        alert_info = AlertInfo()

        alert_info.display_id = f"{incident.name}_{uuid.uuid4()}"
        alert_info.ticket_id = getattr(incident, "original_name", incident.name)
        alert_info.name = get_value_from_template(
            template=self.params.alert_name_template,
            data=flat_incident,
            default_value=incident.properties.title,
        )
        alert_info.rule_generator = get_value_from_template(
            template=self.params.rule_generator_template,
            data=flat_incident,
            default_value=incident.properties.title,
        )
        alert_info.source_grouping_identifier = getattr(
            incident,
            "original_name",
            incident.name
        )
        alert_info.description = incident.properties.description
        alert_info.priority = MicrosoftAzureSentinelParser.calculate_priority(
            incident.properties.severity
        )

        self._set_time_for_alert(
            alert_info=alert_info, incident=incident, flat_incident=flat_incident
        )

        self._set_product_and_vendor_for_alert(
            alert_info=alert_info, incident=incident, flat_incident=flat_incident
        )

        alert_info.extensions = create_extensions(incident.properties)

        if hasattr(incident, "events_slice"):
            alert_info.events = incident.events_slice
        elif (
            incident.properties.additional_data
            and "events_slice" in incident.properties.additional_data
        ):
            alert_info.events = json.loads(
                incident.properties.additional_data["events_slice"]
            )
        else:
            alert_info.events = self._build_events_data(
                incident=incident, flat_incident=flat_incident
            )
        alert_info.environment = self.env_common.get_environment(flat_incident)

        self._adjust_events_data(alert_info=alert_info, incident=incident)
        return alert_info

    def _collect_seen_ids(
        self, incident: Incident, existing_ids: dict[str, dict]
    ) -> dict[str, dict]:
        """
        Collect seen ids based on already existing_ids and additional ids from incident

        Args:
            incident (Incident): Incident object which contains additional ids
            existing_ids (dict[str, dict]): Dictionary representing the current seen ids
            The structure of this dictionary is as follows:
                {
                    "<incident_id>": {
                        "ingested_time": <timestamp>,
                        "alerts": {
                            "<alert_1_id>": {
                                "events": [<event_1_hash>, ...],
                                "entities": [<entity_1_id>, ...]
                            }
                        }
                    }
                }

        Returns:
            dict[str, dict]: Dictionary containing collected seen IDs.
            The structure of the returned dictionary is the same as the `existing_ids`
            with additional entries added based on the Incident object.

        Example:
            {
                "<incident_id>": {
                    "ingested_time": <timestamp>,
                    "alerts": {
                        "<alert_1_id>": {
                            "events": [<event_1_hash>, <event_2_hash>],
                            "entities": [<entity_1_id>]
                        },
                        "<alert_2_id>": {
                            "events": [<event_3_hash>],
                            "entities": [<entity_2_id>, <entity_3_id>]
                        }
                    }
                }
            }
        """
        existing_ids = existing_ids or {}

        return {
            "ingested_time": (
                existing_ids.get("ingested_time")
                if "alerts" in existing_ids
                else incident.last_modified_time_ts
            ),
            "entity_hashes": list(
                set(
                    existing_ids.get("entity_hashes", [])
                    + getattr(incident, "alert_content_hashes", [])
                )
            ),
            "alerts": {
                **existing_ids.get("alerts", {}),
                **{
                    alert.name: {
                        "events": collect_seen_events_hashes(alert, existing_ids),
                        "entities": collect_seen_entities_ids(alert, existing_ids),
                    }
                    for alert in incident.incident_alerts
                },
            },
        }

    def _already_seen_items(
        self,
        incident: Incident
    ) -> tuple[bool, list[IncidentAlert]]:
        """
        Check if incident and all related items are already seen
        Args:
            incident (Incident): Incident object

        Returns:
            tuple[bool, list[IncidentAlert]]: (all_seen, incomplete_alerts)
        """
        if incident.name not in self.context.existing_ids.keys():
            pass

        all_seen = True
        complete_new_alerts = []
        incomplete_new_alerts = []

        incident_number = str(incident.properties.incident_number)

        existing_record = (
            self.context.existing_ids.get(incident.name)
            or self.context.existing_ids.get(f"{incident.name}_0")
            or {}
        )

        for alert in incident.incident_alerts:
            is_new = False
            if alert.name not in existing_record.get("alerts", {}).keys():
                is_new = True
            else:
                alert_ids = existing_record.get("alerts", {}).get(alert.name)

                new_events = [
                    event
                    for event in (
                        (alert.scheduled_alert and alert.scheduled_alert.events) or []
                    )
                    if dict_to_md5_hash(event) not in alert_ids.get("events", [])
                ]
                new_entities = [
                    entity
                    for entity in (alert.entities or [])
                    if entity.name not in alert_ids.get("entities", [])
                ]

                if new_events or new_entities:
                    is_new = True
                    if alert.scheduled_alert:
                        alert.scheduled_alert.events = new_events
                    alert.entities = new_entities

            if is_new:
                all_seen = False
                is_alert_expired = self._is_backlog_alert_expired(
                    incident_number,
                    alert.properties.system_alert_id
                )

                if alert.fully_fetched or is_alert_expired:
                    complete_new_alerts.append(alert)
                else:
                    incomplete_new_alerts.append(alert)

        incident.properties.alerts = complete_new_alerts
        return all_seen, incomplete_new_alerts

    async def _fetch_events_if_needed(self, alert: Incident) -> None:
        """Fetch alerts and events for scheduled alerts if not already fetched."""
        if not alert.properties.alerts:
            self.logger.info(f"Fetching alerts for incident {alert.name}.")
            alert.properties.alerts = await self.manager.get_incident_alerts_by_id(
                alert.name,
                alerts_limit=None
            )

        if not self.params.use_same_approach:
            _scheduled_alerts = [
                a for a in alert.properties.alerts if a.is_scheduled_or_nrt()
            ]
            if _scheduled_alerts:
                await self.manager.fetch_scheduled_alerts(
                    incident_alerts=_scheduled_alerts,
                    incident=alert,
                    connector_starting_time=self.connector_start_time,
                    python_process_timeout=self.params.python_process_timeout,
                    scheduled_alerts_events_limit=(
                        max(
                            constants.DEFAULT_SCHEDULED_ALERTS_EVENTS_LIMIT,
                            self.params.scheduled_alerts_events_limit_to_ingest,
                        )
                        if self.params.scheduled_alerts_events_limit_to_ingest
                        else constants.DEFAULT_SCHEDULED_ALERTS_EVENTS_LIMIT
                    ),
                    scheduled_alerts_new_events_limit=(
                        (
                            max(
                                constants.DEFAULT_SCHEDULED_ALERTS_EVENTS_LIMIT,
                                self.params.scheduled_alerts_events_limit_to_ingest,
                            )
                            - self._calculate_existing_scheduled_alerts_events(alert)
                        )
                        if self.params.scheduled_alerts_events_limit_to_ingest
                        else None
                    ),
                    incident_existing_items=self.context.existing_ids.get(alert.name, {}),
                )
                for a in _scheduled_alerts:
                    a.events_fetched = True

    def _calculate_existing_scheduled_alerts_events(self, incident):
        """
        Calculate existing scheduled alerts events amount
        Args:
            incident (Incident): Incident object

        Returns:
            int: Existing scheduled alerts events amount
        """
        total_events = []
        existing_alerts = self.context.existing_ids.get(incident.name, {}).get(
            "alerts", {}
        )

        for items in existing_alerts.values():
            total_events.extend(items.get("events", []))

        return len(total_events)

    def _is_backlog_alert_expired(self, incident_number: str, alert_id: str) -> bool:
        """
        Check if backlog alert is expired
        """
        alert_data = self.context.backlog_ids.get(incident_number, {}).get(alert_id, {})
        exp_time = alert_data.get("backlog_expiration_time", 0)
        if not exp_time:
            return False

        start_dt = datetime.datetime.fromtimestamp(
            self.connector_start_time / 1000.0,
            tz=datetime.timezone.utc
        )
        exp_dt = datetime.datetime.fromtimestamp(
            exp_time / 1000.0,
            tz=datetime.timezone.utc
        )
        is_expired = self.connector_start_time >= exp_time
        self.logger.info(
            f"[Backlog Expiration Check] Incident {incident_number}, "
            f"Alert {alert_id} -> "
            f"Connector Start Time: "
            f"{start_dt.strftime('%Y-%m-%d %H:%M:%S UTC')} "
            f"({self.connector_start_time}) vs "
            f"Backlog Expiration Time: "
            f"{exp_dt.strftime('%Y-%m-%d %H:%M:%S UTC')} "
            f"({exp_time}). "
            f"Expired?: {is_expired}"
        )

        return is_expired

    def _is_backlog_incident_expired(self, incident_number: str) -> bool:
        """
        Check if backlog incident is expired
        Args:
            incident_number (str): incident number

        Returns:
            bool: True if expired, False otherwise
        """
        if incident_number not in self.context.backlog_ids:
            return False

        backlog_exp_time = (
            self.params.backlog_expiration_timer
            * NUM_OF_SEC_IN_MIN
            * NUM_OF_MILLI_IN_SEC
        )
        backlog_entry = self.context.backlog_ids.get(incident_number, 0)

        if isinstance(backlog_entry, dict):
            for alert_data in backlog_entry.values():
                exp_time = alert_data.get("backlog_expiration_time", 0)
                if exp_time and self.connector_start_time >= exp_time:
                    return True
            return False

        return self.connector_start_time >= backlog_entry + backlog_exp_time


def create_extensions(incident_properties: IncidentProperties) -> dict[str, str]:
    """
    Create extensions for AlertInfo object
    Args:
        incident_properties (IncidentProperties): IncidentProperties object

    Returns:
        dict[str, str]: flat extensions dict
    """
    return dict_to_flat(
        {
            "status": incident_properties.status,
            "labels": [str(label) for label in incident_properties.labels],
            "endTimeUtc": incident_properties.end_time_utc,
            "startTimeUtc": incident_properties.start_time_utc,
            "owner": (
                incident_properties.owner.assigned_to
                if incident_properties.owner
                else None
            ),
            "lastModifiedTimeUtc": incident_properties.last_modified_time_utc,
            "createdTimeUtc": incident_properties.created_time_utc,
            "incidentNumber": incident_properties.incident_number,
            "incidentUri": incident_properties.incident_url,
            "Sentinel Alert ids": ",".join(
                [a.name for a in incident_properties.alerts] or []
            ),
            "additionalData": incident_properties.additional_data,
        }
    )


def collect_seen_events_hashes(
    alert: IncidentAlert, existing_ids: dict[str, dict]
) -> list[str]:
    """
    Collect seen events hashes based on existing_ids and events from alert

    Args:
        alert (IncidentAlert): IncidentAlert object which contains additional hashes
        existing_ids (dict[str, dict]): Dictionary representing the current seen ids
        The structure of this dictionary is as follows:
            {
                "<incident_id>": {
                    "ingested_time": <timestamp>,
                    "alerts": {
                        "<alert_1_id>": {
                            "events": [<event_1_hash>, ...],
                            "entities": [<entity_1_id>, ...]
                        }
                    }
                }
            }

    Returns:
        [str]: list of seen events hashes
    """
    existing_events_hashes = (
        existing_ids.get("alerts", {}).get(alert.name, {}).get("events", [])
    )
    new_events_hashes = (
        [dict_to_md5_hash(event) for event in alert.scheduled_alert.events]
        if alert.scheduled_alert and alert.scheduled_alert.events
        else []
    )

    return list(set(existing_events_hashes + new_events_hashes))


def collect_seen_entities_ids(
    alert: IncidentAlert, existing_ids: dict[str, dict]
) -> list[str]:
    """
    Collect seen entities ids based on existing_ids and entities from alert

    Args:
        alert (IncidentAlert): IncidentAlert object which contains additional ids
        existing_ids (dict[str, dict]): Dictionary representing the current seen ids
        The structure of this dictionary is as follows:
            {
                "<incident_id>": {
                    "ingested_time": <timestamp>,
                    "alerts": {
                        "<alert_1_id>": {
                            "events": [<event_1_hash>, ...],
                            "entities": [<entity_1_id>, ...]
                        }
                    }
                }
            }

    Returns:
        [str]: list of seen entities ids
    """
    existing_entities_ids = (
        existing_ids.get("alerts", {}).get(alert.name, {}).get("entities", [])
    )
    new_entities_ids = [entity.name for entity in (alert.entities or [])]

    return list(set(existing_entities_ids + new_entities_ids))


async def main() -> None:
    """main"""
    connector = IncidentTrackingConnector()
    await asyncio.ensure_future(connector.start())


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
