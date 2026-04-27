from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.McAfeeMvisionEPOManager import McAfeeMvisionEPOManager
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import LIST_TAGS_SCRIPT_NAME, INTEGRATION_NAME, DEFAULT_LIMIT_TAGS


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_TAGS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    scopes = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Scopes",
        is_mandatory=True,
    )

    group_name = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Group Name"
    )

    # Parameters
    max_tags_to_return = extract_action_param(
        siemplify,
        param_name="Max Tags to Return",
        is_mandatory=False,
        input_type=int,
        default_value=DEFAULT_LIMIT_TAGS,
    )

    if max_tags_to_return <= 0:
        max_tags_to_return = DEFAULT_LIMIT_TAGS

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""
    json_results = []
    csv_table = []

    try:
        manager = McAfeeMvisionEPOManager(
            api_root,
            client_id,
            client_secret,
            scopes,
            group_name,
            verify_ssl,
            siemplify.LOGGER,
        )
        tags = manager.get_tags(max_tags_to_return)
        if tags:
            for tag in tags:
                csv_table.append(tag.to_table())
                json_results.append(tag.to_json())

            siemplify.result.add_result_json(json_results)
            siemplify.result.add_data_table(
                title="Available Tags", data_table=construct_csv(csv_table)
            )
            output_message += "Successfully listed available tags in McAfee Mvision ePO"

        else:
            result_value = False
            output_message += (
                "Action wasn’t able to list tags available in McAfee Mvision ePO"
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_TAGS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        output_message += f"Error executing action List Tags. Reason: {e}"
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
