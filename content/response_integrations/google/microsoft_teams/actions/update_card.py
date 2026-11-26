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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param

from ..core.action_utils import build_manager, extract_destination, update_card
from ..core.card_utils import format_warnings, parse_card, validate_card
from ..core.MicrosoftConstants import INTEGRATION_DISPLAY_NAME, UPDATE_CARD_ACTION


@output_handler
def main() -> None:
    """Replace the Adaptive Card of an existing Microsoft Teams message."""
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_CARD_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    try:
        destination = extract_destination(siemplify)
        message_id = extract_action_param(siemplify, param_name="Message ID", is_mandatory=True, print_value=True)
        raw_card = extract_action_param(siemplify, param_name="Card JSON", is_mandatory=True, print_value=False)

        siemplify.LOGGER.info("----------------- Main - Started -----------------")
        destination.validate()
        warnings: list[str] = []
        card = parse_card(raw_card, warnings)
        warnings.extend(validate_card(card))
        for warning in warnings:
            siemplify.LOGGER.warn(warning)

        update_card(build_manager(siemplify), destination, message_id, card)
        siemplify.result.add_result_json({"id": message_id, "status": "updated"})
        output_message = (
            f"Successfully updated the card of message {message_id} in {destination} in {INTEGRATION_DISPLAY_NAME}."
        )
        output_message += format_warnings(warnings)

    except Exception as e:
        output_message = f"Error executing action {UPDATE_CARD_ACTION}. Reason: {e}"
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
