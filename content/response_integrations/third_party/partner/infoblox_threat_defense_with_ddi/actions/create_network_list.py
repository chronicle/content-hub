from __future__ import annotations
import json

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from TIPCommon import extract_action_param

from ..core.datamodels import NetworkList
from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from ..core.constants import (
    CREATE_NETWORK_LIST_SCRIPT_NAME,
    RESULT_VALUE_TRUE,
    RESULT_VALUE_FALSE,
    COMMON_ACTION_ERROR_MESSAGE,
)
from ..core.utils import get_integration_params, validate_required_string, string_to_list


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_NETWORK_LIST_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    name = extract_action_param(siemplify, param_name="Name", input_type=str, is_mandatory=True)
    items_str = extract_action_param(
        siemplify, param_name="Items", input_type=str, is_mandatory=True
    )
    description = extract_action_param(
        siemplify, param_name="Description", input_type=str, is_mandatory=False
    )

    output_message = ""
    result_value = RESULT_VALUE_TRUE
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        # Validate required parameters
        validate_required_string(name, "Name")
        validate_required_string(items_str, "Items")
        items = string_to_list(items_str)

        api_manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)
        response = api_manager.create_network_list(name=name, items=items, description=description)
        network_list = NetworkList(response.get("results"))
        siemplify.result.add_result_json(json.dumps(response.get("results"), indent=4))
        siemplify.result.add_data_table(
            "Network List Details", construct_csv([network_list.to_csv()])
        )
        output_message = f"Successfully created network list '{name}'."

    except (InfobloxException, ValueError) as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(CREATE_NETWORK_LIST_SCRIPT_NAME, e)
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
