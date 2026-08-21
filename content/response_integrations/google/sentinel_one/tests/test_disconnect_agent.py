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

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from soar_sdk.SiemplifyDataModel import EntityTypes

from sentinel_one.actions import DisconnectAgentFromNetwork
from sentinel_one.core.SentinelOneManager import SentinelOneAgentNotFoundError


@dataclass
class MockEntity:
    identifier: str
    entity_type: str


@patch("sentinel_one.actions.DisconnectAgentFromNetwork.SiemplifyAction")
@patch("sentinel_one.actions.DisconnectAgentFromNetwork.SentinelOneManager")
def test_disconnect_direct_agent_id_success(
    mock_manager_cls: MagicMock, mock_siemplify_cls: MagicMock
) -> None:
    mock_siemplify = mock_siemplify_cls.return_value
    mock_siemplify.get_configuration.return_value = {
        "Api Root": "https://example.sentinelone.net",
        "Username": "user",
        "Password": "pwd",
    }
    mock_siemplify.parameters = {"Agent ID": "agent-12345"}
    mock_siemplify.target_entities = []

    mock_manager = mock_manager_cls.return_value
    mock_manager.disconnect_agent_from_network.return_value = True

    DisconnectAgentFromNetwork.main()

    mock_manager.disconnect_agent_from_network.assert_called_once_with("agent-12345")
    mock_manager.find_endpoint_agent_id.assert_not_called()
    mock_siemplify.end.assert_called_once_with(
        "Agent agent-12345 was disconnected from the network.", True
    )


@patch("sentinel_one.actions.DisconnectAgentFromNetwork.SiemplifyAction")
@patch("sentinel_one.actions.DisconnectAgentFromNetwork.SentinelOneManager")
def test_disconnect_direct_agent_id_with_whitespace_and_bypass_entities(
    mock_manager_cls: MagicMock, mock_siemplify_cls: MagicMock
) -> None:
    mock_siemplify = mock_siemplify_cls.return_value
    mock_siemplify.get_configuration.return_value = {
        "Api Root": "https://example.sentinelone.net",
        "Username": "user",
        "Password": "pwd",
    }
    mock_siemplify.parameters = {"Agent ID": "  agent-12345  "}
    mock_siemplify.target_entities = [
        MockEntity("192.168.1.10", EntityTypes.ADDRESS),
        MockEntity("workstation-01", EntityTypes.HOSTNAME),
    ]

    mock_manager = mock_manager_cls.return_value
    mock_manager.disconnect_agent_from_network.return_value = True

    DisconnectAgentFromNetwork.main()

    mock_manager.disconnect_agent_from_network.assert_called_once_with("agent-12345")
    mock_manager.find_endpoint_agent_id.assert_not_called()
    mock_siemplify.end.assert_called_once_with(
        "Agent agent-12345 was disconnected from the network.", True
    )


@patch("sentinel_one.actions.DisconnectAgentFromNetwork.SiemplifyAction")
@patch("sentinel_one.actions.DisconnectAgentFromNetwork.SentinelOneManager")
def test_disconnect_direct_agent_id_failure(
    mock_manager_cls: MagicMock, mock_siemplify_cls: MagicMock
) -> None:
    mock_siemplify = mock_siemplify_cls.return_value
    mock_siemplify.get_configuration.return_value = {
        "Api Root": "https://example.sentinelone.net",
        "Username": "user",
        "Password": "pwd",
    }
    mock_siemplify.parameters = {"Agent ID": "agent-12345"}
    mock_siemplify.target_entities = []

    mock_manager = mock_manager_cls.return_value
    mock_manager.disconnect_agent_from_network.return_value = False

    DisconnectAgentFromNetwork.main()

    mock_manager.disconnect_agent_from_network.assert_called_once_with("agent-12345")
    mock_siemplify.end.assert_called_once_with(
        "Failed to disconnect agent agent-12345 from the network.", False
    )


