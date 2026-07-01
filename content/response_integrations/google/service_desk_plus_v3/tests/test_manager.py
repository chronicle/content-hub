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

from ..core.ServiceDeskPlusManagerV3 import ServiceDeskPlusManagerV3, ServiceDeskPlusV3Exception

class TestServiceDeskPlusManagerV3:
    def test_test_connectivity_success(
        self,
        manager: ServiceDeskPlusManagerV3,
    ) -> None:
        manager.test_connectivity()

    def test_test_connectivity_failure(
        self,
        manager: ServiceDeskPlusManagerV3,
    ) -> None:
        manager.session.headers["TECHNICIAN_KEY"] = "invalid_key"
        with pytest.raises(ServiceDeskPlusV3Exception):
            manager.test_connectivity()

    def test_add_request_success(
        self,
        manager: ServiceDeskPlusManagerV3,
    ) -> None:
        result = manager.request(
            action_type="CREATE",
            request_id="",
            description="Test Description",
            subject="Test Subject",
            requester="Test Requester",
            status=None,
            technician=None,
            priority=None,
            urgency=None,
            category=None,
            request_template=None,
            request_type=None,
            due_by_time=None,
            mode=None,
            level=None,
            site=None,
            group=None,
            impact=None,
            assets=None,
        )
        assert result is not None
        assert result.to_json()["request"]["id"] == "12345"

    def test_add_request_failure(
        self,
        manager: ServiceDeskPlusManagerV3,
    ) -> None:
        with pytest.raises(ServiceDeskPlusV3Exception):
            manager.request(
                action_type="CREATE",
                request_id="",
                description="Test Description",
                subject="FailSubject",
                requester="Test Requester",
                status=None,
                technician=None,
                priority=None,
                urgency=None,
                category=None,
                request_template=None,
                request_type=None,
                due_by_time=None,
                mode=None,
                level=None,
                site=None,
                group=None,
                impact=None,
                assets=None,
            )
