from __future__ import annotations
import json

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from TIPCommon import extract_action_param

from ..core.datamodels import CustomList
from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from ..core.constants import (
    GET_CUSTOM_LIST_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    COMMON_ACTION_ERROR_MESSAGE,
    DEFAULT_OFFSET,
    DEFAULT_LIMIT,
    MAX_TABLE_RECORDS,
)
from ..core.utils import validate_integer_param, get_integration_params


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_CUSTOM_LIST_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    custom_list_id = extract_action_param(
        siemplify,
        param_name="Custom List ID",
        input_type=str,
        is_mandatory=False,
    )
    name = extract_action_param(
        siemplify,
        param_name="Name",
        input_type=str,
        is_mandatory=False,
    )
    type_ = extract_action_param(
        siemplify,
        param_name="Type",
        input_type=str,
        default_value="custom_list",
        is_mandatory=False,
    )
    tag_filter = extract_action_param(
        siemplify,
        param_name="Tag Filter",
        input_type=str,
        is_mandatory=False,
    )
    tag_sort_filter = extract_action_param(
        siemplify,
        param_name="Tag Sort Filter",
        input_type=str,
        is_mandatory=False,
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

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = "No custom lists found."
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        offset = validate_integer_param(offset, "Offset", zero_allowed=True, allow_negative=False)
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)
        if custom_list_id is not None:
            custom_list_id = validate_integer_param(
                custom_list_id, "Custom List ID", zero_allowed=True, allow_negative=False
            )

        api_manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)
        response = api_manager.get_custom_list(
            custom_list_id=custom_list_id,
            name=name,
            type_=type_,
            tag_filter=tag_filter,
            tag_sort_filter=tag_sort_filter,
            offset=offset,
            limit=limit,
        )
        results = response.get("results", response)
        table_results = []
        if isinstance(results, dict):
            results = [results]
            response["results"] = results
        for item in results[:MAX_TABLE_RECORDS]:
            model = CustomList(item)
            table_results.append(model.to_csv())
        siemplify.result.add_result_json(json.dumps(response, indent=4))
        # Table view (using datamodel)
        if table_results:
            siemplify.result.add_data_table(
                title="Custom List Details", data_table=construct_csv(table_results)
            )
            output_message = (
                f"Successfully retrieved {len(results)} custom list(s). "
                f"Showing up to {MAX_TABLE_RECORDS} in table."
            )
        else:
            siemplify.LOGGER.info("No custom lists found to display in table view.")

    except (InfobloxException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(GET_CUSTOM_LIST_SCRIPT_NAME, str(e))
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