@patch("sentinel_one.actions.DisconnectAgentFromNetwork.SiemplifyAction")
@patch("sentinel_one.actions.DisconnectAgentFromNetwork.SentinelOneManager")
def test_disconnect_fallback_entity_success(
    mock_manager_cls: MagicMock, mock_siemplify_cls: MagicMock
) -> None:
    mock_siemplify = mock_siemplify_cls.return_value
    mock_siemplify.get_configuration.return_value = {
        "Api Root": "https://example.sentinelone.net",
        "Username": "user",
        "Password": "pwd",
    }
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [
        MockEntity("192.168.1.10", EntityTypes.ADDRESS),
        MockEntity("workstation-01", EntityTypes.HOSTNAME),
    ]

    mock_manager = mock_manager_cls.return_value
    mock_manager.find_endpoint_agent_id.side_effect = ["id-1", "id-2"]
    mock_manager.disconnect_agent_from_network.return_value = True

    DisconnectAgentFromNetwork.main()

    assert mock_manager.find_endpoint_agent_id.call_count == 2
    mock_manager.find_endpoint_agent_id.assert_any_call(
        "192.168.1.10", by_ip_address=True
    )
    mock_manager.find_endpoint_agent_id.assert_any_call("workstation-01")
    assert mock_manager.disconnect_agent_from_network.call_count == 2
    mock_siemplify.end.assert_called_once_with(
        "The following entities were disconnected from the network: 192.168.1.10,workstation-01",
        True,
    )


@patch("sentinel_one.actions.DisconnectAgentFromNetwork.SiemplifyAction")
@patch("sentinel_one.actions.DisconnectAgentFromNetwork.SentinelOneManager")
def test_disconnect_fallback_entity_partial_failure(
    mock_manager_cls: MagicMock, mock_siemplify_cls: MagicMock
) -> None:
    mock_siemplify = mock_siemplify_cls.return_value
    mock_siemplify.get_configuration.return_value = {
        "Api Root": "https://example.sentinelone.net",
        "Username": "user",
        "Password": "pwd",
    }
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [
        MockEntity("192.168.1.10", EntityTypes.ADDRESS),
        MockEntity("unknown-host", EntityTypes.HOSTNAME),
    ]

    mock_manager = mock_manager_cls.return_value
    mock_manager.find_endpoint_agent_id.side_effect = [
        "id-1",
        SentinelOneAgentNotFoundError("Agent not found"),
    ]
    mock_manager.disconnect_agent_from_network.return_value = True

    DisconnectAgentFromNetwork.main()

    assert mock_manager.find_endpoint_agent_id.call_count == 2
    mock_manager.find_endpoint_agent_id.assert_any_call(
        "192.168.1.10", by_ip_address=True
    )
    mock_manager.find_endpoint_agent_id.assert_any_call("unknown-host")
    mock_manager.disconnect_agent_from_network.assert_called_once_with("id-1")
    mock_siemplify.result.add_data_table.assert_called_once()
    mock_siemplify.end.assert_called_once_with(
        "The following entities were disconnected from the network: 192.168.1.10",
        True,
    )


@patch("sentinel_one.actions.DisconnectAgentFromNetwork.SiemplifyAction")
@patch("sentinel_one.actions.DisconnectAgentFromNetwork.SentinelOneManager")
def test_disconnect_fallback_entity_not_found(
    mock_manager_cls: MagicMock, mock_siemplify_cls: MagicMock
) -> None:
    mock_siemplify = mock_siemplify_cls.return_value
    mock_siemplify.get_configuration.return_value = {
        "Api Root": "https://example.sentinelone.net",
        "Username": "user",
        "Password": "pwd",
    }
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [MockEntity("unknown-host", EntityTypes.HOSTNAME)]

    mock_manager = mock_manager_cls.return_value
    mock_manager.find_endpoint_agent_id.side_effect = SentinelOneAgentNotFoundError(
        "Agent not found"
    )

    DisconnectAgentFromNetwork.main()

    mock_siemplify.result.add_data_table.assert_called_once()
    mock_siemplify.end.assert_called_once_with(
        "No target entities were disconnected from the network.", False
    )


@patch("sentinel_one.actions.DisconnectAgentFromNetwork.SiemplifyAction")
@patch("sentinel_one.actions.DisconnectAgentFromNetwork.SentinelOneManager")
def test_disconnect_fallback_whitespace_param_no_matching_entities(
    mock_manager_cls: MagicMock, mock_siemplify_cls: MagicMock
) -> None:
    mock_siemplify = mock_siemplify_cls.return_value
    mock_siemplify.get_configuration.return_value = {
        "Api Root": "https://example.sentinelone.net",
        "Username": "user",
        "Password": "pwd",
    }
    mock_siemplify.parameters = {"Agent ID": "   "}
    mock_siemplify.target_entities = [
        MockEntity("admin@domain.com", EntityTypes.USER),
    ]

    mock_manager = mock_manager_cls.return_value

    DisconnectAgentFromNetwork.main()

    mock_manager.find_endpoint_agent_id.assert_not_called()
    mock_manager.disconnect_agent_from_network.assert_not_called()
    mock_siemplify.end.assert_called_once_with(
        "No target entities were disconnected from the network.", False
    )
