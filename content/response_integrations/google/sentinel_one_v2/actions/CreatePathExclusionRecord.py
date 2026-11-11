from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from sentinel_one_v2.core.constants import (
    CREATE_PATH_EXCLUSION_RECORD_SCRIPT_NAME,
    INTEGRATION_NAME,
    MODE_MAPPER,
    PRODUCT_NAME,
)
from sentinel_one_v2.core.exceptions import (
    SentinelOneV2ValidationError,
    SentinelOneV2AlreadyExistsError,
    SentinelOneV2BadRequestError,
)
from sentinel_one_v2.core.utils import is_folder_path
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_PATH_EXCLUSION_RECORD_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    file_directory = extract_action_param(
        siemplify, param_name="Path", is_mandatory=True, print_value=True
    )
    operation_system = extract_action_param(
        siemplify, param_name="Operation System", is_mandatory=True, print_value=True
    )
    site_ids = extract_action_param(siemplify, param_name="Site IDs", print_value=True)
    group_ids = extract_action_param(
        siemplify, param_name="Group IDs", print_value=True
    )
    account_ids = extract_action_param(
        siemplify, param_name="Account IDs", print_value=True
    )
    description = extract_action_param(
        siemplify, param_name="Description", print_value=True
    )
    add_to_global_list = extract_action_param(
        siemplify,
        param_name="Add to global exclusion list",
        input_type=bool,
        print_value=True,
    )
    include_subfolders = extract_action_param(
        siemplify, param_name="Include Subfolders", input_type=bool, print_value=True
    )
    mode = extract_action_param(
        siemplify, param_name="Mode", print_value=True, default_value="Suppress Alerts"
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = f"Successfully added path {file_directory} to the exclusion list in {PRODUCT_NAME}"
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        if (
            not site_ids
            and not group_ids
            and not account_ids
            and not add_to_global_list
        ):
            raise SentinelOneV2ValidationError(
                'at least one value should be provided for "Site IDs" or "Group IDs" or "Account IDs" parameters '
                'or "Add to global exclusion list" should be enabled.'
            )

        manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root, api_token=api_token, verify_ssl=verify_ssl
        )

        mode = mode or "Suppress Alerts"
        results = manager.create_path_exclusion(
            path=file_directory,
            os_type=operation_system,
            site_ids=site_ids,
            group_ids=group_ids,
            account_ids=account_ids,
            description=description,
            tenant=add_to_global_list,
            add_subfolders=include_subfolders,
            is_folder_path=is_folder_path(file_directory),
            mode=MODE_MAPPER[mode],
        )

        siemplify.result.add_result_json([res.to_json() for res in results])

    except SentinelOneV2AlreadyExistsError as e:
        output_message = f"The following path was already a part of exclusion list in {PRODUCT_NAME}: {file_directory}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = (
            f"Error executing action {CREATE_PATH_EXCLUSION_RECORD_SCRIPT_NAME}. Reason: {e}"
            if not isinstance(e, SentinelOneV2BadRequestError)
            else f"Action wasn't able to add path {file_directory} to the exclusion list. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
