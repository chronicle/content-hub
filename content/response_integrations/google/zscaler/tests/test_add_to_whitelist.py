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
from unittest.mock import MagicMock
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..actions.AddToWhitelist import AddToWhitelistAction
from ..tests.conftest import LegacyActionOutput
from ..tests.core.zscaler import Zscaler


def create_mock_entity(identifier: str, entity_type: str) -> MagicMock:
    """Local factory for creating mock entities."""
    entity = MagicMock()
    entity.identifier = identifier
    entity.entity_type = entity_type
    entity.is_internal = False
    return entity


class TestHappyPath:
    """
    Tests the happy path for the AddToWhitelist action.
    """

    def test_add_domain_to_whitelist_success(
        self,
        mock_siemplify: MagicMock,
        zscaler_product: Zscaler,
        action_output: LegacyActionOutput,
    ) -> None:
        """
        Tests the successful addition of a Domain to the whitelist.
        """

        mock_siemplify.target_entities = [
            create_mock_entity("dhnconstrucciones.com.ar", EntityTypes.DOMAIN)
        ]
        mock_siemplify.parameters = {}
        assert zscaler_product.whitelist_urls == []

        action = AddToWhitelistAction()
        action.run()

        assert zscaler_product.whitelist_urls == ["dhnconstrucciones.com.ar"]

        assert action_output.is_success is True
        assert (
            "Added the following entities to the Urls whitelist successfully"
            in action_output.output_message
        )
        assert "dhnconstrucciones.com.ar" in action_output.output_message

    def test_add_explicit_parameters_to_whitelist_success(
        self,
        mock_siemplify: MagicMock,
        zscaler_product: Zscaler,
        action_output: LegacyActionOutput,
    ) -> None:
        """
        Tests adding via explicit parameters.
        """
        def mock_extract_action_param(param_name, _print_value=False, **_kwargs):
            if param_name == "IOCs":
                return (
                    "5.5.5.5, 6.6.6.6, http://good-url.com, "
                    "https://safe.com/login, safe-domain.com, trusted.org"
                )
            return ""

        mock_siemplify.extract_action_param.side_effect = mock_extract_action_param
        action = AddToWhitelistAction()
        action.run()

        expected_results = [
            "5.5.5.5",
            "6.6.6.6",
            "good-url.com",
            "safe.com",
            "safe-domain.com",
            "trusted.org"
        ]
        actual_results = zscaler_product.whitelist_urls
        for expected in expected_results:
            assert expected in actual_results

        assert len(actual_results) == len(expected_results)

        assert action_output.is_success is True
        assert (
            "Added the following entities to the Urls whitelist successfully"
            in action_output.output_message
        )
        for expected in expected_results:
            assert expected in action_output.output_message
