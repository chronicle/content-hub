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

import pathlib
import abc
from typing import MutableMapping, MutableSequence
from ...core.datamodels import Detection, Device
from ...tests import common


class Extrahop(abc.ABC):

    def __init__(self) -> None:
        self._devices: MutableMapping[str, Device] = {}
        self._detections: MutableMapping[str, Detection] = {}

    def add_detection(self, detection: Detection) -> None:
        self._detections[detection.id] = detection

    def get_detection(self, detection_id: int) -> Detection:
        """Retrieves a detection by its ID.

        Args:
            detection_id (str): The ID of the detection to retrieve.

        Raises:
            common.DetectionNotFoundError: If the detection ID is not found.

        Returns:
            Detection: The detection object.
        """
        try:
            return self._detections[detection_id]

        except KeyError as e:
            raise common.DetectionNotFoundError("Detection ID not found") from e

    def get_detections(self) -> MutableSequence[Detection]:
        return list(self._detections.values())

    def add_device(self, device: Device) -> None:
        self._devices[device.id] = device

    def get_device(self, device_id: str) -> Device:
        """Retrieves a device by its ID.

        Args:
            device_id (str): The ID of the device to retrieve.

        Raises:
            common.DeviceNotFoundError: If the device ID is not found.

        Returns:
            Device: The device object.
        """
        try:
            return self._devices[device_id]

        except KeyError as e:
            raise common.DeviceNotFoundError("Device ID not found") from e

    def get_devices(self) -> MutableSequence[Device]:
        return list(self._devices.values())

    def cleanup_detections(self) -> None:
        self._detections = {}

    def cleanup_devices(self) -> None:
        self._devices = {}
