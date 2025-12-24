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
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    COMMON_ACTION_ERROR_MESSAGE,
    CREATE_CUSTOM_LIST_SCRIPT_NAME,
)
from ..core.utils import (
    validate_required_string,
    validate_indicators,
    string_to_list,
    parse_tags,
    get_integration_params,
    clean_params,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_CUSTOM_LIST_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    name = extract_action_param(
        siemplify,
        param_name="Name",
        input_type=str,
        is_mandatory=True,
    )
    type_ = extract_action_param(
        siemplify,
        param_name="Type",
        input_type=str,
        default_value="custom_list",
        is_mandatory=True,
    )
    items_str = extract_action_param(
        siemplify,
        param_name="Items",
        input_type=str,
        is_mandatory=False,
    )
    description = extract_action_param(
        siemplify,
        param_name="Description",
        input_type=str,
        is_mandatory=False,
    )
    confidence_level = extract_action_param(
        siemplify,
        param_name="Confidence Level",
        input_type=str,
        default_value="High",
        is_mandatory=False,
    ).upper()
    threat_level = extract_action_param(
        siemplify,
        param_name="Threat Level",
        input_type=str,
        default_value="Low",
        is_mandatory=False,
    ).upper()
    tags_str = extract_action_param(
        siemplify,
        param_name="Tags",
        input_type=str,
        is_mandatory=False,
    )
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        items = string_to_list(items_str)
        tags = parse_tags(tags_str) if tags_str else None
        validate_required_string(name, "Name")
        validate_required_string(type_, "Type")
        if items:
            validate_indicators(items)

        api_manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)
        payload = {
            "name": name,
            "type": type_,
            "items": items if items else [],
        }
        optional_fields = {
            "description": description,
            "confidence_level": confidence_level,
            "threat_level": threat_level,
            "tags": tags,
        }
        payload.update(clean_params(optional_fields))
        response = api_manager.create_custom_list(payload)
        result = response.get("results", response)
        output_message = f"Successfully created custom list '{name}'."
        siemplify.result.add_result_json(json.dumps(result, indent=4))

        # Table view (using datamodel)
        custom_list = CustomList(result)
        siemplify.result.add_data_table(
            "Custom List Details", construct_csv([custom_list.to_csv()])
        )

    except (InfobloxException, ValueError) as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(CREATE_CUSTOM_LIST_SCRIPT_NAME, str(e))
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
