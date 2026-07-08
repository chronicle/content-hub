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

from typing import TYPE_CHECKING, NamedTuple

import dateutil.parser
from SiemplifyUtils import convert_datetime_to_unix_time
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.data_models import BaseAlert
from TIPCommon.transformation import dict_to_flat

from .constants import (
    EVENT_TYPE_FIELD,
    INTEGRATION_DISPLAY_NAME,
    LAST_SEEN_AT_FIELD,
    SEVERITY_MAP,
    EventType,
)
from .exceptions import AlertUpdateError

if TYPE_CHECKING:
    from datetime import datetime


class IntegrationParameters(NamedTuple):
    api_root: str
    api_token: str
    verify_ssl: bool


class SentinelOneAlert(BaseAlert):
    """Data model representing a SentinelOne Alert."""

    def __init__(
        self, raw_data: dict, details: SentinelOneAlertDetails | None = None
    ) -> None:
        super().__init__(raw_data, raw_data.get("id"))
        self.details = details

    @property
    def is_detailed(self) -> bool:
        """Check if the full alert details are loaded."""
        return self.details is not None

    @property
    def name(self) -> str | None:
        """The alert name."""
        return self.raw_data.get("name")

    @property
    def description(self) -> str | None:
        """The alert description."""
        return self.details.description if self.details else None

    @property
    def severity(self) -> str:
        """The alert severity."""
        if self.details and self.details.severity:
            return self.details.severity.upper()
        return (self.raw_data.get("severity") or "INFO").upper()

    @property
    def classification(self) -> str | None:
        """The alert classification."""
        return self.details.classification if self.details else None

    @property
    def updated_at(self) -> str | None:
        """The alert tracking timestamp string, prioritizing details updatedAt."""
        if self.details:
            return self.details.updated_at or self.details.created_at
        return self.raw_data.get("updatedAt") or self.raw_data.get("createdAt")

    @property
    def created_at(self) -> str | None:
        """The alert creation timestamp string, prioritizing details createdAt."""
        if self.details:
            return self.details.created_at or self.details.detected_at
        return self.raw_data.get("createdAt") or self.raw_data.get("detectedAt")

    @property
    def observables(self) -> list[AlertObservable]:
        """The alert observables."""
        return self.details.observables if self.details else []

    @property
    def indicators(self) -> list[AlertIndicator]:
        """The alert indicators."""
        return self.details.indicators if self.details else []

    @property
    def assets(self) -> list[AlertAsset]:
        """The alert assets."""
        return self.details.assets if self.details else []

    def as_alert_info(
        self,
        environment: str | None,
        *,
        is_update: bool,
        last_success_timestamp: datetime,
        device_product_field: str | None = None,
    ) -> AlertInfo:
        """Map SentinelOne alert to a Siemplify AlertInfo object.

        Args:
            environment (str, optional): The mapped environment name.
            is_update (bool): Whether this alert has been previously processed.
            last_success_timestamp (datetime): Fallback timestamp to use if updatedAt is missing.
            device_product_field (str, optional): The custom product field name parameter.

        Returns:
            AlertInfo: The mapped AlertInfo object.

        """
        alert_info = AlertInfo()

        if is_update:
            alert_info.alert_update_supported = True
            alert_info.updated_fields = {
                "status": self.details.status if self.details else None,
                "analystVerdict": self.details.analyst_verdict
                if self.details
                else None,
                "severity": self.severity,
            }

        alert_info.ticket_id = self.alert_id
        alert_info.display_id = (
            f"SentinelOne_Singularity_Operations_Center_{self.alert_id}"
        )
        alert_info.name = self.name or "SentinelOne Alert"
        alert_info.reason = ""
        alert_info.description = self.description or ""
        alert_info.device_vendor = "SentinelOne Singularity Operations Center"

        # Product field mapping
        product_field = device_product_field or "Product Name"
        alert_info.device_product = (
            self.details.get(product_field) if self.details else None
        ) or INTEGRATION_DISPLAY_NAME

        # Severity mapping
        alert_info.priority = SEVERITY_MAP.get(self.severity, -1)
        alert_info.extensions = {
            "Severity": self.severity.title(),
            "RiskScore": self.severity,
        }

        # Rule generator and grouping
        classification = self.classification or ""
        alert_info.rule_generator = (
            f"SentinelOne Singularity Operations Center Alert: {classification}"
        )
        alert_info.source_grouping_identifier = classification

        # Timestamp parsing
        created_at_str = self.created_at
        dt_start = (
            dateutil.parser.parse(created_at_str)
            if created_at_str
            else last_success_timestamp
        )

        updated_at_str = self.updated_at
        dt_end = dateutil.parser.parse(updated_at_str) if updated_at_str else dt_start

        alert_info.start_time = convert_datetime_to_unix_time(dt_start)
        alert_info.end_time = convert_datetime_to_unix_time(dt_end)

        # Environment
        alert_info.environment = environment

        # Events list construction
        events = []
        if self.details:
            events.append(self.details.as_event())

        events.extend(obs.as_event(self.updated_at) for obs in self.observables)

        events.extend(ind.as_event(self.updated_at) for ind in self.indicators)

        events.extend(asset.as_event(self.updated_at) for asset in self.assets)

        alert_info.events = events

        return alert_info


