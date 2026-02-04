from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import INTEGRATION_NAME, UPDATE_RECORD_SCRIPT_NAME
from ..core.exceptions import ServiceNowNotFoundException, ServiceNowTableNotFoundException
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_RECORD_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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
        remove_whitespaces=False,
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
        remove_whitespaces=False,
        print_value=False,
    )
    refresh_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Refresh Token",
        remove_whitespaces=False,
        print_value=False,
    )
    use_oauth = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use Oauth Authentication",
        default_value=False,
        input_type=bool,
    )
    # Action parameters
    table_name = extract_action_param(
        siemplify,
        param_name="Table Name",
        print_value=True,
        default_value=default_incident_table,
    )
    record_sys_id = extract_action_param(
        siemplify, param_name="Record Sys ID", print_value=True, is_mandatory=True
    )
    json_data = extract_action_param(
        siemplify, param_name="Object Json Data", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED

    try:
        try:
            json_data = json.loads(json_data)
        except (json.JSONDecodeError, TypeError):
            error_message = 'Invalid JSON provided for "Object Json Data" parameter'
            siemplify.LOGGER.error(error_message)
            raise ValueError(error_message)

        service_now_manager = ServiceNowManager(
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
        ticket = service_now_manager.update_object(json_data, record_sys_id, table_name)
        not_used_custom_fields = set(json_data) - set(ticket.to_json())

        output_message = (
            f"Successfully updated record with Sys ID {record_sys_id} "
            f'in table "{table_name or default_incident_table}".'
        )
        result_value = ticket.sys_id
        if not_used_custom_fields:
            output_message += (
                f"\nThe following fields were not processed, when updating a "
                f"record: {', '.join(not_used_custom_fields)}"
            )
        siemplify.result.add_result_json(ticket.to_json())

    except ServiceNowNotFoundException as e:
        output_message = (
            str(e)
            if isinstance(e, ServiceNowTableNotFoundException)
            else (f"Record with Sys ID '{record_sys_id}' was not found in table '{table_name}'")
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = f"General error performing action {UPDATE_RECORD_SCRIPT_NAME}. Reason: {e}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
