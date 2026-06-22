from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from actions.AddObjectToContainer import (
    SCRIPT_NAME,
    AddObjectToContainer,
    AddObjectToContainerParameters,
)


class TestAddObjectToContainerParameters:
    @pytest.mark.parametrize(
        "raw_value",
        [
            "Report",
            "Incident Response Case",
            "Request for Information",
            "Request for Takedown",
            "Grouping",
        ],
    )
    def test_accept_container_type(self, raw_value):
        params = AddObjectToContainerParameters(
            container_type=raw_value,
            container_id="container-1",
            object_id="object-1",
        )

        assert params.container_type == raw_value

    def test_raise_on_unsupported_container_type(self):
        with pytest.raises(ValueError):
            AddObjectToContainerParameters(
                container_type="Campaign",
                container_id="container-1",
                object_id="object-1",
            )


class TestAddObjectToContainerAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "Container Type": "Request for Takedown",
            "Container Id": "container-1",
            "Object Id": "object-1",
        }
        result_mock = MagicMock()
        result_mock.json.return_value = {}

        action = AddObjectToContainer(SCRIPT_NAME)
        action._api_client = action._init_api_clients()
        action._api_client.add_object_to_container.return_value = result_mock
        action._validate_params()

        assert action.params.container_type == "Request for Takedown"
        assert action.params.container_id == "container-1"
        assert action.params.object_id == "object-1"

    def test_perform_action_calls_client_with_normalized_type(self, mock_soar_action, mock_api_client):
        mock_soar_action.parameters = {
            "Container Type": "Request for Takedown",
            "Container Id": "container-1",
            "Object Id": "object-1",
        }
        result_mock = MagicMock()
        result_mock.json.return_value = {}
        mock_api_client.add_object_to_container.return_value = result_mock

        action = AddObjectToContainer(SCRIPT_NAME)
        action.run()

        mock_api_client.add_object_to_container.assert_called_once_with(
            container_type="Case-Rft",
            container_id="container-1",
            object_id="object-1",
        )