class SentinelOneAlertDetails:
    """Data model representing SentinelOne Alert Details."""

    def __init__(self, raw_data: dict) -> None:
        self.raw_data = raw_data

    def get(self, key: str, default: object | None = None) -> object | None:
        """Get value from raw data using a fallback default.

        Args:
            key (str): The key to retrieve.
            default (object, optional): The default value to return if key is missing.

        Returns:
            object, optional: The value corresponding to the key, or default.

        """
        return self.raw_data.get(key, default)

    @property
    def id(self) -> str | None:
        """The alert details ID."""
        return self.raw_data.get("id")

    @property
    def description(self) -> str | None:
        """The alert description."""
        return self.raw_data.get("description")

    @property
    def classification(self) -> str | None:
        """The alert classification."""
        return self.raw_data.get("classification")

    @property
    def severity(self) -> str | None:
        """The alert severity."""
        return self.raw_data.get("severity")

    @property
    def status(self) -> str | None:
        """The alert status."""
        return self.raw_data.get("status")

    @property
    def analyst_verdict(self) -> str | None:
        """The alert analyst verdict."""
        return self.raw_data.get("analystVerdict")

    @property
    def created_at(self) -> str | None:
        """The alert creation timestamp string."""
        return self.raw_data.get("createdAt")

    @property
    def detected_at(self) -> str | None:
        """The alert detection timestamp string."""
        return self.raw_data.get("detectedAt")

    @property
    def first_seen_at(self) -> str | None:
        """The alert first seen timestamp string."""
        return self.raw_data.get("firstSeenAt")

    @property
    def last_seen_at(self) -> str | None:
        """The alert last seen timestamp string."""
        return self.raw_data.get("lastSeenAt")

    @property
    def updated_at(self) -> str | None:
        """The alert update timestamp string."""
        return self.raw_data.get("updatedAt")

    @property
    def observables(self) -> list[AlertObservable]:
        """The alert observables."""
        raw_observables = self.raw_data.get("observables") or []
        return [AlertObservable(obs) for obs in raw_observables]

    @property
    def indicators(self) -> list[AlertIndicator]:
        """The alert indicators."""
        raw_indicators = self.raw_data.get("indicators") or []
        return [AlertIndicator(ind) for ind in raw_indicators]

    @property
    def assets(self) -> list[AlertAsset]:
        """The alert assets."""
        raw_assets = self.raw_data.get("assets") or []
        return [AlertAsset(asset) for asset in raw_assets]

    def as_event(self) -> dict:
        """Serialize details to a flat Siemplify event dictionary.

        Returns:
            dict: The flattened event dictionary.

        """
        data = self.raw_data.copy()
        data.pop("observables", None)
        data.pop("indicators", None)
        data.pop("assets", None)
        data[EVENT_TYPE_FIELD] = EventType.ALERT.value
        return dict_to_flat(data)


class AlertObservable:
    """Data model representing a SentinelOne Alert Observable."""

    def __init__(self, raw_data: dict) -> None:
        self.raw_data = raw_data

    @property
    def id(self) -> str | None:
        """The observable ID."""
        return self.raw_data.get("id")

    @property
    def name(self) -> str | None:
        """The observable name."""
        return self.raw_data.get("name")

    @property
    def value(self) -> str | None:
        """The observable value."""
        return self.raw_data.get("value")

    @property
    def type(self) -> str | None:
        """The observable type."""
        return self.raw_data.get("type")

    def as_event(self, alert_updated_at: str | None) -> dict:
        """Serialize observable to a flat Siemplify event dictionary.

        Args:
            alert_updated_at (str, optional): The timestamp when the alert was updated.

        Returns:
            dict: The flattened event dictionary.

        """
        data = self.raw_data.copy()
        data[EVENT_TYPE_FIELD] = EventType.OBSERVABLE.value
        data[LAST_SEEN_AT_FIELD] = alert_updated_at
        if self.name:
            data[self.name] = self.value
        return dict_to_flat(data)


