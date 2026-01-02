from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from TIPCommon import extract_action_param

from ..core.datamodels import NetworkList
from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from ..core.constants import (
    GET_NETWORK_LIST_SCRIPT_NAME,
    RESULT_VALUE_TRUE,
    RESULT_VALUE_FALSE,
    COMMON_ACTION_ERROR_MESSAGE,
    DEFAULT_OFFSET,
    DEFAULT_LIMIT,
    MAX_TABLE_RECORDS,
)
from ..core.utils import validate_integer_param, get_integration_params


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_NETWORK_LIST_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    network_list_id = extract_action_param(
        siemplify,
        param_name="Network List ID",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    security_network_filter = extract_action_param(
        siemplify,
        param_name="Security Network Filter",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    offset = extract_action_param(
        siemplify,
        param_name="Offset",
        input_type=str,
        default_value=DEFAULT_OFFSET,
        is_mandatory=False,
    )

    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        default_value=DEFAULT_LIMIT,
        is_mandatory=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    try:
        # Parameter Validation
        if network_list_id:
            network_list_id = validate_integer_param(
                network_list_id,
                "Network List ID",
                zero_allowed=False,
                allow_negative=False,
            )
        offset = validate_integer_param(offset, "Offset", zero_allowed=True, allow_negative=False)
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)

        infoblox_manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)
        response = infoblox_manager.get_network_list(
            network_list_id=network_list_id,
            network_filter=security_network_filter,
            offset=offset,
            limit=limit,
        )

        if isinstance(response.get("results", []), dict):
            response["results"] = [response.get("results")]

        siemplify.result.add_result_json(response)
        # Prepare table output for SOAR (using datamodel)
        if response.get("results", []):
            table_data = [
                NetworkList(r).to_csv() for r in response.get("results", [])[:MAX_TABLE_RECORDS]
            ]
            siemplify.result.add_data_table("Network List", construct_csv(table_data))
            output_message = (
                f"Successfully retrieved {len(response.get('results', []))} network list(s). "
                f"Showing up to {MAX_TABLE_RECORDS} in table."
            )
        else:
            output_message = "No network lists found."

    except InfobloxException as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(GET_NETWORK_LIST_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"result_value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
