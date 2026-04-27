from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.RSAArcherManager import RSAArcherManager, DEFAULT_APP_NAME, RSAArcherManagerError
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

PROVIDER_NAME = "RSAArcher"
SCRIPT_NAME = "RSAArcher - GetIncidentDetails"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration
    server_address = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Password",
        is_mandatory=True,
        input_type=str,
    )

    instance_name = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Instance Name",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )

    # Parameters
    content_id = extract_action_param(
        siemplify,
        param_name="Content ID",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    application_name = extract_action_param(
        siemplify,
        param_name="Application Name",
        is_mandatory=False,
        print_value=True,
        input_type=str,
        default_value=DEFAULT_APP_NAME,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = False
    result_status = EXECUTION_STATE_COMPLETED

    try:
        archer_manager = RSAArcherManager(
            server_address,
            username,
            password,
            instance_name,
            verify_ssl,
            siemplify.LOGGER,
        )

        app = archer_manager.get_app_by_name(app_name=application_name)
        if app:
            incident_details = archer_manager.get_incident_by_id(
                incident_id=content_id, alias=app.alias, check_content=False
            )

            siemplify.result.add_result_json(incident_details.to_json())
            output_message = (
                "Successfully returned information about the incident with ID {} in RSA Archer."
                "".format(content_id)
            )
            result_value = True
        else:
            output_message = f"Action wasn't able to get incident details. Reason: {application_name} application was not found."

    except RSAArcherManagerError as e:
        output_message = str(e)
        siemplify.LOGGER.error(output_message)

    except Exception as e:
        output_message = f'Error executing action "Get Incident Details". Reason: {e}'
        siemplify.LOGGER.error(f"Error executing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        result_status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {result_status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, result_status)


if __name__ == "__main__":
    main()
