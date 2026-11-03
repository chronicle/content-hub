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
import datetime
from typing import Any
import sys

import httpx

from ..core.MicrosoftAzureSentinelManager import QueryFilterKeyEnum
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time, utc_now
from TIPCommon.extraction import extract_connector_param
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.filters import filter_old_alerts, pass_whitelist_filter
from TIPCommon.transformation import dict_to_flat
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.smp_time import unix_now
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_test_run
from TIPCommon.base.connector.async_connector import AsyncConnector
from ..core import constants
from ..core.datamodels import Incident, IncidentAlert
from ..core.exceptions import (
    MicrosoftAzureSentinelError,
    MicrosoftAzureSentinelManagerError,
    TimeoutIsApproachingError,
    MicrosoftAzureSentinelIncidentNotFoundError,
)
from ..core.MicrosoftAzureSentinelCommon import (
    MicrosoftAzureSentinelCommon,
    read_backlog_ids,
    read_next_page_alerts,
    write_backlog_ids,
    write_next_page_alerts,
    create_scheduled_alert_events,
    create_regular_alert_events,
)
from ..core.MicrosoftAzureSentinelAsyncManager import MicrosoftAzureSentinelAsyncManager
from ..core.MicrosoftAzureSentinelParser import MicrosoftAzureSentinelParser
from ..core.utils import get_value_from_template, find_fallback_value


def _incident_number_from_url(url: httpx.URL) -> str:
    return url.params[QueryFilterKeyEnum.FILTER.value].split(" ")[-1]


