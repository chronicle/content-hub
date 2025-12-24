from __future__ import annotations

import json

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler
from TIPCommon.extraction import extract_action_param

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DEFAULT_LIMIT,
    LIST_NETWORK_INFO_SCRIPT_NAME,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import Network
from ..core.infoblox_exceptions import InfobloxException
from ..core.utils import (
    get_integration_params,
    validate_integer_param,
    validate_network_address,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_NETWORK_INFO_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, username, password, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    network = extract_action_param(
        siemplify,
        param_name="Network",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    extended_attributes = extract_action_param(
        siemplify,
        param_name="Extended Attributes",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        default_value=DEFAULT_LIMIT,
        is_mandatory=False,
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)
        validate_network_address(network)
        api_manager = APIManager(
            api_root, username, password, verify_ssl=verify_ssl, siemplify=siemplify
        )
        results = api_manager.list_network_info(network, extended_attributes, limit)

        siemplify.result.add_result_json(json.dumps(results, indent=4))
        if results:
            table_data = [Network(result).to_csv() for result in results[:MAX_TABLE_RECORDS]]
            siemplify.result.add_data_table(title="Networks", data_table=construct_csv(table_data))

            output_message = (
                f"Successfully found {len(results)} Network(s). "
                f"Showing up to {MAX_TABLE_RECORDS} in table"
            )

        else:
            output_message = "No Network found for the specified criteria."

    except (InfobloxException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(LIST_NETWORK_INFO_SCRIPT_NAME, str(e))
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"status: {status}")
    siemplify.LOGGER.info(f"result_value: {result_value}")
    siemplify.LOGGER.info(f"output_message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
