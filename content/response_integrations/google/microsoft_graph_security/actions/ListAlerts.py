from __future__ import annotations
import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv

from core.constants import (
    DEFAULT_API_PAGINATION_LIMIT,
    INTEGRATION_NAME,
    LIST_ALERTS_SCRIPT_NAME,
)
from core.exceptions import ActionParameterValidationError
from core.utils import GraphSecurityManagerConfig, init_graph_security_manager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_ALERTS_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        input_type=str,
    )
    secret_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret ID",
        is_mandatory=False,
        input_type=str,
    )
    certificate_path = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Certificate Path",
        is_mandatory=False,
        input_type=str,
    )
    certificate_password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Certificate Password",
        is_mandatory=False,
        input_type=str,
    )
    tenant = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Tenant",
        is_mandatory=True,
        input_type=str,
    )
    use_v2_api = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use V2 API",
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
        print_value=True,
    )

    filter_key = extract_action_param(
        siemplify,
        param_name="Filter Key",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    filter_logic = extract_action_param(
        siemplify,
        param_name="Filter Logic",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    filter_value = extract_action_param(
        siemplify,
        param_name="Filter Value",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    max_records_to_return = extract_action_param(
        siemplify,
        param_name="Max Records To Return",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_results = {}
    result_value = json.dumps([])
    config = GraphSecurityManagerConfig(
        client_id=client_id,
        secret_id=secret_id,
        certificate_path=certificate_path,
        certificate_password=certificate_password,
        tenant=tenant,
        verify_ssl=verify_ssl,
        chronicle_soar=siemplify,
    )

    filter_dict = None
    if max_records_to_return is None:
        max_records_to_return = DEFAULT_API_PAGINATION_LIMIT

    try:
        if max_records_to_return <= 0:
            raise ActionParameterValidationError(
                f"Invalid value was provided for “Max Records to Return”"
                f":{max_records_to_return}. Positive number should be provided”."
            )

        if filter_value:
            filter_dict = {
                "key": filter_key if filter_key != "Not Specified" else None,
                "logic": filter_logic if filter_logic != "Not Specified" else None,
                "value": filter_value,
            }
            filter_params_invalid = any(filter_dict.values()) and not all(
                filter_dict.values()
            )
            if filter_params_invalid:
                raise ActionParameterValidationError(
                    "you need to select a field from "
                    'both the “Filter Key” and the "Filter Logic" parameter.'
                )

        siemplify.LOGGER.info("Connecting to Microsoft Graph Security.")
        mtm = init_graph_security_manager(
            config=config,
            use_v2_api=use_v2_api,
        )
        siemplify.LOGGER.info("Connected successfully.")

        siemplify.LOGGER.info("Fetching alerts.")
        alerts = mtm.list_alerts(
            filter_dict=filter_dict, max_alerts=max_records_to_return
        )

        if alerts:
            siemplify.LOGGER.info(f"Found {len(alerts)} alerts.")

            siemplify.LOGGER.info("Adding alerts table.")
            siemplify.result.add_data_table(
                "Alerts", construct_csv([alert.as_csv() for alert in alerts])
            )

            json_results = [alert.raw_data for alert in alerts]
            output_message = f"Successfully found {len(alerts)} alerts for the provided criteria in Microsoft Graph."
            result_value = json.dumps([alert.raw_data for alert in alerts])

        else:
            siemplify.LOGGER.info(
                "No alerts were found for the provided criteria in Microsoft Graph."
            )
            output_message = (
                "No alerts were found for the provided criteria in Microsoft Graph"
            )

        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        siemplify.LOGGER.error(f"Error executing action “List Alerts”. Reason: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action “List Alerts”. Reason: {e}"

    siemplify.result.add_result_json(json_results)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
