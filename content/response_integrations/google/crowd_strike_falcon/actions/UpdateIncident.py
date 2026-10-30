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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.extraction import extract_action_param, extract_configuration_param

from crowd_strike_falcon.core.constants import (
    API_ROOT_DEFAULT,
    CID_ERROR,
    INTEGRATION_NAME,
    UPDATE_INCIDENT_SCRIPT_NAME,
    UPDATE_INCIDENT_DEFAULT_STATUS,
)
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core import exceptions


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_INCIDENT_SCRIPT_NAME
    siemplify.LOGGER.info("--------------- Main - Param Init ----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
        default_value=API_ROOT_DEFAULT,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client API ID",
        is_mandatory=True,
        print_value=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client API Secret",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )
    integration_cid = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Customer ID",
        print_value=True
    )
    action_cid = extract_action_param(
        siemplify,
        param_name="Customer ID",
        print_value=True,
    )
    customer_id = action_cid or integration_cid
    incident_id = extract_action_param(
        siemplify, param_name="Incident ID", is_mandatory=True, print_value=True
    )
    id_status = extract_action_param(siemplify, param_name="Status", print_value=True)
    assign_to = extract_action_param(
        siemplify, param_name="Assign to", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = CrowdStrikeManager(
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=verify_ssl,
            api_root=api_root,
            logger=siemplify.LOGGER,
            customer_id=customer_id,
        )

        if customer_id and not assign_to:
            raise exceptions.CrowdStrikeParameterError(
                'if the Customer ID is provided, "Assign To" value should be '
                "provided as well."
            )

        if assign_to is None and id_status.lower() == UPDATE_INCIDENT_DEFAULT_STATUS:
            raise exceptions.CrowdStrikeParameterError(
                'At least one of the "Status" or "Assign To" parameters should'
                " have a value."
            )

        manager.update_incident(
            incident_id=incident_id,
            id_status=id_status,
            assign_to=assign_to,
            cid=customer_id,
        )

        updated_incident = manager.search_incident(incident_id)
        siemplify.result.add_result_json(updated_incident.to_json())

        output_message = (
            f"Successfully updated incident with ID {incident_id} in Crowdstrike"
        )

    except Exception as e:
        error_message = f"Error executing action {UPDATE_INCIDENT_SCRIPT_NAME}."
        output_message = f"{error_message} Reason: {e}"
        if CID_ERROR in str(e).lower():
            output_message = f"{error_message} Reason: Incorrect Customer ID specified."

        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.info(e)
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n status: {status}"
        f"\n result_value: {result_value}"
        f"\n output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
