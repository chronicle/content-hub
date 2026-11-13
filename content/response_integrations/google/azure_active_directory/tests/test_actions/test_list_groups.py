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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED

from azure_active_directory.actions.ListGroups import main
from azure_active_directory.tests.conftest import (
    LegacyActionOutput,
    LegacyJsonResults,
    MOCK_RESPONSES,
)
from azure_active_directory.tests.core.product import AzureADProduct
from azure_active_directory.tests.core.session import AzureADSession

MOCK_GROUP = MOCK_RESPONSES["processed_group_1"]
MOCK_GROUP_2 = MOCK_RESPONSES["processed_group_2"]


class TestListGroups:
    def test_success(
        self,
        script_session: AzureADSession,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
    ):
        raw_group_1 = MOCK_RESPONSES["raw_group_api_response_1"]["value"][0]
        product.add_group(MOCK_GROUP["id"], raw_group_1)

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "List of groups fetched successfully." in action_output.output_message

        assert len(json_results.json_results) == 1
        result = json_results.json_results[0]

        assert result["Name"] == MOCK_GROUP["displayName"]
        assert result["Id"] == MOCK_GROUP["id"]
        assert (
            result["onPremisesSamAccountName"]
            == MOCK_GROUP["onPremisesSamAccountName"]
        )
        assert script_session.get.call_count == 2
        assert mock_siemplify.result.add_data_table.called

    def test_no_groups_found(
        self,
        script_session: AzureADSession,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
    ):
        assert not product.groups

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is False
        assert (
            "No groups were returned based on provided filter criteria"
            in action_output.output_message
        )

        assert script_session.get.call_count == 2
        assert not json_results.json_results
        assert not mock_siemplify.result.add_data_table.called

    def test_limit(
        self,
        script_session: AzureADSession,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ):
        raw_group_1 = MOCK_RESPONSES["raw_group_api_response_1"]["value"][0]
        raw_group_2 = MOCK_RESPONSES["raw_group_api_response_2"]["value"][0]
        product.add_group(MOCK_GROUP["id"], raw_group_1)
        product.add_group(MOCK_GROUP_2["id"], raw_group_2)
        action_params["Results Limit"] = 1

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "List of groups fetched successfully." in action_output.output_message
        assert script_session.get.call_count == 2

        assert len(json_results.json_results) == 1
        assert mock_siemplify.result.add_data_table.called
