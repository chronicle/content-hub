from __future__ import annotations
from ..core.constants import (
    INTEGRATION_NAME,
    UPDATE_INCIDENT_SCRIPT_NAME,
    UPDATE_INCIDENT_ALREADY_MARKED_MESSAGE,
    UPDATE_INCIDENT_STATUS_DEFAULT_VALUE,
)
from ..core.PhishrodManager import PhishrodManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param, extract_action_param


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_INCIDENT_SCRIPT_NAME
    siemplify.LOGGER.info("--------------- Main - Param Init ---------------")

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

    # action parameters
    incident_id = extract_action_param(
        siemplify, param_name="Incident ID", is_mandatory=True, print_value=True
    )
    incident_status = extract_action_param(
        siemplify,
        param_name="Status",
        default_value=UPDATE_INCIDENT_STATUS_DEFAULT_VALUE,
        is_mandatory=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started ----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED

    manager = PhishrodManager(
        api_root=api_root,
        api_key=api_key,
        client_id=client_id,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
        siemplify_logger=siemplify.LOGGER,
    )
    try:
        action_result = manager.update_incident(incident_id, incident_status)

        if (
            action_result.message not in UPDATE_INCIDENT_ALREADY_MARKED_MESSAGE
            and not action_result.status_marked
        ):
            raise Exception(f"{action_result.message}")
        else:
            if action_result.status_marked:
                output_message = (
                    f"Successfully updated incident {incident_id} in PhishRod."
                )
            else:
                output_message = (
                    f"Incident {incident_id}"
                    " status was already modified previously in PhishRod."
                )
                result_value = False
        siemplify.result.add_result_json(action_result.to_json())

    except Exception as error:
        output_message = (
            f'Error executing action "{UPDATE_INCIDENT_SCRIPT_NAME}".'
            f"\nReason: {error}"
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(f"Exception: {error}")

    siemplify.LOGGER.info("---------------- Main - Finished ----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
