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

from unittest.mock import MagicMock

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from url_scan_io.actions import GetScanFullDetails

from ..common import LegacyActionOutput, LegacyJsonResults
from ..core.url_scan_io import UrlScanIo


def test_get_scan_full_details_success(
    mock_siemplify: MagicMock,
    url_scan_product: UrlScanIo,
    action_output: LegacyActionOutput,
    json_results: LegacyJsonResults,
) -> None:
    """Tests that GetScanFullDetails fetches scan details, links, and screenshot."""
    scan_uuid = "8baedb2c-040c-4b89-ba3f-xxxx"
    url_scan_product.add_scan(
        {
            "task": {
                "uuid": scan_uuid,
                "reportURL": f"https://urlscan.io/result/{scan_uuid}/",
                "domURL": f"https://urlscan.io/dom/{scan_uuid}/",
                "screenshotURL": f"https://urlscan.io/screenshots/{scan_uuid}.png",
            },
            "page": {"url": "https://google.com"},
        }
    )
    mock_siemplify.action_params = {"Scan ID": scan_uuid}

    GetScanFullDetails.main()

    assert action_output.status == EXECUTION_STATE_COMPLETED
    assert action_output.is_success is True
    assert scan_uuid in (action_output.output_message or "")
    assert len(json_results.json_results) == 1
    assert json_results.json_results[0]["task"]["uuid"] == scan_uuid


def test_get_scan_full_details_not_found(
    mock_siemplify: MagicMock,
    action_output: LegacyActionOutput,
) -> None:
    """Tests that GetScanFullDetails handles missing scan IDs gracefully."""
    mock_siemplify.action_params = {"Scan ID": "non-existent-scan-id"}

    GetScanFullDetails.main()

    assert action_output.status == EXECUTION_STATE_COMPLETED
    assert action_output.is_success is False
    assert "not available" in (action_output.output_message or "")
