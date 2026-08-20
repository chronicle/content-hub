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
import pytest
from unittest.mock import MagicMock, patch

from ..actions import CheckContainmentStatus
from ..core.datamodels import Agent
from ..core.exceptions import (
    SentinelOneNotFoundError,
)

EXECUTION_STATE_COMPLETED = 0
EXECUTION_STATE_FAILED = 1


@pytest.fixture
def mock_siemplify():
    siemplify = MagicMock()
    siemplify.script_name = "Check Containment Status"
    siemplify.target_entities = []
    siemplify.parameters = {}
    siemplify.result = MagicMock()
    siemplify.LOGGER = MagicMock()
    return siemplify


class TestCheckContainmentStatusAction:
    def test_check_status_contained_success(self, mock_siemplify):
        mock_mgr = MagicMock()
        agent = Agent(id="12345", uuid="uuid-123", network_status="disconnected", computer_name="HOST1")
        mock_mgr.get_agent_by_uuid.return_value = agent
        mock_mgr.get_containment_status.return_value = "contained"

        def mock_extract(siemplify, param_name, **kwargs):
            return {
                "Agent ID": "uuid-123",
                "Agent UUID": None,
            }.get(param_name, kwargs.get("default_value"))

        with patch.object(CheckContainmentStatus, "SiemplifyAction", return_value=mock_siemplify), \
             patch.object(CheckContainmentStatus, "get_manager", return_value=mock_mgr), \
             patch.object(CheckContainmentStatus, "extract_action_param", side_effect=mock_extract), \
             patch.object(CheckContainmentStatus, "extract_configuration_param"):

            CheckContainmentStatus.main()

        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "Status: contained" in args[0]
        assert args[1] is True
        assert args[2] == EXECUTION_STATE_COMPLETED

    def test_check_status_uncontained_success(self, mock_siemplify):
        mock_mgr = MagicMock()
        agent = Agent(id="12345", uuid="uuid-123", network_status="connected", computer_name="HOST1")
        mock_mgr.get_agent_by_uuid.return_value = agent
        mock_mgr.get_containment_status.return_value = "uncontained"

        def mock_extract(siemplify, param_name, **kwargs):
            return {
                "Agent ID": "uuid-123",
                "Agent UUID": None,
            }.get(param_name, kwargs.get("default_value"))

        with patch.object(CheckContainmentStatus, "SiemplifyAction", return_value=mock_siemplify), \
             patch.object(CheckContainmentStatus, "get_manager", return_value=mock_mgr), \
             patch.object(CheckContainmentStatus, "extract_action_param", side_effect=mock_extract), \
             patch.object(CheckContainmentStatus, "extract_configuration_param"):

            CheckContainmentStatus.main()

        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "Status: uncontained" in args[0]
        assert args[1] is True
        assert args[2] == EXECUTION_STATE_COMPLETED

    def test_agent_not_found(self, mock_siemplify):
        mock_mgr = MagicMock()
        mock_mgr.get_agent_by_uuid.side_effect = SentinelOneNotFoundError("Not found")

        def mock_extract(siemplify, param_name, **kwargs):
            return {
                "Agent ID": "nonexistent-uuid",
                "Agent UUID": None,
            }.get(param_name, kwargs.get("default_value"))

        with patch.object(CheckContainmentStatus, "SiemplifyAction", return_value=mock_siemplify), \
             patch.object(CheckContainmentStatus, "get_manager", return_value=mock_mgr), \
             patch.object(CheckContainmentStatus, "extract_action_param", side_effect=mock_extract), \
             patch.object(CheckContainmentStatus, "extract_configuration_param"):

            CheckContainmentStatus.main()

        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "Could not find endpoint" in args[0]
        assert args[1] is False
        assert args[2] == EXECUTION_STATE_FAILED

    def test_entity_fallback_success(self, mock_siemplify):
        mock_mgr = MagicMock()
        agent = Agent(id="12345", uuid="host-entity-id", network_status="connected", computer_name="HOST1")
        mock_mgr.get_agent_by_uuid.return_value = agent
        mock_mgr.get_containment_status.return_value = "uncontained"

        mock_entity = MagicMock()
        mock_entity.entity_type = "HOSTNAME"
        mock_entity.identifier = "host-entity-id"
        mock_siemplify.target_entities = [mock_entity]

        def mock_extract(siemplify, param_name, **kwargs):
            return kwargs.get("default_value")

        with patch.object(CheckContainmentStatus, "SiemplifyAction", return_value=mock_siemplify), \
             patch.object(CheckContainmentStatus, "get_manager", return_value=mock_mgr), \
             patch.object(CheckContainmentStatus, "extract_action_param", side_effect=mock_extract), \
             patch.object(CheckContainmentStatus, "extract_configuration_param"):

            CheckContainmentStatus.main()

        mock_mgr.get_agent_by_uuid.assert_called_once_with("host-entity-id")
        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "Status: uncontained" in args[0]
        assert args[1] is True
        assert args[2] == EXECUTION_STATE_COMPLETED

    def test_generic_exception(self, mock_siemplify):
        mock_mgr = MagicMock()
        mock_mgr.get_agent_by_uuid.side_effect = RuntimeError("API connection exploded")

        def mock_extract(siemplify, param_name, **kwargs):
            return {
                "Agent ID": "uuid-123",
                "Agent UUID": None,
            }.get(param_name, kwargs.get("default_value"))

        with patch.object(CheckContainmentStatus, "SiemplifyAction", return_value=mock_siemplify), \
             patch.object(CheckContainmentStatus, "get_manager", return_value=mock_mgr), \
             patch.object(CheckContainmentStatus, "extract_action_param", side_effect=mock_extract), \
             patch.object(CheckContainmentStatus, "extract_configuration_param"):

            CheckContainmentStatus.main()

        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "Error executing action" in args[0]
        assert args[1] is False
        assert args[2] == EXECUTION_STATE_FAILED
