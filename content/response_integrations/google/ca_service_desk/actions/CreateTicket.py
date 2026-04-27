from __future__ import annotations
import json

from ..core.CaSoapManager import CaSoapManager
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param, extract_configuration_param
from ..core.constants import INTEGRATION_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    status = EXECUTION_STATE_COMPLETED
    result_value = "false"
    output_message = "There was a problem creating a ticket."
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        input_type=str,
    )

    summary = extract_action_param(
        siemplify,
        param_name="Summary",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    description = extract_action_param(
        siemplify,
        param_name="Description",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    area = extract_action_param(
        siemplify,
        param_name="Category Name",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    group = extract_action_param(
        siemplify,
        param_name="Group Name",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    action_username = extract_action_param(
        siemplify,
        param_name="Username",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    custom_fields = extract_action_param(
        siemplify,
        param_name="Custom Fields",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        ca_manager = CaSoapManager(api_root, username, password)
        ticket_params = {
            "summary": summary,
            "description": description,
            "area": area,
            "group": group,
            "username": action_username,
        }
        if custom_fields:
            custom_fields = json.loads(custom_fields)
            ticket_params.update(custom_fields)

        incident_id = ca_manager.create_incident_openreq(**ticket_params)

        if incident_id:
            output_message = f"Incident {incident_id} was Opened."
            result_value = incident_id
    except Exception as error:
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
