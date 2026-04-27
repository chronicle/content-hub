from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.BMCHelixRemedyForceManager import BMCHelixRemedyForceManager
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, WAIT_FOR_FIELD_UPDATE_ACTION
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
import json
import sys
from ..core.BMCHelixRemedyForceExceptions import RecordTypeNotFound, RecordIDNotFound
from ..core.utils import is_approaching_timeout


def start_operation(siemplify, bmc_manager, record_type, record_id, fields_to_check):
    """
    Main part of the action that gets the initial field_status and validates the inputs
    :param siemplify: SiemplifyAction object.
    :param bmc_manager: BMC manager object.
    :param record_type: Record Type
    :param record_id: ID of the record to watch
    :param fields_to_check: JSON Payload containing fields and expected values
    :return: {output message, json result, execution_state}
    """

    fields_to_check_keys = list(fields_to_check.keys())

    status = EXECUTION_STATE_INPROGRESS
    output_message = f"Waiting for the following fields to be updated for {record_type} record with ID {record_id} in {INTEGRATION_NAME}: {', '.join(fields_to_check_keys)}"

    try:
        record_details = bmc_manager.get_record_details(
            record_type=record_type,
            record_id=record_id,
            fields_to_return=fields_to_check,
        )

        found_fields = list(record_details.raw_data.keys())
        not_found_fields = list(set(found_fields) - set(fields_to_check_keys))
        if len(not_found_fields) != 0:
            raise Exception(
                f"the following fields were not found in the structure of record: {', '.join(not_found_fields)}."
            )

        result_value = True

    except (RecordIDNotFound, RecordTypeNotFound) as e:
        raise

    except Exception as e:
        output_message = (
            f"Error executing action {WAIT_FOR_FIELD_UPDATE_ACTION}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    return output_message, result_value, status


def query_operation_status(
    siemplify, bmc_manager, record_type, record_id, fields_to_check
):
    """
    Part of the action that periodically fetches the record details and compare them with the initial state
    :param siemplify: SiemplifyAction object.
    :param bmc_manager: BMC manager object.
    :param record_type: Record Type
    :param record_id: ID of the record to watch
    :param fields_to_check: JSON Payload containing fields and expected values
    :return: {output message, json result, execution_state}
    """
    try:
        record_details = bmc_manager.get_record_details(
            record_type=record_type, record_id=record_id, fields_to_return=None
        )
        fields_updated = False

        for key, value in list(record_details.raw_data.items()):
            if key in fields_to_check:
                if fields_to_check.get(key) == value:
                    fields_updated = True
                else:
                    fields_updated = False

        if not fields_updated:
            status = EXECUTION_STATE_INPROGRESS
            output_message = f"Waiting for the following fields to be updated for {record_type} record with ID {record_id} in {INTEGRATION_NAME}: {', '.join(fields_to_check)}"
            result_value = True

        else:
            output_message = f"{record_type} record with ID {record_id} was updated in {INTEGRATION_NAME}."
            result_value = True
            status = EXECUTION_STATE_COMPLETED
            siemplify.result.add_result_json(record_details.to_json())

    except Exception as e:
        output_message = (
            f"Error executing action {WAIT_FOR_FIELD_UPDATE_ACTION}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = WAIT_FOR_FIELD_UPDATE_ACTION
    mode = "Main" if is_first_run else "Check changes"
    action_start_time = unix_now()
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

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

    fields_to_check = extract_action_param(
        siemplify, param_name="Fields To Check", print_value=True, is_mandatory=False
    )
    fail_if_timeout = extract_action_param(
        siemplify,
        param_name="Fail If Timeout",
        print_value=True,
        is_mandatory=True,
        input_type=bool,
        default_value=True,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        try:
            fields_to_check = json.loads(fields_to_check)
        except Exception as e:
            raise Exception(
                'Invalid JSON payload provided in the parameter "Fields To Check". Please check the structure.'
            )

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

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify,
                bmc_manager=manager,
                record_type=record_type,
                record_id=record_id,
                fields_to_check=fields_to_check,
            )
        else:
            # If Fail If Timeout is set to True, we don't check the approaching timeout
            if not fail_if_timeout and is_approaching_timeout(
                action_start_time, siemplify.execution_deadline_unix_time_ms
            ):
                output_message = f"The following fields were not updated for {record_type} record with ID {record_id} in {INTEGRATION_NAME}: {', '.join(fields_to_check)}"
                result_value = False
                status = EXECUTION_STATE_COMPLETED
            else:
                output_message, result_value, status = query_operation_status(
                    siemplify,
                    bmc_manager=manager,
                    record_type=record_type,
                    record_id=record_id,
                    fields_to_check=fields_to_check,
                )

    except RecordIDNotFound as e:
        output_message = f"{record_type} record with ID {record_id} doesn't exist in {INTEGRATION_NAME}."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    except RecordTypeNotFound as e:
        output_message = f'Error executing action {WAIT_FOR_FIELD_UPDATE_ACTION}. Reason: {record_type} wasn\'t found in {INTEGRATION_NAME}. Please use the action "List Record Types" to get a list of available record types.'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    except Exception as e:
        output_message = (
            f"Error executing action {WAIT_FOR_FIELD_UPDATE_ACTION}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
