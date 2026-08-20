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

from ..actions import UncontainEndpoint
from ..core.datamodels import Agent
from ..core.exceptions import (
    SentinelOneNotFoundError,
    SentinelOneTimeoutException,
)

EXECUTION_STATE_COMPLETED = 0
EXECUTION_STATE_FAILED = 1
EXECUTION_STATE_INPROGRESS = 2
EXECUTION_STATE_TIMEDOUT = 3


@pytest.fixture
def mock_siemplify():
    siemplify = MagicMock()
    siemplify.script_name = "Uncontain Endpoint"
    siemplify.execution_deadline_unix_time_ms = 9999999999999
    siemplify.target_entities = []
    siemplify.parameters = {}
    siemplify.result = MagicMock()
    siemplify.LOGGER = MagicMock()
    return siemplify


class TestUncontainEndpointAction:
    def test_first_run_initiate_uncontainment_success(self, mock_siemplify):
        mock_mgr = MagicMock()
        agent = Agent(id="12345", uuid="uuid-123", network_status="disconnected", computer_name="HOST1")
        mock_mgr.get_agent_by_uuid.return_value = agent
        mock_mgr.get_containment_status.return_value = "contained"
        mock_mgr.connect_agent_to_network.return_value = True

        def mock_extract(siemplify, param_name, **kwargs):
            return {
                "Fail If Timeout": False,
                "Agent ID": "uuid-123",
                "Agent UUID": None,
            }.get(param_name, kwargs.get("default_value"))

        with patch.object(UncontainEndpoint, "SiemplifyAction", return_value=mock_siemplify), \
             patch.object(UncontainEndpoint, "get_manager", return_value=mock_mgr), \
             patch.object(UncontainEndpoint, "extract_action_param", side_effect=mock_extract), \
             patch.object(UncontainEndpoint, "extract_configuration_param"):

            UncontainEndpoint.main(is_first_run=True)

        mock_mgr.connect_agent_to_network.assert_called_once_with("12345")
        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "Uncontainment initiated" in args[0]
        assert args[1] is True
        assert args[2] == EXECUTION_STATE_INPROGRESS

    def test_first_run_already_uncontained(self, mock_siemplify):
        mock_mgr = MagicMock()
        agent = Agent(id="12345", uuid="uuid-123", network_status="connected", computer_name="HOST1")
        mock_mgr.get_agent_by_uuid.return_value = agent
        mock_mgr.get_containment_status.return_value = "uncontained"

        def mock_extract(siemplify, param_name, **kwargs):
            return {
                "Fail If Timeout": False,
                "Agent ID": "uuid-123",
                "Agent UUID": None,
            }.get(param_name, kwargs.get("default_value"))

        with patch.object(UncontainEndpoint, "SiemplifyAction", return_value=mock_siemplify), \
             patch.object(UncontainEndpoint, "get_manager", return_value=mock_mgr), \
             patch.object(UncontainEndpoint, "extract_action_param", side_effect=mock_extract), \
             patch.object(UncontainEndpoint, "extract_configuration_param"):

            UncontainEndpoint.main(is_first_run=True)

        mock_mgr.connect_agent_to_network.assert_not_called()
        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "already uncontained" in args[0]
        assert args[1] is True
        assert args[2] == EXECUTION_STATE_COMPLETED

    def test_polling_run_now_uncontained(self, mock_siemplify):
        mock_mgr = MagicMock()
        agent = Agent(id="12345", uuid="uuid-123", network_status="connected", computer_name="HOST1")
        mock_mgr.get_agent_by_uuid.return_value = agent
        mock_mgr.get_containment_status.return_value = "uncontained"

        def mock_extract(siemplify, param_name, **kwargs):
            return {
                "Fail If Timeout": False,
                "Agent ID": "uuid-123",
                "Agent UUID": None,
            }.get(param_name, kwargs.get("default_value"))

        with patch.object(UncontainEndpoint, "SiemplifyAction", return_value=mock_siemplify), \
             patch.object(UncontainEndpoint, "get_manager", return_value=mock_mgr), \
             patch.object(UncontainEndpoint, "extract_action_param", side_effect=mock_extract), \
             patch.object(UncontainEndpoint, "extract_configuration_param"):

            UncontainEndpoint.main(is_first_run=False)

        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "Successfully uncontained" in args[0]
        assert args[1] is True
        assert args[2] == EXECUTION_STATE_COMPLETED
