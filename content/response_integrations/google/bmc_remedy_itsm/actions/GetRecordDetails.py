from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import flat_dict_to_csv

from ..core.BMCRemedyITSMExceptions import BMCRemedyITSMClientErrorException
from ..core.BMCRemedyITSMManager import BMCRemedyITSMManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    GET_RECORD_DETAILS_SCRIPT_NAME,
)
from ..core.UtilsManager import convert_comma_separated_to_list

TABLE_NAME = "Record {record_id} Details"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_RECORD_DETAILS_SCRIPT_NAME
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
    record_ids = extract_action_param(
        siemplify, param_name="Record IDs", is_mandatory=True, print_value=True
    )
    fields_to_return = extract_action_param(
        siemplify, param_name="Fields To Return", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    record_ids = list(set(convert_comma_separated_to_list(record_ids)))
    successful_records = {}
    failed_records, json_results, table_results = [], [], []
    manager = None

    try:
        manager = BMCRemedyITSMManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        manager.test_connectivity()

        for record_id in record_ids:
            try:
                record_details = manager.get_record_details(
                    record_type=record_type,
                    record_id=record_id,
                    fields=fields_to_return,
                )
                if record_details.raw_data:
                    successful_records[record_id] = record_details
                    json_results.append(record_details.to_json())
                else:
                    failed_records.append(record_id)
            except BMCRemedyITSMClientErrorException as e:
                raise Exception(e)
            except Exception as e:
                failed_records.append(record_id)
                siemplify.LOGGER.error(
                    f"An error occurred on record with ID {record_id}"
                )
                siemplify.LOGGER.exception(e)

        if successful_records:
            output_message = (
                f"Successfully returned details regarding record type {record_type} in {INTEGRATION_DISPLAY_NAME} "
                f"for the following ids: {', '.join([key for key in successful_records.keys()])}.\n"
            )
            siemplify.result.add_result_json(json_results)
            for identifier, details in successful_records.items():
                siemplify.result.add_data_table(
                    TABLE_NAME.format(record_id=identifier),
                    flat_dict_to_csv(details.to_table()),
                )

        if failed_records:
            output_message += (
                f"Action wasn't able to find details regarding record type {record_type} in "
                f"{INTEGRATION_DISPLAY_NAME} for the following ids: {', '.join(failed_records)}.\n"
            )

        if not successful_records:
            result = False
            output_message = "No records were found."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {GET_RECORD_DETAILS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {GET_RECORD_DETAILS_SCRIPT_NAME}. Reason: {e}"
        )

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
