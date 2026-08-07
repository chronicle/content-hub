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
from ..core.SplunkManager import SplunkManager
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import convert_comma_separated_to_list
from ..core.constants import (
    INTEGRATION_NAME,
    DISPOSITION_MAPPER,
    UPDATE_NOTABLE_EVENTS_SCRIPT_NAME,
)
from ..core.exceptions import UnableToUpdateNotableEvents

EMPTY_DROPDOWN_VALUE = "Select One"
STATUS_MAPPER = {
    "Unassigned": 0,
    "New": 1,
    "In Progress": 2,
    "Pending": 3,
    "Resolved": 4,
    "Closed": 5,
}


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_NOTABLE_EVENTS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=False,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        print_value=False,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        print_value=True,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        print_value=False,
    )

    notable_event_ids = extract_action_param(
        siemplify, param_name="Notable Event IDs", is_mandatory=True, print_value=True
    )
    event_status = extract_action_param(
        siemplify, param_name="Status", print_value=True
    )
    urgency = extract_action_param(siemplify, param_name="Urgency", print_value=True)
    new_owner = extract_action_param(
        siemplify, param_name="New Owner", print_value=True
    )
    comment = extract_action_param(siemplify, param_name="Comment", print_value=True)
    disposition = extract_action_param(
        siemplify, param_name="Disposition", print_value=True
    )

    notable_event_ids = convert_comma_separated_to_list(notable_event_ids)

    event_status = STATUS_MAPPER.get(event_status)
    urgency = urgency.lower() if urgency != EMPTY_DROPDOWN_VALUE else None
    disposition = DISPOSITION_MAPPER.get(disposition)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_FAILED
    result_value = False

    try:
        at_least_one_filled = any(
            bool(parameter or parameter is 0 and parameter != "Select one")
            for parameter in (event_status, urgency, new_owner, comment, disposition)
        )

        if at_least_one_filled is False:
            raise Exception("at least one parameter should have a value.")

        manager = SplunkManager(
            server_address=api_root,
            username=username,
            password=password,
            api_token=api_token,
            ca_certificate=ca_certificate,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        manager.update_notable_event(
            notable_event_ids=notable_event_ids,
            status=event_status,
            urgency=urgency,
            new_owner=new_owner,
            comment=comment,
            disposition=disposition,
        )
        output_message = (
            f"Successfully updated {len(notable_event_ids)} notable events in Splunk."
        )
        result_value = True
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info(output_message)
    except UnableToUpdateNotableEvents as e:
        status = EXECUTION_STATE_COMPLETED
        output_message = f"Action wasn't able to update notable events. Reason:{e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as critical_error:
        output_message = (
            f"Error executing action '{UPDATE_NOTABLE_EVENTS_SCRIPT_NAME}'. "
            f"Reason: {critical_error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(critical_error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"result_value: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
