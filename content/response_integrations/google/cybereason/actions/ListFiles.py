from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.CybereasonManager import CybereasonManager
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, LIST_FILES_SCRIPT_NAME
from ..core.utils import (
    string_to_multi_value,
    get_supported_file_hashes,
    validate_fields_to_return,
    validate_positive_integer,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_FILES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
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
        default_value=False,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate Base64",
    )

    file_hashes = string_to_multi_value(
        extract_action_param(siemplify, param_name="File Hash", print_value=True)
    )
    limit = extract_action_param(
        siemplify,
        param_name="Results Limit",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    fields_to_return = string_to_multi_value(
        extract_action_param(siemplify, param_name="Fields To Return", print_value=True)
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    csv_output, json_results = [], {}
    output_message = ""
    result_value = 0

    try:
        manager = CybereasonManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_b64=ca_certificate,
            force_check_connectivity=True,
        )
        validate_positive_integer(limit)
        status = EXECUTION_STATE_COMPLETED
        result_files = []
        valid_field_to_return, invalid_field_to_return = validate_fields_to_return(
            fields_to_return
        )

        if not valid_field_to_return and invalid_field_to_return:
            raise Exception(
                "none of the provided fields are valid. Please check the spelling."
            )
        elif invalid_field_to_return:
            output_message += f'The following fields are invalid: {", ".join(invalid_field_to_return)}.\n'
        supported_file_hashes = get_supported_file_hashes(siemplify, file_hashes)
        if supported_file_hashes:
            for file_hash in supported_file_hashes:
                files = manager.get_files(
                    file_hash=file_hash,
                    limit=limit,
                    fields_to_return=valid_field_to_return,
                )
                result_files.extend(files)
        else:
            files = manager.get_files(limit=limit, fields_to_return=fields_to_return)
            result_files.extend(files)
        if result_files:
            result_files = result_files[:limit]
            csv_output = [
                file_obj.to_csv(valid_field_to_return) for file_obj in result_files
            ]
            json_results = [file_obj.to_json() for file_obj in result_files]
            result_value = len(result_files)
            output_message += (
                "Successufully retrieved information about hashes from Cybereason."
            )
        else:
            output_message += "No information about hashes was found."

        if csv_output:
            siemplify.result.add_data_table("Files", construct_csv(csv_output))
        if json_results:
            siemplify.result.add_result_json(json_results)

    except Exception as e:
        output_message = f"Error executing action {LIST_FILES_SCRIPT_NAME}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = 0

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  num_of_files: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