class AlertIndicator:
    """Data model representing a SentinelOne Alert Indicator."""

    def __init__(self, raw_data: dict) -> None:
        self.raw_data = raw_data

    @property
    def id(self) -> str | None:
        """The indicator ID."""
        return self.raw_data.get("id")

    @property
    def value(self) -> str | None:
        """The indicator value."""
        return self.raw_data.get("value")

    @property
    def type(self) -> str | None:
        """The indicator type."""
        return self.raw_data.get("type")

    def as_event(self, alert_updated_at: str | None) -> dict:
        """Serialize indicator to a flat Siemplify event dictionary.

        Args:
            alert_updated_at (str, optional): The timestamp when the alert was updated.

        Returns:
            dict: The flattened event dictionary.

        """
        data = self.raw_data.copy()
        data[EVENT_TYPE_FIELD] = EventType.INDICATOR.value
        data[LAST_SEEN_AT_FIELD] = alert_updated_at
        return dict_to_flat(data)


class AlertAsset:
    """Data model representing a SentinelOne Alert Asset."""

    def __init__(self, raw_data: dict) -> None:
        self.raw_data = raw_data

    @property
    def id(self) -> str | None:
        """The asset ID."""
        return self.raw_data.get("id")

    @property
    def name(self) -> str | None:
        """The asset name."""
        return self.raw_data.get("name")

    @property
    def type(self) -> str | None:
        """The asset type."""
        return self.raw_data.get("type")

    def as_event(self, alert_updated_at: str | None) -> dict:
        """Serialize asset to a flat Siemplify event dictionary.

        Args:
            alert_updated_at (str, optional): The timestamp when the alert was updated.

        Returns:
            dict: The flattened event dictionary.

        """
        data = self.raw_data.copy()
        data[EVENT_TYPE_FIELD] = EventType.ASSET.value
        data[LAST_SEEN_AT_FIELD] = alert_updated_at
        return dict_to_flat(data)


class AlertUpdateResult:
    """Data model representing the result of updating an alert."""

    def __init__(
        self,
        *,
        is_scheduled: bool = False,
        execution_id: str | None = None,
        success_count: int = 0,
        skips: list[str] | None = None,
    ) -> None:
        self.is_scheduled = is_scheduled
        self.execution_id = execution_id
        self.success_count = success_count
        self.skips = skips or []

    @property
    def is_skipped(self) -> bool:
        """Check if the update was skipped (no successes and not scheduled)."""
        return not self.is_scheduled and self.success_count == 0

    @classmethod
    def from_api_response(
        cls,
        response_data: dict,
        alert_id: str,
    ) -> AlertUpdateResult:
        """Create an AlertUpdateResult from a raw API response.

        Args:
            response_data (dict): The raw GraphQL API response dictionary.
            alert_id (str): The ID of the alert being updated.

        Returns:
            AlertUpdateResult: The parsed result.

        Raises:
            AlertUpdateError: If the API returns errors or the update fails.

        """
        data = response_data.get("data", {}) or {}
        result = data.get("alertTriggerActions") or {}
        typename = result.get("__typename")

        if typename == "ActionsTriggered":
            actions = result.get("actions") or []
            failures = []
            skips = []
            success_count = 0

            for action in actions:
                success_count += len(action.get("success") or [])
                failures.extend(
                    f"{action['actionId']}: {f.get('errorMessage')}"
                    for f in action.get("failure") or []
                )
                skips.extend(
                    f"{action['actionId']}: {s.get('skipMessage')}"
                    for s in action.get("skip") or []
                )

            if failures:
                msg = f"Alert update encountered failures for alert '{alert_id}': {', '.join(failures)}"
                raise AlertUpdateError(msg)

            return cls(
                is_scheduled=False,
                success_count=success_count,
                skips=skips,
            )

        if typename == "TriggerActionsError":
            errors = result.get("errors") or []
            error_msgs = [
                e.get("errorMessage") for e in errors if e.get("errorMessage")
            ]
            msg = f"Failed to update SentinelOne alert '{alert_id}' due to API error: {', '.join(error_msgs)}"
            raise AlertUpdateError(msg)

        if typename == "TriggerActionsScheduled":
            execution_id = result.get("executionId")
            return cls(
                is_scheduled=True,
                execution_id=execution_id,
            )

        msg = f"Received unexpected response type from SentinelOne API: {typename}"
        raise AlertUpdateError(msg)


class AlertNote:
    """Data model representing a SentinelOne Alert Note/Comment."""

    def __init__(self, raw_data: dict) -> None:
        self.raw_data = raw_data

    @property
    def id(self) -> str | None:
        """The note ID."""
        return self.raw_data.get("id")

    @property
    def alert_id(self) -> str | None:
        """The alert ID."""
        return self.raw_data.get("alertId")

    @property
    def text(self) -> str | None:
        """The text of the note."""
        return self.raw_data.get("text")

    @property
    def type(self) -> str | None:
        """The type of the note (ContentType)."""
        return self.raw_data.get("type")

    @property
    def created_at(self) -> str | None:
        """The note creation timestamp."""
        return self.raw_data.get("createdAt")

    @property
    def updated_at(self) -> str | None:
        """The note update timestamp."""
        return self.raw_data.get("updatedAt")
