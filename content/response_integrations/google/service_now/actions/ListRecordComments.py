from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import (
    INTEGRATION_NAME,
    LIST_RECORD_COMMENTS_SCRIPT_NAME,
    PRODUCT_NAME,
    RECORD_COMMENT_TYPES,
)
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_RECORD_COMMENTS_SCRIPT_NAME

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=False,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        print_value=False,
    )
    default_incident_table = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Incident Table",
        print_value=True,
        default_value=DEFAULT_TABLE,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        print_value=False,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        print_value=False,
    )
    refresh_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Refresh Token",
        print_value=False,
    )
    use_oauth = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use Oauth Authentication",
        default_value=False,
        input_type=bool,
    )
    # Parameters
    table_name = extract_action_param(
        siemplify, param_name="Table Name", is_mandatory=True, print_value=True
    )
    ticket_sys_id = extract_action_param(
        siemplify, param_name="Record Sys ID", is_mandatory=True, print_value=True
    )
    data_type = extract_action_param(
        siemplify, param_name="Type", is_mandatory=True, print_value=True
    )
    max_results_to_return = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        is_mandatory=False,
        print_value=True,
        input_type=int,
        default_value=50,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED

    try:
        if max_results_to_return < 1:
            raise Exception("Max Results To Return parameter should be a positive number.")

        manager = ServiceNowManager(
            api_root=api_root,
            username=username,
            password=password,
            default_incident_table=default_incident_table,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            use_oauth=use_oauth,
        )

        results = manager.get_record_comments(
            table_name=table_name,
            type=data_type,
            record_id=ticket_sys_id,
            limit=max_results_to_return,
        )
        obj_type = RECORD_COMMENT_TYPES.get(data_type)
        obj_type = obj_type if obj_type == "comments" else "work notes"
        if results:
            result_value = True
            siemplify.result.add_result_json([res.to_json() for res in results])
            output_message = f"Successfully returned {obj_type} related to {table_name} with Sys ID {ticket_sys_id} in {PRODUCT_NAME}."
        else:
            result_value = True
            output_message = f"No {obj_type} were found for {table_name} with Sys ID {ticket_sys_id} in {PRODUCT_NAME}."

    except Exception as err:
        output_message = (
            f'Error executing action "{LIST_RECORD_COMMENTS_SCRIPT_NAME}". Reason: {err}'
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
