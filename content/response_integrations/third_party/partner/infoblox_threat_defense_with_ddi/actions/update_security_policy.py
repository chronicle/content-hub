from __future__ import annotations
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from TIPCommon import extract_action_param
from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from ..core.constants import (
    UPDATE_SECURITY_POLICY_SCRIPT_NAME,
    RESULT_VALUE_TRUE,
    RESULT_VALUE_FALSE,
    COMMON_ACTION_ERROR_MESSAGE,
)
from ..core.datamodels import SecurityPolicy
from ..core.utils import (
    get_integration_params,
    parse_tags,
    parse_and_validate_int_list,
    validate_integer_param,
    get_nullable_field,
    is_empty_string,
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
    existing_data,
):
    payload = {
        "name": policy_name if policy_name else existing_data.get("name"),
        "description": get_nullable_field(description, existing_data.get("description")),
        "default_action": "action_allow",
        "block_dns_rebind_attack": (
            existing_data.get("block_dns_rebind_attack")
            if not block_dns_rebinding
            else block_dns_rebinding.lower() == "true"
        ),
        "safe_search": (
            existing_data.get("safe_search") if not safe_search else safe_search.lower() == "true"
        ),
        "network_lists": get_nullable_field(
            network_lists,
            existing_data.get("network_lists"),
            parser=lambda v: parse_and_validate_int_list(v, "Network Lists"),
        )
        or [],
        "dfps": get_nullable_field(
            dfps, existing_data.get("dfps"), parser=lambda v: parse_and_validate_int_list(v, "DFPS")
        )
        or [],
        "roaming_device_groups": get_nullable_field(
            roaming_device_groups,
            existing_data.get("roaming_device_groups"),
            parser=lambda v: parse_and_validate_int_list(v, "Roaming Device Groups"),
        )
        or [],
        "tags": get_nullable_field(tags, existing_data.get("tags", {}), parser=parse_tags),
    }
    if rules:
        if is_empty_string(rules):
            payload["rules"] = []
        else:
            payload["rules"] = parse_rules_param(rules)
    else:
        payload["rules"] = existing_data.get("rules", [])
    add_additional_params_to_payload(payload, additional_params)
    return payload


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_SECURITY_POLICY_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    security_policy_id = extract_action_param(
        siemplify, param_name="Security Policy ID", input_type=str, is_mandatory=True
    )
    policy_name = extract_action_param(
        siemplify, param_name="Policy Name", input_type=str, is_mandatory=False
    )
    description = extract_action_param(
        siemplify,
        param_name="Description",
        input_type=str,
        is_mandatory=False,
        remove_whitespaces=True,
    )
    rules = extract_action_param(
        siemplify, param_name="Rules", input_type=str, is_mandatory=False, remove_whitespaces=True
    )
    network_lists = extract_action_param(
        siemplify,
        param_name="Network Lists",
        input_type=str,
        is_mandatory=False,
        remove_whitespaces=True,
    )
    dfps = extract_action_param(
        siemplify, param_name="DFPS", input_type=str, is_mandatory=False, remove_whitespaces=True
    )
    roaming_device_groups = extract_action_param(
        siemplify,
        param_name="Roaming Device Groups",
        input_type=str,
        is_mandatory=False,
        remove_whitespaces=True,
    )
    block_dns_rebinding = extract_action_param(
        siemplify,
        param_name="Block DNS Rebinding",
        input_type=str,
        is_mandatory=False,
        remove_whitespaces=True,
    )
    safe_search = extract_action_param(
        siemplify,
        param_name="Safe Search",
        input_type=str,
        is_mandatory=False,
        remove_whitespaces=True,
    )
    tags = extract_action_param(
        siemplify, param_name="Tags", input_type=str, is_mandatory=False, remove_whitespaces=True
    )
    additional_params = extract_action_param(
        siemplify, param_name="Additional Parameters", input_type=str, is_mandatory=False
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        # Validate required param
        security_policy_id = validate_integer_param(
            security_policy_id, "Security Policy ID", zero_allowed=False, allow_negative=False
        )

        api_manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)
        # Fetch existing policy for populating fields if needed
        existing_policy = api_manager.get_security_policies(
            security_policy_filter=f"id=={security_policy_id}"
        )
        existing_data = None
        if isinstance(existing_policy, dict):
            results = existing_policy.get("results", existing_policy)
            if isinstance(results, list) and results:
                existing_data = results[0]
            elif isinstance(results, dict):
                existing_data = results
        if not existing_data:
            raise ValueError(f"Security Policy with ID {security_policy_id} not found.")

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
            existing_data,
        )

        siemplify.LOGGER.info(
            f"Payload for update_security_policy: {json.dumps(payload, indent=2)}"
        )
        response = api_manager.update_security_policy(security_policy_id, payload)
        result = response.get("results", response)
        output_message = f"Successfully updated security policy with ID '{security_policy_id}'."
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
            UPDATE_SECURITY_POLICY_SCRIPT_NAME, str(e)
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
