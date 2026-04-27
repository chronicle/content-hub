from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.BMCHelixRemedyForceManager import BMCHelixRemedyForceManager
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    construct_csv,
    convert_comma_separated_to_list,
)
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import INTEGRATION_NAME, GET_RECORD_DETAILS_ACTION
from ..core.BMCHelixRemedyForceExceptions import RecordTypeNotFound, RecordIDNotFound


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_RECORD_DETAILS_ACTION

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
    record_ids = extract_action_param(
        siemplify, param_name="Record IDs", print_value=True, is_mandatory=True
    )
    record_ids = convert_comma_separated_to_list(record_ids)
    fields_to_return = extract_action_param(
        siemplify, param_name="Fields To Return", print_value=True, is_mandatory=False
    )
    fields_to_return = convert_comma_separated_to_list(fields_to_return)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    successful_records = []
    successful_records_details = []
    failed_records = []
    json_result = []
    output_message = ""

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

        for record_id in record_ids:
            try:
                record_details = manager.get_record_details(
                    record_type=record_type,
                    record_id=record_id,
                    fields_to_return=fields_to_return,
                )

                if record_details.to_json():

                    found_keys = list(record_details.to_json().keys())
                    not_found_keys = list(set(fields_to_return) - set(found_keys))
                    if not_found_keys:
                        siemplify.LOGGER.error(
                            f"Following fields were not found for the record {record_type} with ID {record_id} in {INTEGRATION_NAME}: {', '.join(not_found_keys)}."
                        )

                    successful_records.append(record_id)
                    json_result.append(record_details.to_json())

                    successful_records_details.append(record_details)
                    siemplify.result.add_data_table(
                        f"Record {record_id} Details",
                        data_table=construct_csv(record_details.to_table()),
                    )
                else:
                    raise Exception(
                        "none of the provided fields were found. Please check the spelling"
                    )

            except RecordIDNotFound as e:
                failed_records.append(record_id)
                continue

            except Exception as e:
                raise

        if successful_records:
            siemplify.result.add_result_json(json_result)
            output_message += f"Successfully returned details regarding record type {record_type} for the following ids: {', '.join([record_id for record_id in successful_records])}."

        if failed_records:
            output_message += f"\nAction wasn't able to find details regarding record type {record_type} for the following ids: {', '.join([record_id for record_id in failed_records])}."

        if not successful_records:
            result_value = False
            output_message = "No records were found."

    except RecordTypeNotFound as e:
        output_message = f'Error executing action {GET_RECORD_DETAILS_ACTION}. Reason: {record_type} wasn\'t found in {INTEGRATION_NAME}. Please use the action "List Record Types" to get a list of available record types.'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    except Exception as e:
        output_message = (
            f"Error executing action {GET_RECORD_DETAILS_ACTION}. Reason: {e}."
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
