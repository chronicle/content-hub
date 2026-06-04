# Copyright 2025 Google LLC
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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ToolsCommon import (
    ExecutionScope,
    get_execution_scope,
    get_target_alerts,
)

ALERT_SCORE = "ALERT_SCORE"


def update_single_alert_score(
    siemplify: SiemplifyAction,
    alert_group_id: str | None,
    _input: str,
) -> str:
    """Fetch, increment, and save context score for a specific alert.

    Args:
        siemplify: The SiemplifyAction orchestration instance.
        alert_group_id: Group identifier of the alert (None for current alert).
        _input: String representation of the value to increment by.

    Returns:
        The new alert score string value.
    """
    current_score = siemplify.get_alert_context_property(
        ALERT_SCORE,
        alert_group_identifier=alert_group_id,
    )
    if current_score is not None:
        current_score = current_score.strip('"')
    else:
        current_score = 0

    new_score = str(int(current_score) + int(_input))
    siemplify.set_alert_context_property(
        ALERT_SCORE,
        new_score,
        alert_group_identifier=alert_group_id,
    )
    return new_score


@output_handler
def main():
    siemplify = SiemplifyAction()

    _input = siemplify.extract_action_param("Input")

    raw_scope = getattr(siemplify, "execution_scope", ExecutionScope.Alert.value)
    execution_scope = get_execution_scope(raw_scope, logger=siemplify.LOGGER)

    target_alerts = get_target_alerts(siemplify, execution_scope)

    updated_count = 0
    last_score = None
    for alert in target_alerts:
        try:
            last_score = update_single_alert_score(
                siemplify,
                alert.alert_group_identifier,
                _input,
            )
            updated_count += 1
        except Exception as e:
            siemplify.LOGGER.error(
                "Failed to update alert score for alert "
                f"{alert.identifier}: {e}"
            )

    if execution_scope.value == ExecutionScope.Alert.value:
        result_value = last_score
        output_message = f"The Alert Score has been updated to: {last_score}"
    else:
        result_value = updated_count
        output_message = (
            "The Alert Score was successfully updated for "
            f"{updated_count} alert(s)."
        )

    siemplify.end(output_message, result_value, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
