from __future__ import annotations
import json
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_configuration_param, extract_action_param

from ..core.BMCRemedyITSMExceptions import (
    BMCRemedyITSMNotFoundException,
    BMCRemedyITSMTimeoutException,
)
from ..core.BMCRemedyITSMManager import BMCRemedyITSMManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    WAIT_FOR_RECORD_FIELDS_UPDATE_SCRIPT_NAME,
)
from ..core.UtilsManager import is_async_action_timeout


def check_record_fields(record, fields_to_check_dict):
    """
    Check record fields
    :param record: {RecordDetails} RecordDetails object
    :param fields_to_check_dict: {dict} dictionary containing needed fields and values
    :return: {tuple} updated_fields, not_updated_fields
    """
    updated_fields = []
    not_updated_fields = []
    not_found_fields = []

    for key, value in fields_to_check_dict.items():
        try:
            record.raw_data[key]
        except KeyError:
            not_found_fields.append(key)

        if record.raw_data.get(key, "") == value:
            updated_fields.append(key)
        else:
            not_updated_fields.append(key)

    if not_found_fields:
        raise Exception(
            f"the following fields were not found in the structure of record: "
            f"{','.join(not_found_fields)}."
        )

    return updated_fields, not_updated_fields


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = WAIT_FOR_RECORD_FIELDS_UPDATE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
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
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # action parameters
    record_type = extract_action_param(
        siemplify, param_name="Record Type", is_mandatory=True, print_value=True
    )
    record_id = extract_action_param(
        siemplify, param_name="Record ID", is_mandatory=True, print_value=True
    )
    fields_to_check = extract_action_param(
        siemplify, param_name="Fields To Check", is_mandatory=True, print_value=True
    )
    fail_if_timeout = extract_action_param(
        siemplify,
        param_name="Fail If Timeout",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    manager = None
    output_message = ""

    try:
        # check if async action timeout approaching
        if is_async_action_timeout(siemplify):
            additional_data = json.loads(
                extract_action_param(
                    siemplify=siemplify,
                    param_name="additional_data",
                    default_value="[]",
                )
            )
            if not fail_if_timeout:
                raise BMCRemedyITSMTimeoutException(
                    f"The following fields were not updated for {record_type} record "
                    f"with ID {record_id} in {INTEGRATION_DISPLAY_NAME}: "
                    f"{','.join(additional_data)}"
                )

            raise Exception(
                f"The following fields were not updated for {record_type} record with ID {record_id} in "
                f"{INTEGRATION_DISPLAY_NAME}: {','.join(additional_data)}"
            )

        try:
            fields_to_check_dict = json.loads(fields_to_check)
        except Exception:
            raise Exception(
                'Invalid JSON payload provided in the parameter "Fields To Check". Please check the '
                "structure."
            )

        manager = BMCRemedyITSMManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        record = manager.get_record_details(record_type, record_id, fields={})

        if not record:
            raise BMCRemedyITSMNotFoundException(
                f"record with ID {record_id} was not found"
            )

        updated_fields, not_updated_fields = check_record_fields(
            record, fields_to_check_dict
        )

        if len(updated_fields) == len(fields_to_check_dict.keys()):
            siemplify.result.add_result_json(record.to_json())
            result = True
            status = EXECUTION_STATE_COMPLETED
            output_message = f"{record_type} record with ID {record_id} was updated in {INTEGRATION_DISPLAY_NAME}."
        else:
            result = json.dumps(not_updated_fields)
            status = EXECUTION_STATE_INPROGRESS
            output_message = (
                f"Waiting for the following fields to be updated for {record_type} record with ID "
                f"{record_id} in {INTEGRATION_DISPLAY_NAME}: {','.join(not_updated_fields)}"
            )

    except BMCRemedyITSMTimeoutException as e:
        result = False
        status = EXECUTION_STATE_COMPLETED
        output_message = str(e)
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {WAIT_FOR_RECORD_FIELDS_UPDATE_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action {WAIT_FOR_RECORD_FIELDS_UPDATE_SCRIPT_NAME}. Reason: {e}"

    finally:
        try:
            if manager:
                siemplify.LOGGER.info(f"Logging out from {INTEGRATION_DISPLAY_NAME}..")
                manager.logout()
                siemplify.LOGGER.info(
                    f"Successfully logged out from {INTEGRATION_DISPLAY_NAME}"
                )
        except Exception as error:
            siemplify.LOGGER.error(f"Logging out failed. Error: {error}")
            siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
