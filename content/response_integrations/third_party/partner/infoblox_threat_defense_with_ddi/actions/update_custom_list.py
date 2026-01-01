from __future__ import annotations
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from TIPCommon import extract_action_param
from ..core.datamodels import CustomList
from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from ..core.constants import (
    RESULT_VALUE_TRUE,
    RESULT_VALUE_FALSE,
    COMMON_ACTION_ERROR_MESSAGE,
    UPDATE_CUSTOM_LIST_SCRIPT_NAME,
)
from ..core.utils import (
    validate_integer_param,
    get_integration_params,
    parse_tags,
    get_nullable_field,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_CUSTOM_LIST_SCRIPT_NAME
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
    name = extract_action_param(
        siemplify,
        param_name="Name",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    description = extract_action_param(
        siemplify,
        param_name="Description",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    confidence_level = extract_action_param(
        siemplify,
        param_name="Confidence Level",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    threat_level = extract_action_param(
        siemplify,
        param_name="Threat Level",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    tags_str = extract_action_param(
        siemplify,
        param_name="Tags",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        custom_list_id = validate_integer_param(
            custom_list_id, "Custom List ID", zero_allowed=False, allow_negative=False
        )
        api_manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)

        # Fetch existing custom list to inherit fields if not provided
        existing = api_manager.get_custom_list(custom_list_id=custom_list_id)
        existing = existing["results"]
        payload = {
            "name": name if name else existing.get("name"),
            "description": get_nullable_field(description, existing.get("description", "")),
            "confidence_level": (
                existing.get("confidence_level")
                if not confidence_level or str(confidence_level) == "None"
                else confidence_level.upper()
            ),
            "threat_level": (
                existing.get("threat_level")
                if not threat_level or str(threat_level) == "None"
                else threat_level.upper()
            ),
            "items": existing.get("items", []),
            "tags": get_nullable_field(tags_str, existing.get("tags", {}), parser=parse_tags),
        }

        response = api_manager.update_custom_list(custom_list_id, payload)
        result = response.get("results", response)
        output_message = f"Successfully updated custom list with ID '{custom_list_id}'."
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
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(UPDATE_CUSTOM_LIST_SCRIPT_NAME, str(e))
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
