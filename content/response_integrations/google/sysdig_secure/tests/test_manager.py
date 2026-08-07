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

from ..core.SysdigSecureManager import ApiManager

from ..tests.core.session import ApiSession
from integration_testing.request import HttpMethod


class TestApiManager:
    """Unit tests for Sysdig Secure ApiManager."""
    def test_test_connectivity(
            self,
            sysdig_script_session: ApiSession,
            sysdig_manager: ApiManager
    ):
        sysdig_manager.test_connectivity()

        assert len(sysdig_script_session.request_history) >= 1
        assert (
            sysdig_script_session.request_history[-1].request.method
            == HttpMethod.GET
        )
        assert (
            sysdig_script_session.request_history[-1].request.url.path
            .endswith("events")
        )
