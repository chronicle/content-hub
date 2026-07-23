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

import json
from unittest.mock import MagicMock

from soar_sdk.SiemplifyDataModel import EntityTypes

from ..actions.LookupEntity import main

from ..tests.conftest import LegacyActionOutput, LegacyJsonResults


def create_mock_entity(identifier: str, entity_type: str) -> MagicMock:
    """Local factory for creating mock entities."""
    entity = MagicMock()
    entity.identifier = identifier
    entity.entity_type = entity_type
    entity.is_internal = False
    return entity


class TestLookupEntity:
    """
    Tests the happy path for the LookupEntity action.
    """

    def test_lookup_domain_success(
        self,
        mock_siemplify: MagicMock,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_data: dict,
    ) -> None:
        """
        Tests the successful lookup of a Domain entity.
        """

        mock_siemplify.target_entities = [
            create_mock_entity("dhnconstrucciones.com.ar", EntityTypes.DOMAIN)
        ]

        main()

        assert action_output.is_success is True
        assert "found in Zscaler" in action_output.output_message
        assert "dhnconstrucciones.com.ar" in action_output.output_message

        expected_json: dict = mock_data["url_lookup_success"][0]

        result_json_dict: dict = json.loads(json_results.json_results_str)[0]

        assert "EntityResult" in result_json_dict
        assert result_json_dict["EntityResult"]["url"] == expected_json["url"]
        assert (
            result_json_dict["EntityResult"]["urlClassificationsWithSecurityAlert"]
            == (expected_json["urlClassificationsWithSecurityAlert"])
        )
