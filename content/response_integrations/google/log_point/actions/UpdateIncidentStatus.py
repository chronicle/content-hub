from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.LogPointManager import LogPointManager
from ..core.consts import (
    INTEGRATION_NAME,
    UPDATE_INCIDENT_STATUS_SCRIPT_NAME,
    ACTION_MAPPING,
    CLOSE,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_INCIDENT_STATUS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    ip_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="IP Address",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )

    secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret",
        is_mandatory=True,
    )

    ca_certificate_file = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        is_mandatory=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=True,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    incident_id = extract_action_param(
        siemplify, param_name="Incident ID", is_mandatory=True, print_value=True
    )
    action = extract_action_param(
        siemplify,
        param_name="Action",
        is_mandatory=True,
        default_value=CLOSE,
        print_value=True,
    )

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = (
        f"Successfully {ACTION_MAPPING[action]} incident with ID {incident_id} in "
        f"{INTEGRATION_NAME}."
    )

    try:
        manager = LogPointManager(
            ip_address=ip_address,
            username=username,
            secret=secret,
            ca_certificate_file=ca_certificate_file,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        try:
            (
                manager.resolve_and_close_incident(incident_id)
                if action == CLOSE
                else manager.resolve_incident_status(incident_id)
            )

        except Exception as error:
            siemplify.LOGGER.exception(error)
            output_message = (
                f"Action wasn't able to {action} incident with ID {incident_id} in "
                "Logpoint."
            )

        siemplify.LOGGER.info(output_message)

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action '{UPDATE_INCIDENT_STATUS_SCRIPT_NAME}'. "
            f"Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: "
        f"{output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
