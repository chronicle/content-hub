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
    CREATE_RESPONSE_POLICY_ZONE_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import RPZone
from ..core.infoblox_exceptions import InfobloxException
from ..core.utils import (
    get_integration_params,
    validate_additional_params,
    validate_required_string,
)


def validate_fireeye_rule_mapping(fireeye_rule_mapping):
    """
    Validate fireeye_rule_mapping.
    """
    # Handle fireeye_rule_mapping
    try:
        fireeye_rule_mapping = json.loads(fireeye_rule_mapping)
        if not isinstance(fireeye_rule_mapping, dict):
            raise ValueError("Fireeye Rule Mapping must be a JSON object.")

        return fireeye_rule_mapping
    except Exception:
        raise ValueError("Fireeye Rule Mapping must be a JSON object.")


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_RESPONSE_POLICY_ZONE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, username, password, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    fqdn = extract_action_param(
        siemplify, param_name="FQDN", input_type=str, is_mandatory=True, print_value=True
    )
    substitute_name = extract_action_param(
        siemplify,
        param_name="Substitute Name",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    comment = extract_action_param(
        siemplify, param_name="Comment", input_type=str, is_mandatory=False, print_value=True
    )
    rpz_policy = extract_action_param(
        siemplify,
        param_name="RPZ Policy",
        input_type=str,
        is_mandatory=False,
        default_value="GIVEN",
        print_value=True,
    )
    rpz_severity = extract_action_param(
        siemplify,
        param_name="RPZ Severity",
        input_type=str,
        is_mandatory=False,
        default_value="MAJOR",
        print_value=True,
    )
    rpz_type = extract_action_param(
        siemplify,
        param_name="RPZ Type",
        input_type=str,
        is_mandatory=False,
        default_value="LOCAL",
        print_value=True,
    )
    fireeye_rule_mapping = extract_action_param(
        siemplify,
        param_name="Fireeye Rule Mapping",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    additional_parameters = extract_action_param(
        siemplify,
        param_name="Additional Parameters",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        validate_required_string(fqdn, "FQDN")
        additional_parameters = validate_additional_params(additional_parameters)

        if fireeye_rule_mapping:
            fireeye_rule_mapping = validate_fireeye_rule_mapping(fireeye_rule_mapping)

        api_manager = APIManager(
            api_root, username, password, verify_ssl=verify_ssl, siemplify=siemplify
        )
        result = api_manager.create_rp_zone(
            fqdn,
            rpz_policy,
            rpz_severity,
            rpz_type,
            substitute_name,
            comment,
            fireeye_rule_mapping,
            additional_parameters,
        )
        siemplify.result.add_result_json(json.dumps(result, indent=4))

        if result:
            table_data = [RPZone(result).to_csv()]
            siemplify.result.add_data_table(title="RP Zone", data_table=construct_csv(table_data))
            output_message = f"Created Response Policy Zone {fqdn}."
        else:
            result_value = RESULT_VALUE_FALSE
            output_message = "Failed to create Response Policy Zone."

    except (InfobloxException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            CREATE_RESPONSE_POLICY_ZONE_SCRIPT_NAME, str(e)
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
