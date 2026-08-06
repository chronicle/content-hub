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
import sys
import json
import secrets
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from ..core.constants import (
    INTEGRATION_NAME,
    SEND_SMS_AND_WAIT_ACTION,
    ID_GENERATION_START,
    ID_GENERATION_END,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEND_SMS_AND_WAIT_ACTION
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
    status = EXECUTION_STATE_INPROGRESS
    sent_message_time = ""
    try:
        twilio_manager = TwilioManager(account_sid, auth_token)

        # Add a unique ID to the message - random 5 to 6-digit number
        siemplify_id = (
            secrets.randbelow(ID_GENERATION_END - ID_GENERATION_START)
            + ID_GENERATION_START
        )
        message = f"{message}\nTo respond type your reply followed by {siemplify_id}"

        siemplify.LOGGER.info(f"Sending message - {message}")

        siemplify.LOGGER.info(f"Sending SMS to: {phone_number}")
        message_object = twilio_manager.send_message(
            to=phone_number, from_=from_number, body=message
        )
        sent_message_time = message_object.date_created
        siemplify.LOGGER.info(
            f"SMS was successfully sent from {from_number} to {phone_number} at {str(sent_message_time)}"
        )

        output_message = f"SMS was sent to {phone_number}.\nMessage: {message}"

    except Exception as e:
        output_message = f"Failed to send the SMS. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info(f"Status: {status}, Output Message: {output_message}")
    siemplify.end(
        output_message, json.dumps((siemplify_id, str(sent_message_time))), status
    )


def query_job():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEND_SMS_AND_WAIT_ACTION

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
    to_number = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="SmsPhoneNumber",
        input_type=str,
    )

    from_number = extract_action_param(
        siemplify, param_name="Phone Number", is_mandatory=True, print_value=True
    )

    status = EXECUTION_STATE_INPROGRESS
    messages = []
    income_message_time = ""
    try:
        twilio_manager = TwilioManager(account_sid, auth_token)

        # Extract message time
        siemplify_id, income_message_time = json.loads(
            siemplify.parameters["additional_data"]
        )
        # A list of message objects with filtering
        siemplify.LOGGER.info(
            f"Fetching reply messages from {from_number} to {to_number}, since {income_message_time}"
        )

        messages = twilio_manager.list_messages(
            to=to_number, from_=from_number, date_sent_after=income_message_time
        )

    except Exception as e:
        output_message = f"Failed to fetch reply messages. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    if messages:
        siemplify.LOGGER.info(
            f"Found total {len(messages)} messages since {income_message_time} from {from_number} to {to_number}. Searching for message {siemplify_id}."
        )

        # Messages will be sorted on the DateSent field with the most recent messages appearing first.
        for message in messages:
            if isinstance(message.body, str) and message.body.endswith(
                str(siemplify_id)
            ):
                response_message = message.body
                siemplify.LOGGER.info(f"Found message response: {response_message}")
                siemplify.LOGGER.info(
                    "----------------- Main - Finished -----------------"
                )
                output_message = (
                    f"SMS retrieve from {from_number}\nReply: {response_message}"
                )
                status = EXECUTION_STATE_COMPLETED
                siemplify.end(output_message, response_message, status)

    else:
        siemplify.LOGGER.info(
            f"No messages were found since {income_message_time} from {from_number} to {to_number}."
        )

    output_message = f"Continuing...waiting for response from {from_number}"
    siemplify.LOGGER.info("Response not found yet. Waiting.")
    siemplify.end(
        output_message, json.dumps((siemplify_id, str(income_message_time))), status
    )


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        query_job()