class IssuesConnector(AsyncConnector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.coros_limit = 10
        self.manager: MicrosoftAzureSentinelAsyncManager | None = None
        self.sentinel_common = MicrosoftAzureSentinelCommon(self.logger)

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
        self.params.incidents_alerts_limit_to_ingest = extract_connector_param(
            self.siemplify,
            param_name="Incident's Alerts Limit to Ingest",
            input_type=int,
            print_value=True,
            default_value=constants.DEFAULT_INCIDENTS_ALERTS_LIMIT_TO_INGEST,
        )
        self.params.azure_api_timeout_in_seconds = extract_connector_param(
            self.siemplify,
            param_name="Azure API Timeout In Seconds",
            input_type=int,
            print_value=True,
            default_value=constants.DEFAULT_HTTP_REQUEST_TIMEOUT_SECONDS,
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
        self.params.max_new_incidents_per_cycle = (
            self.param_validator.validate_positive(
                param_name="Max New Incidents Per Cycle",
                value=self.params.max_new_incidents_per_cycle,
            )
        )
        self.params.max_backlog_incidents_per_cycle = (
            self.param_validator.validate_positive(
                param_name="Max Backlog Incidents per cycle",
                value=self.params.max_backlog_incidents_per_cycle,
            )
        )
        self.params.offset_time_in_hours = self.param_validator.validate_positive(
            param_name="Offset Time In Hours", value=self.params.offset_time_in_hours
        )
        self.params.scheduled_alerts_events_limit_to_ingest = (
            self.param_validator.validate_positive(
                param_name="Scheduled Alerts Events Limit to Ingest",
                value=self.params.scheduled_alerts_events_limit_to_ingest,
            )
        )
        self.params.incidents_alerts_limit_to_ingest = (
            self.param_validator.validate_positive(
                param_name="Incident's Alerts Limit to Ingest",
                value=self.params.incidents_alerts_limit_to_ingest,
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
            param_name="StartTimeFallback",
            csv_string=self.params.start_time_fallback,
        )
        self.params.end_time_fallback = self.param_validator.validate_csv(
            param_name="EndTimeFallback",
            csv_string=self.params.end_time_fallback,
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
            param_name="EventFieldFallback",
            csv_string=self.params.event_field_fallback,
        )
        self.params.azure_api_timeout_in_seconds = (
            self.param_validator.validate_positive(
                param_name="Azure API Timeout In Seconds",
                value=self.params.azure_api_timeout_in_seconds,
            )
        )

    def init_managers(self) -> None:
        self.manager = MicrosoftAzureSentinelAsyncManager(
            http_timeout_seconds=self.params.azure_api_timeout_in_seconds,
            api_root=self.params.api_root,
            client_id=self.params.client_id,
            client_secret=self.params.client_secret,
            tenant_id=self.params.azure_active_directory_id,
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
            max_backwards_param_name="offset_time_in_hours",
            metric="hours",
            padding_period_param_name="incidents_padding_period",
            padding_period_metric="minutes",
        )

    def read_context_data(self) -> None:
        """Read connector's context data from DB (or FileStorage)."""
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = list(read_ids(self.siemplify))
        self.context.backlog_ids = read_backlog_ids(self.siemplify)
        self.context.initial_backlog = set(self.context.backlog_ids)
        self.context.next_page_link = read_next_page_alerts(self.siemplify)

    def store_alert_in_cache(self, incident: Incident) -> None:
        """Store alert in connector's IDs cache.

        Args:
            incident: Incident's data model

        Returns:
            None, updates self.context.existing_ids with incident.name
        """
        self.context.existing_ids.append(incident.name)

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
                inc.created_time_ts
                > self.context.last_success_timestamp.timestamp() * NUM_OF_MILLI_IN_SEC
            )

        super().set_last_success_time(
            filtered_alerts=list(filter(after_last_success_time, filtered_alerts)),
            unprocessed_alerts=list(
                filter(
                    after_last_success_time,
                    unprocessed_alerts,
                )
            ),
            timestamp_key="created_time_ts",
        )

    def write_context_data(self, filtered_alerts: list[Incident], _: Any) -> None:
        """Saves connector's context data into DB (or FileStorage).

        Args:
            filtered_alerts: List of filtered alerts
            _ : Unused parameter

        Returns:
            None, updates self.context.existing_ids and self.context.backlog_ids
        """
        if filtered_alerts:
            self.logger.info("Saving existing ids.")
            write_ids(
                self.siemplify,
                self.context.existing_ids,
                stored_ids_limit=constants.STORED_IDS_LIMIT,
            )

            # Exclude from backlog fetched alerts that were already processed
            incident_number_lookup = {
                str(incident.properties.incident_number)
                for incident in filtered_alerts
                if incident.name in self.context.existing_ids
            }

            if incident_number_lookup:
                self.context.next_page_link = ""

            self.context.backlog_ids = {
                id_: ts
                for id_, ts in self.context.backlog_ids.items()
                if id_ not in incident_number_lookup
            }

        if self.context.initial_backlog.symmetric_difference(self.context.backlog_ids):
            self.logger.info("Saving backlog ids.")
            write_backlog_ids(self.siemplify, self.context.backlog_ids)

    async def finalize(self) -> None:
        """Connector finalization coroutine."""
        if not hasattr(self.context, "next_page_link"):
            return

        if not self.is_test_run:
            write_next_page_alerts(
                self.siemplify, data_to_write=self.context.next_page_link
            )

        await self.manager.async_client.aclose()

    async def _get_backlog_incidents(self) -> list[Incident]:
        """Fetch backlog incidents data from Azure Sentinel.

        Returns:
            List of Incident data models
        """
        fetched_backlog_incidents = []

        backlog_incidents_futures = [
            self.manager.get_incident_by_number(incident_number=inc_number)
            for inc_number in self.context.backlog_ids
        ]

        for backlog_incident_future in asyncio.as_completed(backlog_incidents_futures):
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

                fetched_backlog_incidents.append(await backlog_incident_future)

            except TimeoutIsApproachingError as error:
                self.logger.info(
                    "Connector approaching timeout when trying to fetch backlog "
                    f"incident. {error}",
                )
                break
            except httpx.TimeoutException as ex:
                self.logger.info(
                    "Got HTTP timeout when fetching backlog incident with "
                    f"number={_incident_number_from_url(ex.request.url)}"
                )
            except MicrosoftAzureSentinelIncidentNotFoundError as error:
                inc_number, error_msg = error.args
                self.logger.error(
                    f"Failed to fetch {inc_number} backlog incident. Error: {error_msg}"
                )
                if inc_number in self.context.backlog_ids:
                    del self.context.backlog_ids[inc_number]
                    self.logger.info(
                        f"Removed {inc_number} from backlog as it was not found "
                        "on Sentinel."
                    )

        return fetched_backlog_incidents

    async def get_alerts(self) -> list[Incident]:
        """Fetches new incidents from Azure Sentinel.

        Returns:
            List of Incident data models
        """
        all_fetched_incidents = await self._get_backlog_incidents()
        self.logger.info(f"Fetched {len(all_fetched_incidents)} backlog alerts.")

        filtered_incidents_lookup = set(self.context.existing_ids)
        filtered_incidents_lookup.update(
            incident.name for incident in all_fetched_incidents
        )
        try:
            (
                fetched_incidents,
                self.context.next_page_link,
            ) = await self.manager.get_incidents_with_new_endpoint(
                creation_time=self.context.last_success_timestamp,
                statuses=self.params.incident_statuses_to_fetch,
                severities=self.params.incident_severities_to_fetch,
                limit=self.params.max_new_incidents_per_cycle,
                existing_ids=filtered_incidents_lookup,
                next_page_link=self.context.next_page_link,
            )
        except MicrosoftAzureSentinelError as err:
            error_text = (
                "An error occurred when fetching the incidents. "
                f"Error representation: {err}."
            )

            if isinstance(err, MicrosoftAzureSentinelManagerError):
                error_text += f" Error context: {str(err.error_context)}"

            self.logger.error(error_text)

            self.context.next_page_link = ""
            raise
        except httpx.TimeoutException:
            self.logger.info("No new incidents were fetched because of timeout")

            fetched_incidents = []
            self.context.next_page_link = ""

        self.logger.info(f"Number of fetched alerts: {len(fetched_incidents)}")

        all_fetched_incidents.extend(fetched_incidents)
        self.logger.info(f"Total alerts to process: {len(all_fetched_incidents)}")
        return all_fetched_incidents

    def filter_alerts(self, alerts: list[Incident]) -> list[Incident]:
        """Filter fetched incidents to exclude already fetched.

        Args:
            alerts: List of Incident data models

        Returns:
            List of filtered Incident data models sorted by incident.created_time_ts
        """
        return sorted(
            filter_old_alerts(
                self.siemplify,
                alerts=alerts,
                existing_ids=set(self.context.existing_ids),
                id_key="name",
            ),
            key=lambda _alert: _alert.created_time_ts,
        )

    async def process_alert(self, alert: Incident) -> Incident:
        """Process alert coroutine.

        Args:
            alert: Incident data model

        Returns:
            Processed Incident data model
        """
        self.logger.info(
            f"Processing incident {alert.alert_id} "
            f"with timestamps: {alert.created_time_ts}"
        )

        return await self.manager.adjust_incidents_alerts_data(
            incident=alert,
            connector_starting_time=self.connector_start_time,
            python_process_timeout=self.params.python_process_timeout,
            scheduled_alerts_events_limit=(
                self.params.scheduled_alerts_events_limit_to_ingest
            ),
            incidents_alerts_limit_to_ingest=(
                self.params.incidents_alerts_limit_to_ingest
            ),
            backlog_ids=self.context.backlog_ids,
            alerts_for_no_entities=self.params.alerts_for_no_entities,
            use_same_approach=self.params.use_same_approach,
            wait_for_scheduled_alerts=self.params.wait_for_scheduled_alerts,
        )

    def pass_filters(self, alert: Incident) -> bool:
        """Check if incident passes whitelist filter and is fully fetched.

        Args:
            alert: Incident data model

        Returns:
            True if passes filter, False otherwise
        """
        _incident_number = str(alert.properties.incident_number)

        if self.siemplify.whitelist and not pass_whitelist_filter(
            self.siemplify,
            self.params.use_dynamic_list_as_a_blocklist,
            model=alert,
            model_key="incident_title",
        ):
            if _incident_number in self.context.backlog_ids:
                self.logger.info(
                    f"Backlog alert {alert.name} ({_incident_number}) "
                    "is blacklisted, removing from backlog ..."
                )
                del self.context.backlog_ids[_incident_number]

            return False

        if self.params.incidents_tags_to_ingest and not (
            alert.incident_labels
            and pass_whitelist_filter(
                self.siemplify,
                whitelist_as_a_blacklist=False,
                model=alert,
                model_key="incident_labels",
                whitelist=self.params.incidents_tags_to_ingest,
            )
        ):
            if _incident_number in self.context.backlog_ids:
                self.logger.info(
                    f"Backlog alert {alert.name} ({_incident_number}) "
                    "is blacklisted by tags, removing from backlog ..."
                )
                del self.context.backlog_ids[_incident_number]

            return False

        # Checking if fetched incident is ready for processing
        _is_backlog_expired = self.connector_start_time >= (
            self.context.backlog_ids.get(_incident_number, 0)
            + self.params.backlog_expiration_timer * 60 * 1000
        )

        if alert.fully_fetched:
            _processing_type = (
                "Backlog alert"
                if _incident_number in self.context.backlog_ids
                else "Regular alert"
            )
            self.logger.info(
                f"{_processing_type} {alert.name} ({_incident_number})"
                f" will be fully processed"
            )

        elif _incident_number not in self.context.backlog_ids:
            self.logger.info(
                f"Sending alert {alert.name} ({_incident_number}) to backlog."
            )
            self.context.backlog_ids[_incident_number] = unix_now()
            return False

        elif _is_backlog_expired:
            self.logger.info(
                f"Expired backlog alert "
                f"{alert.name} ({_incident_number}) will be "
                f"partially processed."
            )

        else:
            self.logger.info(
                f"Alert {alert.name} ({_incident_number}) will stay "
                f"in backlog as it wasn't fully fetched."
            )
            return False

        return True

    def set_time_for_alert(
        self, alert_info: AlertInfo, incident: Incident, flat_incident: dict
    ) -> None:
        """Try setting start and end time using fallbacks and log the process.

        Args:
            alert_info: AlertInfo object of SOAR alert
            incident: Incident data model
            flat_incident: Flat incident data to use for fallbacks fetch

        Returns:
            None, update alert_info on the spot
        """
        start_time = incident.properties.created_time_utc
        end_time = incident.properties.created_time_utc

        for item in self.params.start_time_fallback:
            if flat_incident.get(item):
                start_time = flat_incident[item]
                if self.params.fallback_logic_debug:
                    flat_incident["StartTimeFallback"] = item
                break

        for item in self.params.end_time_fallback:
            if flat_incident.get(item):
                end_time = flat_incident[item]
                if self.params.fallback_logic_debug:
                    flat_incident["EndTimeFallback"] = item
                break

        if start_time:
            alert_info.start_time = convert_string_to_unix_time(start_time)
            if self.params.fallback_logic_debug and not flat_incident.get(
                "StartTimeFallback"
            ):
                flat_incident["StartTimeFallback"] = "CreatedTimeUTC"
        else:
            alert_info.start_time = unix_now()
            self.logger.info(
                "Chronicle SOAR Alert's start time is set to current time, as "
                "no values were found with the provided fallback fields."
            )
            if self.params.fallback_logic_debug:
                flat_incident["StartTimeFallback"] = "Current time"

        if end_time:
            alert_info.end_time = convert_string_to_unix_time(end_time)
            if self.params.fallback_logic_debug and not flat_incident.get(
                "EndTimeFallback"
            ):
                flat_incident["EndTimeFallback"] = "CreatedTimeUTC"
        else:
            alert_info.end_time = unix_now()
            self.logger.info(
                "Chronicle SOAR Alert's end time is set to current time, as "
                "no values were found with the provided fallback fields."
            )
            if self.params.fallback_logic_debug:
                flat_incident["EndTimeFallback"] = "Current time"

    def set_product_and_vendor_for_alert(
        self, alert_info: AlertInfo, incident: Incident, flat_incident: dict
    ) -> None:
        """Try setting Vendor and Product using fallbacks and log the process.

        Args:
            alert_info: AlertInfo object of SOAR alert
            incident: Incident data model
            flat_incident: Flat incident data to use for fallbacks fetch

        Returns:
            None, update alert_info on the spot
        """
        product_value = None
        vendor_value = None

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

            product_value, item = find_fallback_value(
                source_dicts=[
                    source_event_flat,
                    dict_to_flat(source_alert.to_event()),
                    flat_incident,
                ],
                fallbacks_list=self.params.product_field_fallback,
            )
        else:
            for item in self.params.product_field_fallback:
                if flat_incident.get(item):
                    product_value = flat_incident[item]
                    if self.params.fallback_logic_debug:
                        flat_incident["ProductFieldFallback"] = item
                    break

            for item in self.params.vendor_field_fallback:
                if flat_incident.get(item):
                    vendor_value = flat_incident[item]
                    if self.params.fallback_logic_debug:
                        flat_incident["VendorFieldFallback"] = item
                    break

        alert_info.device_vendor = (
            vendor_value if vendor_value else constants.DEFAULT_VENDOR_NAME
        )
        alert_info.device_product = (
            product_value if product_value else constants.DEFAULT_PRODUCT_NAME
        )

    def build_events_data(self, incident: Incident, flat_incident: dict) -> list[dict]:
        """Build events data out of alerts for incident and return their flat data.

        Args:
            incident: Incident data model
            flat_incident: Flattened incident data

        Returns:
            List of flattened event dicts
        """
        if not incident.properties.alerts:
            flat_incident["kind"] = constants.INCIDENT_EVENT_KIND
            return [flat_incident]

        events = []

        for incident_alert in incident.properties.alerts:
            if (
                incident_alert.is_scheduled_or_nrt()
                and not self.params.use_same_approach
            ):
                if not incident_alert.scheduled_alert:
                    self.logger.info(
                        f"Incident alert {incident_alert.id} is scheduled "
                        "but has no scheduled alerts data fetched. "
                        "Incident alert data will be used instead."
                    )
                    events.append(incident_alert.to_event())
                    events.extend(
                        create_regular_alert_events(
                            flat_incident,
                            incident_alert,
                            self.params.create_extra_events_for_all_entities,
                            self.params.product_field_fallback,
                            self.params.fallback_logic_debug,
                        )
                    )
                    continue

                events.extend(
                    create_scheduled_alert_events(
                        flat_incident,
                        incident_alert,
                        self.params.create_extra_events_for_all_entities,
                        self.params.product_field_fallback,
                        self.params.fallback_logic_debug,
                    )
                )

            else:
                # Use the alert itself as the event
                events.append(incident_alert.to_event())

                events.extend(
                    create_regular_alert_events(
                        flat_incident,
                        incident_alert,
                        self.params.create_extra_events_for_all_entities,
                        self.params.product_field_fallback,
                        self.params.fallback_logic_debug,
                    )
                )

        return events

    def adjust_events_data(self, alert_info: AlertInfo, incident: Incident) -> None:
        """Adjust events data with all additional fields.

        Args:
            alert_info: SOAR alert data model
            incident: Incident data model

        Returns:
            None, update alert_info.events dicts on the sport
        """
        for event in alert_info.events:
            event["properties_title"] = incident.properties.title
            event["properties_incidentNumber"] = incident.properties.incident_number
            event["properties_incidentUrl"] = incident.properties.incident_url
            event["alert_type"] = incident.type

            for item in self.params.event_field_fallback:
                if event.get(item):
                    event["event_type"] = event[item]
                    if self.params.fallback_logic_debug:
                        event["EventFieldFallback"] = item
                    break

            event_start_time = incident.properties.created_time_utc
            event_end_time = incident.properties.created_time_utc
            for item in self.params.start_time_fallback:
                if event.get(item):
                    event_start_time = event[item]
                    if self.params.fallback_logic_debug:
                        event["StartTimeFallback"] = item
                    break
            for item in self.params.end_time_fallback:
                if event.get(item):
                    event_end_time = event[item]
                    if self.params.fallback_logic_debug:
                        event["EndTimeFallback"] = item
                    break

            if event_start_time:
                event["Siemplify_Start_Time"] = event_start_time
                if self.params.fallback_logic_debug and not event.get(
                    "StartTimeFallback"
                ):
                    event["StartTimeFallback"] = "CreatedTimeUTC"
            else:
                event["Siemplify_Start_Time"] = utc_now().isoformat()
                if self.params.fallback_logic_debug:
                    event["StartTimeFallback"] = "Current time"

            if event_end_time:
                event["Siemplify_End_Time"] = event_end_time
                if self.params.fallback_logic_debug and not event.get(
                    "EndTimeFallback"
                ):
                    event["EndTimeFallback"] = "CreatedTimeUTC"
            else:
                event["Siemplify_End_Time"] = utc_now().isoformat()
                if self.params.sfallback_logic_debug:
                    event["EndTimeFallback"] = "Current time"

    def create_alert_info(self, incident: Incident) -> AlertInfo:
        """Create AlertInfo object out of and Incident data model.

        Args:
            incident: Incident data model

        Returns:
            AlertInfo object
        """
        flat_incident = incident.raw_to_flat_data()
        alert_info = AlertInfo()

        alert_info.display_id = incident.name
        alert_info.ticket_id = incident.name
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
        alert_info.description = incident.properties.description
        alert_info.priority = MicrosoftAzureSentinelParser.calculate_priority(
            incident.properties.severity
        )

        self.set_time_for_alert(
            alert_info=alert_info, incident=incident, flat_incident=flat_incident
        )

        self.set_product_and_vendor_for_alert(
            alert_info=alert_info, incident=incident, flat_incident=flat_incident
        )

        extensions_dict: SingleJson = {
            "status": incident.properties.status,
            "labels": [str(label) for label in incident.properties.labels],
            "endTimeUtc": incident.properties.end_time_utc,
            "startTimeUtc": incident.properties.start_time_utc,
            "owner": (
                incident.properties.owner.assigned_to
                if incident.properties.owner
                else None
            ),
            "lastModifiedTimeUtc": incident.properties.last_modified_time_utc,
            "createdTimeUtc": incident.properties.created_time_utc,
            "incidentNumber": incident.properties.incident_number,
            "incidentUri": incident.properties.incident_url,
            "additionalData": incident.properties.additional_data,
        }

        if incident.properties.provider_incident_id:
            extensions_dict[
                "graph_incident_id"
            ] = incident.properties.provider_incident_id

        alert_info.extensions = dict_to_flat(extensions_dict)
        alert_info.events = self.build_events_data(
            incident=incident,
            flat_incident=flat_incident,
        )
        alert_info.environment = self.env_common.get_environment(flat_incident)

        self.adjust_events_data(alert_info=alert_info, incident=incident)
        return alert_info


async def main() -> None:
    """main"""
    script_name = constants.INCIDENT_CONNECTOR_V2_NAME
    is_test = is_test_run(sys.argv)
    connector = IssuesConnector(script_name, is_test)
    await asyncio.ensure_future(connector.start())


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())