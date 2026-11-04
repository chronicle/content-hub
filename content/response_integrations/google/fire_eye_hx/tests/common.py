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
import re
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock, patch
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / 'config.json'
CONFIG: dict = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}


SUMMARY_PATTERN: re.Pattern[str] = re.compile(
    r"^ACTION_RESULT_SUMMARY v=1 outcome=(?P<outcome>SUCCESS|PARTIAL_SUCCESS|FAILURE) "
    r"error_type=(?P<error_type>[A-Z_]+) execution_state=(?P<execution_state>COMPLETED|FAILED|TIMEDOUT|IN_PROGRESS) "
    r"targets=(?P<targets>\d+) failed=(?P<failed>\d+) skipped=(?P<skipped>\d+) "
    r"exc_type=(?P<exc_type>\w+) http_status=(?P<http_status>\d+|NONE)$"
)


def get_summary_lines(mock_siemplify: Any) -> list[dict[str, str]]:
    """Get the ACTION_RESULT_SUMMARY lines that an action logged, parsed into fields.

    Args:
        mock_siemplify: The mocked action object.

    Returns:
        The fields of each summary line. A line that does not match the exact format fails the test.
    """
    lines = [
        call.args[0]
        for call in mock_siemplify.LOGGER.info.call_args_list
        if call.args and str(call.args[0]).startswith("ACTION_RESULT_SUMMARY")
    ]
    matches = [SUMMARY_PATTERN.match(line) for line in lines]
    assert all(matches), lines

    return [match.groupdict() for match in matches]


def run_action(
    module: Any,
    params: dict[str, Any],
    manager_setup: Callable[[Any], None],
    entities: list[Any] | None = None,
) -> Any:
    """Run a synchronous FireEyeHX action with a mocked manager.

    Args:
        module: The action module.
        params: The action parameters.
        manager_setup: Configure the mocked manager.
        entities: The target entities.

    Returns:
        The mocked action object.
    """
    with (
        patch.object(module, "SiemplifyAction") as mock_siemplify_action,
        patch.object(module, "extract_configuration_param"),
        patch.object(module, "extract_action_param") as mock_extract_action,
        patch.object(module, "FireEyeHXManager") as mock_manager_cls,
    ):
        mock_siemplify = mock_siemplify_action.return_value
        mock_siemplify.target_entities = entities or []
        mock_siemplify.execution_deadline_unix_time_ms = 9999999999999
        mock_extract_action.side_effect = lambda siemplify, param_name, **kwargs: params.get(
            param_name, kwargs.get("default_value")
        )
        mock_manager_cls.return_value.lookup_errors = []
        manager_setup(mock_manager_cls.return_value)
        module.main()

    return mock_siemplify


def make_entity(identifier: str, entity_type: str) -> MagicMock:
    """Build a target entity.

    Args:
        identifier: The entity identifier.
        entity_type: The entity type.

    Returns:
        The entity.
    """
    entity = MagicMock()
    entity.identifier = identifier
    entity.entity_type = entity_type
    return entity
