from __future__ import annotations
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from TIPCommon import extract_action_param

from ..core.datamodels import SecurityPolicy
from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from ..core.constants import (
    CREATE_SECURITY_POLICY_SCRIPT_NAME,
    RESULT_VALUE_TRUE,
    RESULT_VALUE_FALSE,
    COMMON_ACTION_ERROR_MESSAGE,
)
from ..core.utils import (
    get_integration_params,
    validate_required_string,
    parse_tags,
    parse_and_validate_int_list,
    add_additional_params_to_payload,
    parse_rules_param,
)


def create_payload_security_policy(
    policy_name,
    description,
    block_dns_rebinding,
    safe_search,
    network_lists,
    dfps,
    roaming_device_groups,
    rules,
    tags,
    additional_params,
):
    payload = {
        "name": policy_name,
        "description": description,
        "block_dns_rebind_attack": block_dns_rebinding.lower() == "true",
        "safe_search": safe_search.lower() == "true",
        "network_lists": parse_and_validate_int_list(network_lists, "Network Lists"),
        "dfps": parse_and_validate_int_list(dfps, "DFPS"),
        "roaming_device_groups": parse_and_validate_int_list(
            roaming_device_groups, "Roaming Device Groups"
        ),
        "tags": parse_tags(tags),
        "rules": parse_rules_param(rules),
    }

    add_additional_params_to_payload(payload, additional_params)
    return payload


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_SECURITY_POLICY_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    policy_name = extract_action_param(
        siemplify, param_name="Policy Name", input_type=str, is_mandatory=True
    )
    description = extract_action_param(
        siemplify, param_name="Description", input_type=str, is_mandatory=False
    )
    rules = extract_action_param(siemplify, param_name="Rules", input_type=str, is_mandatory=False)
    network_lists = extract_action_param(
        siemplify, param_name="Network Lists", input_type=str, is_mandatory=False
    )
    dfps = extract_action_param(siemplify, param_name="DFPS", input_type=str, is_mandatory=False)
    roaming_device_groups = extract_action_param(
        siemplify, param_name="Roaming Device Groups", input_type=str, is_mandatory=False
    )
    block_dns_rebinding = extract_action_param(
        siemplify,
        param_name="Block DNS Rebinding",
        input_type=str,
        default_value="false",
        is_mandatory=False,
    )
    safe_search = extract_action_param(
        siemplify,
        param_name="Safe Search",
        input_type=str,
        default_value="false",
        is_mandatory=False,
    )
    tags = extract_action_param(siemplify, param_name="Tags", input_type=str, is_mandatory=False)
    additional_params = extract_action_param(
        siemplify, param_name="Additional Parameters", input_type=str, is_mandatory=False
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        # Validations
        validate_required_string(policy_name, "Policy Name")

        # Prepare payload
        payload = create_payload_security_policy(
            policy_name,
            description,
            block_dns_rebinding,
            safe_search,
            network_lists,
            dfps,
            roaming_device_groups,
            rules,
            tags,
            additional_params,
        )

        api_manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)
        response = api_manager.create_security_policy(payload)
        result = response.get("results", response)
        output_message = f"Successfully created security policy '{policy_name}'."
        siemplify.result.add_result_json(json.dumps(result, indent=4))

        # Table view
        policy = SecurityPolicy(result)
        siemplify.result.add_data_table("Security Policy Details", construct_csv([policy.to_csv()]))
    except (InfobloxException, ValueError) as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            CREATE_SECURITY_POLICY_SCRIPT_NAME, str(e)
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
