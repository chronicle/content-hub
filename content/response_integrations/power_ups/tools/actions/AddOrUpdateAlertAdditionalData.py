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

import json
from typing import Any

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ToolsCommon import (
    ExecutionScope,
    get_execution_scope,
    get_target_alerts,
)


def process_single_alert(alert: Any, incoming_data: Any) -> dict[str, Any]:
    """Update an alert's additional data payload with incoming JSON fields.

    Args:
        alert: The target alert SDK instance.
        incoming_data: Parsed incoming JSON fields to merge/extend.

    Returns:
        The updated additional data payload dictionary.
    """
    additional_data = alert.additional_data
    if additional_data:
        alert_data = json.loads(additional_data)
        if "list" not in alert_data:
            alert_data["list"] = []
        if "dict" not in alert_data:
            alert_data["dict"] = {}
        if "data" not in alert_data:
            alert_data["data"] = ""
    else:
        alert_data = {"dict": {}, "list": []}

    if incoming_data:
        if isinstance(incoming_data, list):
            alert_data["list"].extend(incoming_data)
        elif isinstance(incoming_data, dict):
            alert_data["dict"].update(incoming_data)
        else:
            alert_data["data"] = incoming_data

    return alert_data


@output_handler
def main() -> None:
    """Execute AddOrUpdateAlertAdditionalData action."""
    siemplify = SiemplifyAction()

    in_string = siemplify.parameters.get("Json Fields")
    data = None
    if in_string:
        try:
            data = json.loads(in_string)
        except Exception:
            data = in_string

    raw_scope = getattr(siemplify, "execution_scope", ExecutionScope.Alert.value)
    execution_scope = get_execution_scope(raw_scope, logger=siemplify.LOGGER)

    target_alerts = get_target_alerts(siemplify, execution_scope)

    updates = {}
    last_processed_data = None

    for alert in target_alerts:
        try:
            alert_data = process_single_alert(alert, data)
            updates[alert.identifier] = json.dumps(alert_data)
            last_processed_data = alert_data
        except Exception as e:
            siemplify.LOGGER.error(
                f"Failed to process alert {alert.identifier} additional data: {e}."
            )

    if updates:
        siemplify.update_alerts_additional_data(updates)

    output_message = "Alert data attached as JSON to the action result."
    result_value = len(updates)
    siemplify.result.add_result_json(last_processed_data or {})
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
