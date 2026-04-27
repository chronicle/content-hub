from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.BMCHelixRemedyForceManager import BMCHelixRemedyForceManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import INTEGRATION_NAME, DELETE_RECORD_ACTION
from ..core.BMCHelixRemedyForceExceptions import RecordTypeNotFound, RecordIDNotFound


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DELETE_RECORD_ACTION

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Login API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client ID"
    )
    client_secret = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client Secret"
    )
    refresh_token = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Refresh Token"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    record_type = extract_action_param(
        siemplify, param_name="Record Type", print_value=True, is_mandatory=True
    )
    record_id = extract_action_param(
        siemplify, param_name="Record ID", print_value=True, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = BMCHelixRemedyForceManager(
            api_root=api_root,
            password=password,
            username=username,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            login_api_root=login_api_root,
        )
        manager.delete_record(record_type=record_type, record_id=record_id)
        output_message = f"Successfully deleted {record_type} record with ID {record_id} in {INTEGRATION_NAME}."

    except RecordIDNotFound as e:
        output_message = f"{record_type} record with ID {record_id} doesn't exist in {INTEGRATION_NAME}."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_COMPLETED

    except RecordTypeNotFound as e:
        output_message = f'Error executing action {DELETE_RECORD_ACTION}. Reason: {record_type} wasn\'t found in {INTEGRATION_NAME}. Please use the action "List Record Types" to get a list of available record types.'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    except Exception as e:
        output_message = f"Error executing action {DELETE_RECORD_ACTION}. Reason: {e}."
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
