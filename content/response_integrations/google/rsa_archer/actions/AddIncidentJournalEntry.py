from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.RSAArcherManager import RSAArcherManager, SecurityIncidentDoesntExistError
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import PROVIDER_NAME, ADD_JOURNAL_ENTRY_SCRIPT_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_JOURNAL_ENTRY_SCRIPT_NAME
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
    destination_content_id = extract_action_param(
        siemplify,
        param_name="Destination Content ID",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    text = extract_action_param(
        siemplify,
        param_name="Text",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""

    try:
        archer_manager = RSAArcherManager(
            server_address,
            username,
            password,
            instance_name,
            verify_ssl,
            siemplify.LOGGER,
        )

        application_id = archer_manager.get_incident_journal_app_id()
        request_details = archer_manager.get_security_incident_id(application_id)
        security_incident_level_id = archer_manager.get_security_incident_level()

        request_details["security_incident_level_id"] = security_incident_level_id

        _result = archer_manager.get_security_incident_details(
            incident_id=destination_content_id
        )  # check if given content_id exist

        result = archer_manager.add_journal_entry(
            destination_content_id=destination_content_id,
            text=text,
            request_details=request_details,
        )

        siemplify.result.add_result_json(result)
        output_message += f"Successfully added new journal entry to the Security Incident {destination_content_id} in RSA Archer."

    except SecurityIncidentDoesntExistError as e:
        output_message = f"Error executing action Add Incident Journal Entry. Reason: Security Incident {destination_content_id} was not found."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    except Exception as e:
        output_message = (
            f"Error executing action Add Incident Journal Entry. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
