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
from collections.abc import Iterable

from ...tests import common
from ...tests.core.product import Extrahop
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class ExtrahopSession(MockSession[MockRequest, MockResponse, Extrahop]):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            get_oauth_token,
            self.get_device,
            self.get_devices,
            self.get_detection,
            self.get_detections,
            self.update_detection,
        ]

    @router.get(r"/api/v1/devices")
    def get_devices(self, _: MockRequest) -> MockResponse:
        """Handle GET /api/v1/devices requests"""
        devices = self._product.get_devices()
        if devices and devices[0].id == common.INVALID_DEVICE_ID:
            return MockResponse(content=common.INVALID_TOKEN, status_code=401)

        return MockResponse(content=[device.to_json() for device in devices])

    @router.get(r"/api/v1/devices/[0-9]+")
    def get_device(self, request: MockRequest) -> MockResponse:
        """Handle GET /api/v1/devices/[0-9] requests"""
        device_id = request.url.path.split("/")[-1]
        device = self._product.get_device(int(device_id))
        if device.id == 999999:
            return MockResponse(content=common.INVALID_DEVICE_JSON, status_code=400)

        return MockResponse(content=device.to_json())

    @router.get(r"/api/v1/detections/[0-9]+")
    def get_detection(self, request: MockRequest) -> MockResponse:
        """Handle GET /api/v1/detections/[0-9]+ requests"""
        detection_id = request.url.path.split("/")[-1]
        detection = self._product.get_detection(detection_id)
        if detection.id == "999999":
            return MockResponse(content=common.INVALID_DETECTION_JSON, status_code=404)

        return MockResponse(content=detection.to_json(), status_code=200)

    @router.post(r"/api/v1/detections/search")
    def get_detections(self, request: MockRequest) -> MockResponse:
        """Handle POST /api/v1/detections/search requests"""
        payload = request.kwargs["json"]
        if payload["update_time"] == common.INVALID_TIME:
            return MockResponse(
                content={"error": '"update_time" value not supported'}, status_code=400
            )

        detections = self._product.get_detections()
        return MockResponse(content=[detection.to_json() for detection in detections])

    @router.patch(r"/api/v1/detections/[0-9]+")
    def update_detection(self, request: MockRequest) -> MockResponse:
        """Handle PATCH ./api/v1/detections/[0-9]+ requests"""
        detection_id = request.url.path.split("/")[-1]
        detection = self._product.get_detection(detection_id)
        if detection.id == "999999":
            return MockResponse(content=common.INVALID_DETECTION_JSON, status_code=404)

        return MockResponse(content={}, status_code=204)


@router.post("/oauth2/token")
def get_oauth_token(request: MockRequest) -> MockResponse:
    """Get an OAuth token"""
    if "raise_error" in request.kwargs["data"].values():
        return MockResponse(
            content=common.INVALID_TOKEN,
            status_code=400,
        )

    return MockResponse(common.OAUTH_TOKEN_JSON)
