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

from unittest import mock
import unittest

from ..actions import CheckContainmentStatus as check_action_module
from ..actions.CheckContainmentStatus import main
from ..core.SentinelOneManager import (
    SentinelOneAgentNotFoundError,
    SentinelOneManager,
)


class TestSentinelOneManagerNetworkStatus(unittest.TestCase):
    @mock.patch.object(SentinelOneManager, "get_token", return_value="dummy_token")
    def setUp(self, mock_get_token: mock.MagicMock) -> None:
        self.manager = SentinelOneManager("https://test.sentinelone.net", "user", "pass")

    @mock.patch.object(SentinelOneManager, "get_endpoint_system_information")
    def test_get_agent_network_status_snake_case(self, mock_get_info: mock.MagicMock) -> None:
        mock_get_info.return_value = {"network_status": "disconnected"}
        status = self.manager.get_agent_network_status("12345")
        assert status == "disconnected"

    @mock.patch.object(SentinelOneManager, "get_endpoint_system_information")
    def test_get_agent_network_status_camel_case(self, mock_get_info: mock.MagicMock) -> None:
        mock_get_info.return_value = {"networkStatus": "connected"}
        status = self.manager.get_agent_network_status("12345")
        assert status == "connected"

    @mock.patch.object(SentinelOneManager, "get_endpoint_system_information")
    def test_get_agent_network_status_nested_data_dict(self, mock_get_info: mock.MagicMock) -> None:
        mock_get_info.return_value = {"data": {"network_status": "disconnecting"}}
        status = self.manager.get_agent_network_status("12345")
        assert status == "disconnecting"

    @mock.patch.object(SentinelOneManager, "get_endpoint_system_information")
    def test_get_agent_network_status_nested_data_list(self, mock_get_info: mock.MagicMock) -> None:
        mock_get_info.return_value = {"data": [{"networkStatus": "connecting"}]}
        status = self.manager.get_agent_network_status("12345")
        assert status == "connecting"

    @mock.patch.object(SentinelOneManager, "get_endpoint_system_information")
    def test_get_agent_network_status_network_information(self, mock_get_info: mock.MagicMock) -> None:
        mock_get_info.return_value = {"network_information": {"network_status": "disconnected"}}
        status = self.manager.get_agent_network_status("12345")
        assert status == "disconnected"

    @mock.patch.object(SentinelOneManager, "get_endpoint_system_information")
    def test_get_agent_network_status_unknown(self, mock_get_info: mock.MagicMock) -> None:
        mock_get_info.return_value = {"os_name": "linux"}
        status = self.manager.get_agent_network_status("12345")
        assert status == "unknown"


