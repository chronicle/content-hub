from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import CREATE_RECORD_SCRIPT_NAME, INTEGRATION_NAME
from ..core.exceptions import ServiceNowNotFoundException
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_RECORD_SCRIPT_NAME

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
        siemplify,
        param_name="Table Name",
        print_value=True,
        default_value=default_incident_table,
    )
    json_data = extract_action_param(siemplify, param_name="Object Json Data", print_value=True)

    try:
        json_data = json.loads(json_data)
    except:
        siemplify.LOGGER.info(
            'Provided "Object Json Data" is not valid JSON. Using empty json instead'
        )
        json_data = {}

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED

    try:
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
        obj, not_used_custom_keys = service_now_manager.create_object(
            json_data, table_name=table_name
        )

        if obj.is_empty():
            output_message = f"Failed to create ServiceNow record in {table_name}."
        else:
            result_value = obj.sys_id
            siemplify.result.add_result_json(obj.to_json())

            output_message = (
                f'Successfully created record with Sys ID {obj.sys_id} in table "{table_name}".'
            )
            if not_used_custom_keys:
                output_message += f"\nThe following fields were not processed, when creating a record: {', '.join(not_used_custom_keys)}"

    except ServiceNowNotFoundException as e:
        output_message = str(e)
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = f"General error performing action {CREATE_RECORD_SCRIPT_NAME}. Reason: {e}"
        result_value = False
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
