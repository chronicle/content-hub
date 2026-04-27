from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.ArcsightManager import ArcsightManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.exceptions import ArcsightInvalidParamError
from ..core.constants import GET_ACTIVE_LIST_ENTRIES_SCRIPT_NAME, INTEGRATION_NAME

ENTRIES_TABLE_NAME = "Entries"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ACTIVE_LIST_ENTRIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
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
    ca_certificate_file = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    list_uuid = extract_action_param(
        siemplify, param_name="Active list UUID", print_value=True
    )
    list_name = extract_action_param(
        siemplify, param_name="Active list name", print_value=True
    )
    map_columns = extract_action_param(
        siemplify, param_name="Map Columns", print_value=True, input_type=bool
    )
    limit = extract_action_param(
        siemplify, param_name="Max Entries To Return", print_value=True, input_type=int
    )

    output_message = (
        "Successfully found entries in active list ‘{}’ from ArcSight.".format(
            f"with UUID {list_uuid}" if list_uuid else list_name
        )
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        if not list_uuid and not list_name:
            raise ArcsightInvalidParamError(
                "Error executing action ‘{}’. Reason: either ‘Active list UUID' or 'Active list "
                "name’ should be provided.".format(GET_ACTIVE_LIST_ENTRIES_SCRIPT_NAME)
            )

        fetched_by_uuid = bool(list_uuid)

        arcsight_manager = ArcsightManager(
            server_ip=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_file=ca_certificate_file,
        )
        arcsight_manager.login()

        if not list_uuid:
            list_uuid = arcsight_manager.get_activelist_uuid(list_name)

        result = arcsight_manager.get_activelist_entries_by_uuid(list_uuid, limit)

        if not result.enries_count:
            output_message = (
                "No entries were found in active list ‘{}’ from ArcSight.".format(
                    f"with UUID {list_uuid}" if fetched_by_uuid else list_name
                )
            )
            result_value = False
        else:
            siemplify.result.add_data_table(ENTRIES_TABLE_NAME, result.to_csv())
            siemplify.result.add_result_json(result.to_json(map_columns))
            result_value = True

        status = EXECUTION_STATE_COMPLETED
        arcsight_manager.logout()
    except Exception as e:
        output_message = (
            str(e)
            if isinstance(e, ArcsightInvalidParamError)
            else f"Error executing action {GET_ACTIVE_LIST_ENTRIES_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
