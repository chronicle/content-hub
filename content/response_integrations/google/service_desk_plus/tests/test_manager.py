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
import pathlib

import pytest

from ..core.ServiceDeskPlusManager import ServiceDeskPlusManager, ServiceDeskPlusManagerError
from ..core.datamodels import WorkOrder

class TestServiceDeskPlusManager:

    def test_test_connectivity_success(
        self,
        manager: ServiceDeskPlusManager,
    ) -> None:
        assert manager.test_connectivity() is True

    def test_test_connectivity_failure(
        self,
        manager: ServiceDeskPlusManager,
    ) -> None:
        manager.api_url_base = "https://invalid.url"
        with pytest.raises(ServiceDeskPlusManagerError):
            manager.test_connectivity()

    def test_add_request_success(
        self,
        manager: ServiceDeskPlusManager,
    ) -> None:
        result: WorkOrder = manager.add_request(
            subject="Test Subject",
            requester="Test Requester",
        )
        assert result is not None
        assert result.raw_data["workorderid"] == "12345"

    def test_add_request_failure(
        self,
        manager: ServiceDeskPlusManager,
    ) -> None:
        with pytest.raises(ServiceDeskPlusManagerError):
            manager.add_request(subject="FailSubject")
