from __future__ import annotations
import json

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param
from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from ..core.constants import (
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    COMMON_ACTION_ERROR_MESSAGE,
    UPDATE_CUSTOM_LIST_ITEMS_SCRIPT_NAME,
)
from ..core.utils import (
    validate_integer_param,
    validate_indicators,
    string_to_list,
    get_integration_params,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_CUSTOM_LIST_ITEMS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    custom_list_id = extract_action_param(
        siemplify,
        param_name="Custom List ID",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    action = extract_action_param(
        siemplify,
        param_name="Action",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    items_str = extract_action_param(
        siemplify,
        param_name="Items",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        custom_list_id = validate_integer_param(
            custom_list_id, "Custom List ID", zero_allowed=False, allow_negative=False
        )
        items = string_to_list(items_str)
        if not items:
            raise InfobloxException("Items list must not be empty.")
        validate_indicators(items)

        api_manager = APIManager(api_root, api_key, verify_ssl, siemplify)
        response = api_manager.update_custom_list_items(custom_list_id, action, items)
        added = response.get("inserted_items", [])
        removed = response.get("deleted_items", [])
        updated = response.get("updated_items", [])
        output_message = (
            f"Action '{action}' executed successfully on Custom List ID {custom_list_id}."
        )
        if added:
            output_message += f" Added: {len(added)}."
        if removed:
            output_message += f" Removed: {len(removed)}."
        if updated:
            output_message += f" Updated: {len(updated)}."
        if not (added or removed or updated):
            output_message = "No items were added, removed, or updated."
        siemplify.result.add_result_json(json.dumps(response))

    except (InfobloxException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(UPDATE_CUSTOM_LIST_ITEMS_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"result_value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
