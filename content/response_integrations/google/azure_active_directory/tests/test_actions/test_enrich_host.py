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
from typing import Any
from unittest.mock import MagicMock
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from azure_active_directory.actions.EnrichHost import main
from azure_active_directory.tests.conftest import (
    LegacyActionOutput,
    LegacyJsonResults,
    MockSiemplifyEntity,
)
from azure_active_directory.tests.core.product import AzureADProduct
from azure_active_directory.tests.core.session import AzureADSession

HOSTNAME = "DESKTOP-TEST01"
DEVICE_RAW = {
    "id": "device-id-001",
    "displayName": HOSTNAME,
    "accountEnabled": True,
    "operatingSystem": "Windows",
    "operatingSystemVersion": "10.0.19041",
    "profileType": "RegisteredDevice",
    "isCompliant": True,
    "approximateLastSignInDateTime": "2024-01-15T10:00:00Z",
}


class TestEnrichHost:
    def test_enrich_host_success(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        _action_params: dict[str, Any],
    ) -> None:
        """Test successfully enriching a HOSTNAME entity."""
        product.add_device(HOSTNAME, DEVICE_RAW)
        entity = MockSiemplifyEntity(
            identifier=HOSTNAME, entity_type=EntityTypes.HOSTNAME
        )
        mock_siemplify.target_entities = [entity]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Successfully enriched hosts" in action_output.output_message
        assert HOSTNAME in action_output.output_message
        assert entity.is_enriched is True
        assert "AAD_OS" in entity.additional_properties or any(
            "AAD_" in k for k in entity.additional_properties
        )

    def test_enrich_host_not_found(
        self,
        _product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
    ) -> None:
        """Test enrichment when no device matches the hostname."""
        entity = MockSiemplifyEntity(
            identifier="UNKNOWN-HOST", entity_type=EntityTypes.HOSTNAME
        )
        mock_siemplify.target_entities = [entity]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is False
        assert "No entities were enriched" in action_output.output_message
        assert entity.is_enriched is False

    def test_enrich_host_api_error(
        self,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
    ) -> None:
        """Test that a global API failure surfaces as FAILED status."""
        product.add_device(HOSTNAME, DEVICE_RAW)
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(
                identifier=HOSTNAME, entity_type=EntityTypes.HOSTNAME
            )
        ]

        with product.fail_all_requests():
            main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False

    def test_enrich_host_skips_user_entities(
        self,
        _product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
    ) -> None:
        """Test that USER entities are silently ignored."""
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(
                identifier="user@domain.com", entity_type=EntityTypes.USER
            )
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is False
        assert "No entities were enriched" in action_output.output_message

    def test_enrich_host_disabled_device_skipped(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
    ) -> None:
        """Test that disabled devices are excluded from enrichment results.

        ISSUE FINDER: The manager filters devices by accountEnabled=True, then
        sorts by lastSignIn and picks the last. If ALL matching devices are
        disabled the filtered list is empty, leading to an IndexError on [-1]
        which is caught by the per-entity handler and lands in failed_entities
        rather than giving a user-friendly 'not found' message.
        """
        disabled_device = {**DEVICE_RAW, "accountEnabled": False}
        product.add_device(HOSTNAME, disabled_device)
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(
                identifier=HOSTNAME, entity_type=EntityTypes.HOSTNAME
            )
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is False
        assert "No entities were enriched" in action_output.output_message
