from __future__ import annotations
import json
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CybereasonManager import CybereasonManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import INTEGRATION_NAME, EXECUTE_SIMPLE_INVESTIGATION_SEARCH_SCRIPT_NAME
from ..core.utils import convert_comma_separated_to_list
from ..core.exceptions import (
    CybereasonSuccessWithFailureError,
    CybereasonClientError,
    CybereasonInvalidQueryError,
    CybereasonInvalidFormatError,
)


TABLE_NAME = "Search Results"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_SIMPLE_INVESTIGATION_SEARCH_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # configuration parameters
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

    # action parameters
    query_filters_json_string = extract_action_param(
        siemplify, param_name="Query Filters JSON", is_mandatory=True, print_value=True
    )
    fields_to_return_string = extract_action_param(
        siemplify, param_name="Fields To Return", is_mandatory=True, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        input_type=int,
        default_value=50,
        print_value=True,
    )

    fields_to_return = convert_comma_separated_to_list(fields_to_return_string)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = f"No data was found for the provided query in {INTEGRATION_NAME}."

    try:
        if limit < 1:
            raise Exception(
                f'Invalid value was provided for "Max Results To Return": {limit}. Positive number '
                f"should be provided."
            )

        try:
            query_filters_json = json.loads(query_filters_json_string)
        except Exception:
            raise Exception(
                'Invalid JSON provided in the parameter "Query Filters JSON". Please check the structure.'
            )

        manager = CybereasonManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_b64=ca_certificate,
            logger=siemplify.LOGGER,
            force_check_connectivity=True,
        )

        try:
            results = manager.execute_custom_query(
                query_filters_json, fields_to_return, limit
            )
        except (
            CybereasonSuccessWithFailureError,
            CybereasonClientError,
            CybereasonInvalidFormatError,
        ):
            raise Exception(
                "Invalid query provided. Please double check the structure and syntax."
            )
        except CybereasonInvalidQueryError as e:
            raise Exception(
                f"Invalid query provided. Please double check the structure and syntax. {str(e) if e else ''}"
            )

        if results:
            siemplify.result.add_data_table(
                TABLE_NAME, construct_csv([result.to_table() for result in results])
            )
            siemplify.result.add_result_json([result.to_json() for result in results])
            output_message = f"Successfully executed query in {INTEGRATION_NAME}."

    except Exception as e:
        output_message = f'Error executing action "{EXECUTE_SIMPLE_INVESTIGATION_SEARCH_SCRIPT_NAME}". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
