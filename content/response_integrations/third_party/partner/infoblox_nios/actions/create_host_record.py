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
    CREATE_HOST_RECORD_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import Host
from ..core.infoblox_exceptions import InfobloxException
from ..core.utils import (
    get_integration_params,
    string_to_list,
    validate_additional_params,
    validate_ip_address_objects_params,
    validate_required_string,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_HOST_RECORD_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, username, password, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    name = extract_action_param(
        siemplify,
        param_name="Name",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    ipv4_addresses = extract_action_param(
        siemplify,
        param_name="IPv4 Addresses",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    ipv6_addresses = extract_action_param(
        siemplify,
        param_name="IPv6 Addresses",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    view = extract_action_param(
        siemplify,
        param_name="View",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        default_value="default",
    )
    comment = extract_action_param(
        siemplify, param_name="Comment", input_type=str, is_mandatory=False, print_value=True
    )
    aliases = extract_action_param(
        siemplify, param_name="Aliases", input_type=str, is_mandatory=False, print_value=True
    )
    additional_params = extract_action_param(
        siemplify,
        param_name="Additional Parameters",
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
    configure_for_dns = extract_action_param(
        siemplify,
        param_name="Configure for DNS",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
        default_value=True,
    )
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        validate_required_string(name, "Name")
        ipv4_addresses = validate_ip_address_objects_params(ipv4_addresses, "IPv4 Address")
        ipv6_addresses = validate_ip_address_objects_params(ipv6_addresses, "IPv6 Address")
        additional_params = validate_additional_params(additional_params)
        aliases_list = string_to_list(aliases)

        api_manager = APIManager(
            api_root, username, password, verify_ssl=verify_ssl, siemplify=siemplify
        )
        results = api_manager.create_host_record(
            name,
            ipv4_addresses,
            ipv6_addresses,
            view,
            comment,
            aliases_list,
            configure_for_dns,
            extended_attributes,
            additional_params,
        )

        siemplify.result.add_result_json(json.dumps(results, indent=4))
        if results:
            table_data = [Host(results).to_csv()]
            siemplify.result.add_data_table(title="Hosts", data_table=construct_csv(table_data))
            output_message = f"Created Host Record with Name {name}."
        else:
            result_value = RESULT_VALUE_FALSE
            output_message = "Failed to create Host Record."

    except (InfobloxException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(CREATE_HOST_RECORD_SCRIPT_NAME, str(e))
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
