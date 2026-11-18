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

import json
from unittest.mock import MagicMock


class MockSiemplifyEntity:
    def __init__(self, identifier, entity_type):
        self.identifier = identifier
        self.entity_type = entity_type


def create_mock_response(json_data, status_code=200):
    """Create a MagicMock response object."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.content = json.dumps(json_data).encode("utf-8")
    response.raise_for_status.return_value = None
    return response


def run_action_with_parameters(mocker, module_name, parameters, config, siemplify_attributes=None):
    """Runs an action's main() with a mocked Siemplify and returns the mock.

    The HTTP layer is served by the autouse `script_session` fixture.

    Args:
        mocker: The pytest-mock fixture.
        module_name: Name of the module in `microsoft_teams.actions`.
        parameters: The action parameters.
        config: The integration configuration keyed by parameter name.
        siemplify_attributes: Optional attributes to set on the mocked Siemplify.

    Returns:
        The mocked `SiemplifyAction` instance.
    """
    import importlib  # pylint: disable=import-outside-toplevel

    module = importlib.import_module(f"microsoft_teams.actions.{module_name}")
    mock_siemplify = MagicMock()
    mock_siemplify.parameters = parameters
    for name, value in (siemplify_attributes or {}).items():
        setattr(mock_siemplify, name, value)
    mocker.patch.object(module, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(
        module,
        "extract_configuration_param",
        side_effect=lambda *_args, **kwargs: config.get(kwargs["param_name"]),
    )
    module.main()
    return mock_siemplify
