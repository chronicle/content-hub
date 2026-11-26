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
from soar_sdk.SiemplifyDataModel import EntityTypes

from tenable_io.actions.ListEndpointVulnerabilities import main
from tenable_io.tests.conftest import (
    LegacyActionOutput,
    MockSiemplifyEntity,
)
from tenable_io.tests.core.product import TenableIOProduct


class TestHappyPath:
    """Tests for the "List Endpoint Vulnerabilities" action."""

    def test_list_vulnerabilities_success(
        self,
        mock_siemplify: MagicMock,
        tenable_io_product: TenableIOProduct,
        action_output: LegacyActionOutput,
    ) -> None:
        """Test the successful listing of vulnerabilities for an endpoint.

        Verifies that vulnerabilities are correctly retrieved for an asset
        identified by its IP address.

        Args:
            mock_siemplify: The mocked Siemplify API object.
            tenable_io_product: The mocked Tenable.io product instance.
            action_output: The captured action output.
        """
        _ = tenable_io_product
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier="10.0.0.1", entity_type=EntityTypes.ADDRESS)
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Successfully listed vulnerabilities" in action_output.output_message

    def test_list_vulnerabilities_hostname_matching(
        self,
        mock_siemplify: MagicMock,
        tenable_io_product: TenableIOProduct,
        action_output: LegacyActionOutput,
    ) -> None:
        """Test robust hostname matching for vulnerability listing.

        Verifies that vulnerabilities can be listed for an asset identified
        by its FQDN, NetBIOS name, or short hostname.

        Args:
            mock_siemplify: The mocked Siemplify API object.
            tenable_io_product: The mocked Tenable.io product instance.
            action_output: The captured action output.
        """
        _ = tenable_io_product
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(
                identifier="server.domain.local", entity_type=EntityTypes.HOSTNAME
            ),
            MockSiemplifyEntity(
                identifier="SERVER-NB", entity_type=EntityTypes.HOSTNAME
            ),
            MockSiemplifyEntity(identifier="server", entity_type=EntityTypes.HOSTNAME),
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True

        output_message = action_output.output_message
        assert "server.domain.local" in output_message
        assert "SERVER-NB" in output_message
        assert "server" in output_message
