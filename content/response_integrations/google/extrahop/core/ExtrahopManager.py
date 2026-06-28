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
from collections.abc import MutableMapping
from datetime import datetime
import dataclasses
import requests

from TIPCommon.filters import filter_old_alerts
from extrahop.core import api_utils
from extrahop.core.constants import (
    ALERT_ID_KEY,
    DEFAULT_LIMIT,
    DEFAULT_PARAM_VALUE,
    RESOLUTION_MAPPING,
    STATUS_MAPPING,
)
from extrahop.core.datamodels import Detection, Device
from extrahop.core.ExtrahopParser import ExtrahopParser


@dataclasses.dataclass(slots=True)
class ApiParameters:
    api_root: str
    client_id: str
    client_secret: str


class ExtrahopManager:

    def __init__(
        self,
        session: requests.Session,
        api_parameters: ApiParameters,
        siemplify=None,
    ) -> None:
        self.api_root = (
            api_parameters.api_root[:-1]
            if api_parameters.api_root.endswith("/")
            else api_parameters.api_root
        )
        self.client_id = api_parameters.client_id
        self.client_secret = api_parameters.client_secret
        self.siemplify = siemplify
        self.parser = ExtrahopParser()
        self.session: requests.Session = session
        self.session.auth = None

    def test_connectivity(self) -> None:
        """Test connectivity"""
        url = api_utils.get_full_url(self.api_root, "ping")
        response = self.session.get(url)
        api_utils.validate_response(response)

    def get_detections(
        self,
        existing_ids: list[str],
        limit: int,
        start_timestamp: datetime,
    ) -> list[Detection]:
        """Get detections.

        Args:
            existing_ids(list): The list of existing ids
            limit(int): The limit for results
            start_timestamp(datetime): The timestamp for oldest detection to fetch.

        Returns:
            list[Detection]: The list of filtered Detection objects.
        """
        request_url = api_utils.get_full_url(self.api_root, "get_detections")
        payload = {
            "sort": [{"direction": "asc", "field": "update_time"}],
            "filter": {"status": ["new", "in_progress", ".none"]},
            "update_time": start_timestamp,
            "limit": max(limit, DEFAULT_LIMIT),
        }
        response = self.session.post(request_url, json=payload)
        api_utils.validate_response(response)
        detections = self.parser.build_detections_list(response.json())

        filtered_detections = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=detections,
            existing_ids=existing_ids,
            id_key=ALERT_ID_KEY,
        )
        return sorted(filtered_detections, key=lambda detection: detection.update_time)[
            :limit
        ]

    def get_device_details(self, device_id: int) -> Device:
        """Get device details

        Args:
            device_id(int): Id of the device.

        Returns:
            Device: Device object.
        """
        request_url = api_utils.get_full_url(
            self.api_root,
            "get_device_details",
            device_id=device_id,
        )
        response = self.session.get(request_url)
        api_utils.validate_response(response)
        return self.parser.build_device(response.json())

    def update_detection(
        self,
        detection_id: str,
        status: str,
        resolution: str,
        assign_to: str | None = None,
    ) -> Detection:
        """Update detection in Extrahop.

        Args:
            detection_id (str): Detection ID.
            status (str): Status to be updated.
            resolution (str): Resolution to be updated.
            assign_to (str | None): Assignee to be updated.

        Returns:
            Detection: Detection object.
        """
        payload: MutableMapping[str, str] = {}
        if status != DEFAULT_PARAM_VALUE:
            payload["status"] = STATUS_MAPPING.get(status)
        if assign_to:
            if assign_to == "Unassign":
                payload["assignee"] = None
            else:
                payload["assignee"] = assign_to
        if resolution != DEFAULT_PARAM_VALUE:
            payload["resolution"] = RESOLUTION_MAPPING.get(resolution)
        url = api_utils.get_full_url(
            self.api_root, "get_and_update_detection", detection_id=detection_id
        )
        response = self.session.patch(url=url, json=payload)
        api_utils.validate_response(response)

        return self.get_detection(detection_id=detection_id)

    def get_detection(self, detection_id: str) -> Detection:
        """Gets the detection from Extrahop.

        Args:
            detection_id (str): Detection ID.

        Returns:
            Detection: Detection object.
        """
        url = api_utils.get_full_url(
            self.api_root, "get_and_update_detection", detection_id=detection_id
        )
        response = self.session.get(url=url)
        api_utils.validate_response(response)

        return self.parser.build_detection(response.json())
