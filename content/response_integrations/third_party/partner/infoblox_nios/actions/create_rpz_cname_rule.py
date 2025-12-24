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
    CREATE_RPZ_CNAME_RULE_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import RPZCNAMERule
from ..core.infoblox_exceptions import InfobloxException
from ..core.utils import (
    get_integration_params,
    validate_additional_params,
    validate_required_string,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_RPZ_CNAME_RULE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, username, password, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    name = extract_action_param(
        siemplify, param_name="Name", input_type=str, is_mandatory=True, print_value=True
    )
    rp_zone = extract_action_param(
        siemplify, param_name="RP Zone", input_type=str, is_mandatory=True, print_value=True
    )
    comment = extract_action_param(
        siemplify, param_name="Comment", input_type=str, is_mandatory=False, print_value=True
    )
    view = extract_action_param(
        siemplify,
        param_name="View",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        default_value="default",
    )
    additional_params = extract_action_param(
        siemplify,
        param_name="Additional Parameters",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    substitute_name = extract_action_param(
        siemplify,
        param_name="Substitute Name",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    rule_type = extract_action_param(
        siemplify,
        param_name="Rule Type",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        default_value="Block (No data)",
    )
    object_type = extract_action_param(
        siemplify,
        param_name="Object Type",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        default_value="Domain Name",
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        validate_required_string(rp_zone, "RP Zone")
        validate_required_string(name, "Name")
        additional_params = validate_additional_params(additional_params)

        api_manager = APIManager(
            api_root, username, password, verify_ssl=verify_ssl, siemplify=siemplify
        )
        result = api_manager.create_rpz_cname_rule(
            rule_type, object_type, name, rp_zone, comment, substitute_name, view, additional_params
        )
        siemplify.result.add_result_json(json.dumps(result, indent=4))

        if result:
            table_data = [RPZCNAMERule(result, rule_type).to_csv()]
            siemplify.result.add_data_table(
                title="RPZ CNAME Rule", data_table=construct_csv(table_data)
            )

            output_message = f"Created RPZ CNAME rule {name}."

        else:
            result_value = RESULT_VALUE_FALSE
            output_message = "Failed to create RPZ CNAME rule."

    except (InfobloxException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            CREATE_RPZ_CNAME_RULE_SCRIPT_NAME, str(e)
        )
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
