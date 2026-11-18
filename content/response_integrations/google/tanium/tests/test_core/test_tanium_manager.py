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
from tanium.core.TaniumManager import TaniumManager
from tanium.core.constants import INTEGRATION_VERSION


def test_tanium_manager_headers(mocker):
    mocker.patch.object(TaniumManager, "test_connectivity")

    manager = TaniumManager(
        api_token="dummy_token",
        api_root="https://dummy_url",
        verify_ssl=False,
        force_check_connectivity=False,
    )

    assert "x-tanium-integration" in manager.session.headers
    assert (
        manager.session.headers["x-tanium-integration"]
        == f"googlesecops-taniumrest-{INTEGRATION_VERSION}"
    )
