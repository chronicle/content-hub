from __future__ import annotations
from ..core.constants import (
    RESPONSE_ALREADY_UPDATED,
    INTEGRATION_NAME,
    MARK_INCIDENT_SCRIPT_NAME,
    MARK_INCIDENT_STATUS_TYPE,
)
from ..core.PhishrodManager import PhishrodManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param, extract_action_param


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = MARK_INCIDENT_SCRIPT_NAME

    siemplify.LOGGER.info("-------------- Main - Param Init --------------")

    # integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
        remove_whitespaces=False,
        print_value=False,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
        remove_whitespaces=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    # Action parameters
    incident_number = extract_action_param(
        siemplify, param_name="Incident ID", is_mandatory=True, print_value=False
    )
    incident_status = extract_action_param(
        siemplify,
        param_name="Status",
        is_mandatory=False,
        default_value=MARK_INCIDENT_STATUS_TYPE.get(0),
        print_value=True,
        input_type=str,
    )
    comment = extract_action_param(
        siemplify, param_name="Comment", is_mandatory=True, print_value=False
    )

    siemplify.LOGGER.info("---------------- Main - Started ----------------")

    output_message = ""
    result = True
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = PhishrodManager(
            api_root=api_root,
            api_key=api_key,
            client_id=client_id,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        action_result = manager.mark_incident(
            incident_number=incident_number,
            incident_status=MARK_INCIDENT_STATUS_TYPE.get(incident_status),
            comment=comment,
        )

        if RESPONSE_ALREADY_UPDATED in action_result.status:
            output_message = (
                f"Incident {incident_number} was already marked previously in"
                " PhishRod"
            )
            result = False
        else:
            output_message = (
                f"Successfully marked the incident {incident_number} in" " PhishRod."
            )
        siemplify.result.add_result_json(action_result.to_json())

    except Exception as error:
        siemplify.LOGGER.error(f"Error executing action {MARK_INCIDENT_SCRIPT_NAME}")
        siemplify.LOGGER.exception(error)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action  {MARK_INCIDENT_SCRIPT_NAME}. {error}"

    siemplify.LOGGER.info("---------------- Main - Finished ---------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
