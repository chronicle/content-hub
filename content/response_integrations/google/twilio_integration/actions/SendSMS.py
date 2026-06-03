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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.TwilioManager import TwilioManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import INTEGRATION_NAME, SEND_SMS_ACTION


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEND_SMS_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    account_sid = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AccountSid",
        input_type=str,
    )
    auth_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AuthenticationToken",
        input_type=str,
    )
    from_number = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="SmsPhoneNumber",
        input_type=str,
    )

    phone_number = extract_action_param(
        siemplify, param_name="Phone Number", is_mandatory=True, print_value=True
    )
    message = extract_action_param(
        siemplify, param_name="Message", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        twilio_manager = TwilioManager(account_sid, auth_token)
        twilio_manager.send_message(to=phone_number, from_=from_number, body=message)
        output_message = f"SMS was sent to {phone_number}.\nMessage: {message}"

    except Exception as e:
        output_message = f"Failed to send the SMS. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info(
        f"Status: {status}, Result Value: {result_value}, Output Message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