class TestCheckContainmentStatusAction(unittest.TestCase):
    @mock.patch.object(check_action_module, "SentinelOneManager")
    @mock.patch.object(check_action_module, "SiemplifyAction")
    def test_check_containment_status_contained(
        self, mock_siemplify_cls: mock.MagicMock, mock_manager_cls: mock.MagicMock
    ) -> None:
        mock_siemplify = mock_siemplify_cls.return_value
        mock_siemplify.get_configuration.return_value = {
            "Api Root": "https://test.sentinelone.net",
            "Username": "user",
            "Password": "password",
        }
        mock_siemplify.extract_action_param.return_value = "agent-uuid-001"

        mock_manager = mock_manager_cls.return_value
        mock_manager.get_agent_network_status.return_value = "disconnected"

        main()

        mock_manager.get_agent_network_status.assert_called_once_with("agent-uuid-001")
        mock_siemplify.result.add_result_json.assert_called_once_with({
            "endpoint_containment_status": {
                "agent-uuid-001": {
                    "status": "contained",
                    "reason": None,
                }
            }
        })
        mock_siemplify.result.add_data_table.assert_called_once_with(
            "Containment Statuses", ["Property, Value", "agent-uuid-001,contained"]
        )
        mock_siemplify.end.assert_called_once_with("Containment status for agent agent-uuid-001: contained", True)

    @mock.patch.object(check_action_module, "SentinelOneManager")
    @mock.patch.object(check_action_module, "SiemplifyAction")
    def test_check_containment_status_uncontained(
        self, mock_siemplify_cls: mock.MagicMock, mock_manager_cls: mock.MagicMock
    ) -> None:
        mock_siemplify = mock_siemplify_cls.return_value
        mock_siemplify.get_configuration.return_value = {
            "Api Root": "https://test.sentinelone.net",
            "Username": "user",
            "Password": "password",
        }
        mock_siemplify.extract_action_param.return_value = "agent-uuid-002"

        mock_manager = mock_manager_cls.return_value
        mock_manager.get_agent_network_status.return_value = "connected"

        main()

        mock_siemplify.result.add_result_json.assert_called_once_with({
            "endpoint_containment_status": {
                "agent-uuid-002": {
                    "status": "uncontained",
                    "reason": None,
                }
            }
        })
        mock_siemplify.end.assert_called_once_with("Containment status for agent agent-uuid-002: uncontained", True)

    @mock.patch.object(check_action_module, "SentinelOneManager")
    @mock.patch.object(check_action_module, "SiemplifyAction")
    def test_check_containment_status_containment_requested(
        self, mock_siemplify_cls: mock.MagicMock, mock_manager_cls: mock.MagicMock
    ) -> None:
        mock_siemplify = mock_siemplify_cls.return_value
        mock_siemplify.get_configuration.return_value = {
            "Api Root": "https://test.sentinelone.net",
            "Username": "user",
            "Password": "password",
        }
        mock_siemplify.extract_action_param.return_value = "agent-uuid-003"

        mock_manager = mock_manager_cls.return_value
        mock_manager.get_agent_network_status.return_value = "disconnecting"

        main()

        mock_siemplify.result.add_result_json.assert_called_once_with({
            "endpoint_containment_status": {
                "agent-uuid-003": {
                    "status": "containment_requested",
                    "reason": None,
                }
            }
        })
        mock_siemplify.end.assert_called_once_with(
            "Containment status for agent agent-uuid-003: containment_requested", True
        )

    @mock.patch.object(check_action_module, "SentinelOneManager")
    @mock.patch.object(check_action_module, "SiemplifyAction")
    def test_check_containment_status_uncontainment_requested(
        self, mock_siemplify_cls: mock.MagicMock, mock_manager_cls: mock.MagicMock
    ) -> None:
        mock_siemplify = mock_siemplify_cls.return_value
        mock_siemplify.get_configuration.return_value = {
            "Api Root": "https://test.sentinelone.net",
            "Username": "user",
            "Password": "password",
        }
        mock_siemplify.extract_action_param.return_value = "agent-uuid-004"

        mock_manager = mock_manager_cls.return_value
        mock_manager.get_agent_network_status.return_value = "connecting"

        main()

        mock_siemplify.result.add_result_json.assert_called_once_with({
            "endpoint_containment_status": {
                "agent-uuid-004": {
                    "status": "uncontainment_requested",
                    "reason": None,
                }
            }
        })
        mock_siemplify.end.assert_called_once_with(
            "Containment status for agent agent-uuid-004: uncontainment_requested", True
        )

    @mock.patch.object(check_action_module, "SentinelOneManager")
    @mock.patch.object(check_action_module, "SiemplifyAction")
    def test_check_containment_status_unknown_status(
        self, mock_siemplify_cls: mock.MagicMock, mock_manager_cls: mock.MagicMock
    ) -> None:
        mock_siemplify = mock_siemplify_cls.return_value
        mock_siemplify.get_configuration.return_value = {
            "Api Root": "https://test.sentinelone.net",
            "Username": "user",
            "Password": "password",
        }
        mock_siemplify.extract_action_param.return_value = "agent-uuid-005"

        mock_manager = mock_manager_cls.return_value
        mock_manager.get_agent_network_status.return_value = "some_random_status"

        main()

        mock_siemplify.result.add_result_json.assert_called_once_with({
            "endpoint_containment_status": {
                "agent-uuid-005": {
                    "status": "unknown",
                    "reason": None,
                }
            }
        })
        mock_siemplify.end.assert_called_once_with(
            "Could not determine containment status for agent agent-uuid-005 (raw status: some_random_status).",
            False,
        )

    @mock.patch.object(check_action_module, "SentinelOneManager")
    @mock.patch.object(check_action_module, "SiemplifyAction")
    def test_check_containment_status_agent_not_found(
        self, mock_siemplify_cls: mock.MagicMock, mock_manager_cls: mock.MagicMock
    ) -> None:
        mock_siemplify = mock_siemplify_cls.return_value
        mock_siemplify.get_configuration.return_value = {
            "Api Root": "https://test.sentinelone.net",
            "Username": "user",
            "Password": "password",
        }
        mock_siemplify.extract_action_param.return_value = "nonexistent-agent"

        mock_manager = mock_manager_cls.return_value
        mock_manager.get_agent_network_status.side_effect = SentinelOneAgentNotFoundError("Agent not found")

        main()

        mock_siemplify.result.add_result_json.assert_called_once_with({
            "endpoint_containment_status": {
                "nonexistent-agent": {
                    "status": "unknown",
                    "reason": "Agent not found",
                }
            }
        })
        mock_siemplify.result.add_data_table.assert_called_once_with(
            "Unsuccessful Attempts", ["Property, Value", "nonexistent-agent,Agent not found"]
        )
        mock_siemplify.end.assert_called_once_with(
            "Error executing action 'Check Containment Status'. Reason: Agent not found",
            False,
        )


if __name__ == "__main__":
    unittest.main()
