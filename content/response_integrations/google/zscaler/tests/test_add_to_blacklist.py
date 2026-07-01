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
from ..actions.AddToBlacklist import AddToBlacklistAction
from ..tests.conftest import LegacyActionOutput
from ..tests.core.zscaler import Zscaler


def create_mock_entity(identifier: str, entity_type: str) -> MagicMock:
    """Local factory for creating mock entities."""
    entity = MagicMock()
    entity.identifier = identifier
    entity.entity_type = entity_type
    entity.is_internal = False
    return entity


class TestAddToBlacklist:
    """
    Tests the AddToBlacklist action.
    """

    def test_add_entities_to_blacklist_success(
        self,
        mock_siemplify: MagicMock,
        zscaler_product: Zscaler,
        action_output: LegacyActionOutput,
    ) -> None:
        """
        Tests adding via Target Entities.
        """
        mock_siemplify.target_entities = [
            create_mock_entity("target-entity-domain.com", EntityTypes.DOMAIN),
            create_mock_entity("8.8.8.8", EntityTypes.ADDRESS),
        ]
        mock_siemplify.parameters = {}

        assert zscaler_product.blacklist_urls == []

        action = AddToBlacklistAction()
        action.run()

        expected_results = ["target-entity-domain.com", "8.8.8.8"]

        actual_results = zscaler_product.blacklist_urls
        for expected in expected_results:
            assert expected in actual_results

        assert len(actual_results) == len(expected_results)

        assert action_output.is_success is True
        assert (
            "Added the following entities to the Urls blacklist successfully"
            in action_output.output_message
        )
        for expected in expected_results:
            assert expected in action_output.output_message

    def test_add_entities_and_parameters_to_blacklist(
        self,
        mock_siemplify: MagicMock,
        zscaler_product: Zscaler,
        action_output: LegacyActionOutput,
    ) -> None:
        """
        Tests adding via both Target Entities and explicit parameters.
        """
        mock_siemplify.target_entities = [
            create_mock_entity("target-entity-domain.com", EntityTypes.DOMAIN),
            create_mock_entity("8.8.8.8", EntityTypes.ADDRESS)
        ]
        def mock_extract_action_param(param_name, _print_value=False, **_kwargs):
            if param_name == "IOCs":
                return (
                    "1.1.1.1, 2.2.2.2, http://evil-url.com, "
                    "https://phishing.com/login  , bad-domain.com, "
                    "another-domain.org"
                )
            return ""

        mock_siemplify.extract_action_param.side_effect = mock_extract_action_param

        assert zscaler_product.blacklist_urls == []

        action = AddToBlacklistAction()
        action.run()

        expected_results = [
            "target-entity-domain.com",
            "8.8.8.8",
            "1.1.1.1",
            "2.2.2.2",
            "evil-url.com",
            "phishing.com",
            "bad-domain.com",
            "another-domain.org"
        ]
        actual_results = zscaler_product.blacklist_urls
        for expected in expected_results:
            assert expected in actual_results

        assert len(actual_results) == len(expected_results)

        assert action_output.is_success is True
        assert (
            "Added the following entities to the Urls blacklist successfully"
            in action_output.output_message
        )
        for expected in expected_results:
            assert expected in action_output.output_message
