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
from copy import deepcopy
import pytest
from ..core.datamodels import Detection, Device
from ..core.ExtrahopManager import ExtrahopManager
from ..tests import common
from ..tests.core.product import Extrahop
from ..tests.core.session import ExtrahopSession


class TestApiManager:
    """Unit tests for Integration's ExtrahopManager methods."""

    def test_ping_success(
        self,
        manager: ExtrahopManager,
        extrahop: Extrahop,
        script_session: ExtrahopSession,
    ) -> None:
        """Test ping success.

        Verify that the test_connectivity method successfully pings the Extrahop API and
        returns a 200 status code.

        Args:
            manager (ExtrahopManager): ExtrahopManager object.
            extrahop (Extrahop): Extrahop product object.
            script_session (ExtrahopSession): ExtrahopSession object.
        """
        extrahop.cleanup_devices()
        device: Device = deepcopy(common.DEVICE)
        extrahop.add_device(device)

        manager.test_connectivity()

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 200
        assert script_session.request_history[0].response.json() == [
            extrahop.get_device(device.id).to_json()
        ]

    def test_ping_failure_invalid_token(
        self,
        manager: ExtrahopManager,
        extrahop: Extrahop,
        script_session: ExtrahopSession,
    ) -> None:
        """Test ping failure due to invalid token.

        Args:
            manager (ExtrahopManager): ExtrahopManager object.
            extrahop (Extrahop): Extrahop product object.
            script_session (ExtrahopSession): ExtrahopSession object.
        """
        extrahop.cleanup_devices()
        device: Device = deepcopy(common.DEVICE)
        device.id = common.INVALID_DEVICE_ID
        device.raw_data["id"] = common.INVALID_DEVICE_ID
        extrahop.add_device(device)
        with pytest.raises(Exception) as e:
            manager.test_connectivity()

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 401
        assert script_session.request_history[0].response.json() == common.INVALID_TOKEN
        assert type(e.value).__name__ == "InvalidCredentialsError"
        assert "Please check the credentials." in str(e.value)

    def test_get_detections_success(
        self,
        manager: ExtrahopManager,
        extrahop: Extrahop,
        script_session: ExtrahopSession,
    ) -> None:
        """Test getting detections successfully..

        Args:
            manager (ExtrahopManager): ExtrahopManager object.
            extrahop (Extrahop): Extrahop product object.
            script_session (ExtrahopSession): ExtrahopSession object.
        """
        extrahop.cleanup_detections()
        detection_1: Detection = deepcopy(common.DETECTION)
        extrahop.add_detection(detection_1)
        detection_2: Detection = deepcopy(common.DETECTION)
        detection_2.id = 2
        detection_2.raw_data["id"] = 2

        extrahop.add_detection(detection_1)
        extrahop.add_detection(detection_2)
        manager.get_detections(
            existing_ids=[],
            limit=10,
            start_timestamp=None,
        )

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.json()[0]["id"] == int(
            extrahop.get_detections()[0].id
        )
        assert script_session.request_history[0].response.json()[1]["id"] == int(
            extrahop.get_detections()[1].id
        )

    def test_get_detections_failure(
        self,
        manager: ExtrahopManager,
        extrahop: Extrahop,
        script_session: ExtrahopSession,
    ) -> None:
        """Test getting detections failure.

        Args:
            manager (ExtrahopManager): ExtrahopManager object.
            extrahop (Extrahop): Extrahop product object.
            script_session (ExtrahopSession): ExtrahopSession object.
        """
        extrahop.cleanup_detections()
        detection_1: Detection = deepcopy(common.DETECTION)
        extrahop.add_detection(detection_1)

        with pytest.raises(Exception) as e:
            manager.get_detections(
                existing_ids=[],
                limit=10,
                start_timestamp="invalid_time",
            )

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 400
        assert type(e.value).__name__ == "ExtrahopException"
        assert "value not supported" in str(e.value)

    def test_get_device_details_success(
        self,
        manager: ExtrahopManager,
        extrahop: Extrahop,
        script_session: ExtrahopSession,
    ) -> None:
        """Test getting device successfully.

        Args:
            manager (ExtrahopManager): ExtrahopManager object.
            extrahop (Extrahop): Extrahop product object.
            script_session (ExtrahopSession): ExtrahopSession object.
        """
        extrahop.cleanup_devices()
        device: Device = deepcopy(common.DEVICE)
        extrahop.add_device(device)
        manager.get_device_details(device_id=device.id)

        assert len(script_session.request_history) == 1

    def test_get_device_details_failure(
        self,
        manager: ExtrahopManager,
        extrahop: Extrahop,
        script_session: ExtrahopSession,
    ) -> None:
        """Test getting device failure.

        Args:
            manager (ExtrahopManager): ExtrahopManager object.
            extrahop (Extrahop): Extrahop product object.
            script_session (ExtrahopSession): ExtrahopSession object.
        """
        extrahop.cleanup_devices()
        device: Device = deepcopy(common.DEVICE)
        device.id = 999999
        device.raw_data["id"] = 999999
        extrahop.add_device(device)

        with pytest.raises(Exception) as e:
            manager.get_device_details(device_id=device.id)

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 400
        assert type(e.value).__name__ == "ExtrahopException"
        assert "device_not_found" in str(e.value)

    def test_update_detection_success(
        self,
        manager: ExtrahopManager,
        extrahop: Extrahop,
        script_session: ExtrahopSession,
    ) -> None:
        """Test update detection successfully.

        Args:
            manager (ExtrahopManager): ExtrahopManager object.
            extrahop (Extrahop): Extrahop product object.
            script_session (ExtrahopSession): ExtrahopSession object.
        """
        extrahop.cleanup_detections()
        detection: Detection = deepcopy(common.DETECTION)
        extrahop.add_detection(detection)
        manager.update_detection(
            detection_id=detection.id,
            status="Closed",
            resolution="Action Taken",
        )

        assert len(script_session.request_history) == 2
        assert script_session.request_history[0].response.status_code == 204
        assert script_session.request_history[0].response.json() == {}
        assert script_session.request_history[1].response.status_code == 200
        assert (
            script_session.request_history[1].response.json()
            == extrahop.get_detection(detection.id).to_json()
        )

    def test_update_detection_failure(
        self,
        manager: ExtrahopManager,
        extrahop: Extrahop,
        script_session: ExtrahopSession,
    ) -> None:
        """Test update detection failure.

        Args:
            manager (ExtrahopManager): ExtrahopManager object.
            extrahop (Extrahop): Extrahop product object.
            script_session (ExtrahopSession): ExtrahopSession object.
        """
        extrahop.cleanup_detections()
        detection: Detection = deepcopy(common.DETECTION)
        detection.id = "999999"
        detection.raw_data["id"] = "999999"
        extrahop.add_detection(detection)

        with pytest.raises(Exception) as e:
            manager.update_detection(
                detection_id=detection.id,
                status="Closed",
                resolution="Action Taken",
            )

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 404
        assert type(e.value).__name__ == "InvalidDetectionIDError"
        assert "Detection not found." in str(e.value)

    def test_get_detection_success(
        self,
        manager: ExtrahopManager,
        extrahop: Extrahop,
        script_session: ExtrahopSession,
    ) -> None:
        """Test getting a detection successfully.

        Args:
            manager (ExtrahopManager): ExtrahopManager object.
            extrahop (Extrahop): Extrahop product object.
            script_session (ExtrahopSession): ExtrahopSession object.
        """
        extrahop.cleanup_detections()
        detection: Detection = deepcopy(common.DETECTION)
        extrahop.add_detection(detection)
        manager.get_detection(detection_id=detection.id)

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 200
        assert (
            script_session.request_history[0].response.json()
            == extrahop.get_detection(detection.id).to_json()
        )

    def test_get_detection_failure(
        self,
        manager: ExtrahopManager,
        extrahop: Extrahop,
        script_session: ExtrahopSession,
    ) -> None:
        """Test getting a detection failure.

        Args:
            manager (ExtrahopManager): ExtrahopManager object.
            extrahop (Extrahop): Extrahop product object.
            script_session (ExtrahopSession): ExtrahopSession object.
        """
        extrahop.cleanup_detections()
        detection: Detection = deepcopy(common.DETECTION)
        detection.id = "999999"
        detection.raw_data["id"] = "999999"
        extrahop.add_detection(detection)

        with pytest.raises(Exception) as e:
            manager.get_detection(detection_id=detection.id)

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 404
        assert type(e.value).__name__ == "InvalidDetectionIDError"
        assert "Detection not found." in str(e.value)
