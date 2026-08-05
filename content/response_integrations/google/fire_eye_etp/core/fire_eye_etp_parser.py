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


"""Parser for FireEye ETP payload data."""

from __future__ import annotations

from typing import Any

from .datamodels import Alert


class FireEyeETPParser:
    """Parser class for converting ETP raw data into datamodels."""

    def build_first_alert(self, raw_data: dict[str, Any], timezone_offset: str | None = None) -> Alert | None:
        """Build the first alert from raw data.

        Args:
            raw_data: The raw API response JSON.
            timezone_offset: The timezone offset.

        Returns:
            The parsed Alert object, or None if no alerts found.

        """
        data_json: list[dict[str, Any]] = raw_data.get("data", [])
        if data_json:
            return self.build_siemplify_alert_obj(alert_data=data_json[0], timezone_offset=timezone_offset)
        return None

    def build_alerts_array(self, raw_json: dict[str, Any], timezone_offset: str | None = None) -> list[Alert]:
        """Build an array of alerts from raw JSON response.

        Args:
            raw_json: The raw API response JSON.
            timezone_offset: The timezone offset.

        Returns:
            A list of parsed Alert objects.

        """
        alerts_data: list[dict[str, Any]] = raw_json.get("data", []) or []
        return [
            self.build_siemplify_alert_obj(alert_data=alert_data, timezone_offset=timezone_offset)
            for alert_data in alerts_data
        ]

    @staticmethod
    def build_siemplify_alert_obj(alert_data: dict[str, Any], timezone_offset: str | None = None) -> Alert:
        """Build a single Alert object from alert data.

        Args:
            alert_data: The single alert JSON object.
            timezone_offset: The timezone offset.

        Returns:
            The parsed Alert object.

        """
        return Alert(
            raw_data=alert_data,
            timezone_offset=timezone_offset,
        )
