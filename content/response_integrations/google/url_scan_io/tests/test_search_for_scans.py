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

from unittest.mock import MagicMock
from soar_sdk.SiemplifyDataModel import EntityTypes
from url_scan_io.actions import SearchForScans
from url_scan_io.tests.conftest import LegacyActionOutput, LegacyJsonResults
from url_scan_io.tests.core.url_scan_io import UrlScanIo


def create_mock_entity(
    identifier: str,
    entity_type: str
) -> MagicMock:
    """Local factory for creating mock entities."""
    entity = MagicMock()
    entity.identifier = identifier
    entity.entity_type = entity_type
    entity.is_internal = False
    entity.additional_properties = {}
    return entity


class TestSearchForScans:
    """
    Tests the SearchForScans action.
    """

    def test_search_scans_domain_success(
        self,
        mock_siemplify: MagicMock,
        url_scan_product: UrlScanIo,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_data: dict,
    ) -> None:
        """
        Tests that a DOMAIN entity is correctly processed and scans are found.
        """
        # Arrange
        domain = "google.com"
        mock_siemplify.target_entities = [
            create_mock_entity(domain, EntityTypes.DOMAIN)
        ]

        # Populate the mock product with data matching the domain
        scan_data = mock_data["search_results"]["results"][0]
        url_scan_product.add_scan(scan_data)

        # Act
        SearchForScans.main()

        # Assert
        assert action_output.is_success is True
        assert_message = "Successfully listed scans for the following entities:"
        assert f"{assert_message}\n {domain}" in action_output.output_message

        # Verify JSON results
        assert any(
            result_item["Entity"] == domain
            for result_item in json_results.json_results
        )
        # We also need to get the actual results for the domain from the json_results
        actual_results_for_domain = next(
            item["EntityResult"] for item in json_results.json_results
            if item["Entity"] == domain
        )
        assert len(actual_results_for_domain) == 1
        assert actual_results_for_domain[0]["task"]["domain"] == domain

    def test_search_scans_no_suitable_entities(
        self,
        mock_siemplify: MagicMock,
        action_output: LegacyActionOutput,
    ) -> None:
        """Tests behavior when no suitable entities are provided."""
        # Arrange
        mock_siemplify.target_entities = [
            create_mock_entity("user", EntityTypes.USER)
        ]

        # Act
        SearchForScans.main()

        # Assert
        assert action_output.is_success is False
        assert "No suitable entities were found" in action_output.output_message
