from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.RSAManager import RSAManager
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, ADD_NOTE_TO_INCIDENT_SCRIPT_NAME
from ..core.RSAExceptions import UpdateFailException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_NOTE_TO_INCIDENT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration.
    ui_api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Web API Root"
    )
    ui_username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Web Username"
    )
    ui_password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Web Password"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Parameters
    incident_id = extract_action_param(
        siemplify, param_name="Incident ID", input_type=str, is_mandatory=True
    )
    note = extract_action_param(
        siemplify, param_name="Note", input_type=str, is_mandatory=True
    )
    author = extract_action_param(
        siemplify, param_name="Author", input_type=str, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = False

    try:
        rsa_manager = RSAManager(
            ui_api_root=ui_api_root,
            ui_username=ui_username,
            ui_password=ui_password,
            verify_ssl=verify_ssl,
        )
        rsa_manager.add_note_to_incident(
            incident_id=incident_id, note=note, author=author
        )
        output_message = f"Successfully added note to incident with ID {incident_id} in RSA Netwitness"
        result_value = True
    except UpdateFailException as e:
        output_message = f"Action wasn't able to add note to incident with ID {incident_id} in RSA Netwitness. Reason: {e}"
        siemplify.LOGGER.error(output_message)

    except Exception as e:
        output_message = f'Error executing action "Add Note to Incident". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
