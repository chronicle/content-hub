from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import (
    API_VERSION_2_1,
    API_VERSION_2_2,
    API_VERSION_2_5,
    COMMON_ACTION_ERROR_MESSAGE,
    INTEGRATION_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    SEARCH_HOSTS_SCRIPT_NAME,
)
from ..core.UtilsManager import extract_fields, validate_limit_param, validator
from ..core.VectraQUXExceptions import InvalidIntegerException
from ..core.VectraQUXManager import VectraQUXManager


def remove_api_version_from_url(host):
    if host.get("url"):
        host["url"] = (
            host.get("url", "")
            .replace(API_VERSION_2_5, "")
            .replace(API_VERSION_2_1, "")
            .replace(API_VERSION_2_2, "")
        )
    if host.get("host_url"):
        host["host_url"] = (
            host.get("host_url", "")
            .replace(API_VERSION_2_5, "")
            .replace(API_VERSION_2_1, "")
            .replace(API_VERSION_2_2, "")
        )
    if host.get("detection_set"):
        host["detection_set"] = [
            url.replace(API_VERSION_2_5, "")
            .replace(API_VERSION_2_1, "")
            .replace(API_VERSION_2_2, "")
            for url in host.get("detection_set", "")
        ]
    return host


@output_handler
def main():
    """Main function for the Hosts Search action.

    This function will query the Vectra API for hosts based on the parameters
    provided by the user.

    Parameters
    ----------
    - API Root: The root URL of the Vectra API
    - API Token: The API token to use for authentication
    - Verify SSL: Whether or not to verify the SSL certificate of the API
    - Ordering: The field to order the results by
    - Fields: The fields to include in the results
    - Name: The name of the host to search for
    - State: The state of the host to search for
    - Threat GTE: The minimum threat level to search for
    - Certainty GTE: The minimum certainty level to search for
    - Last Timestamp GTE: The minimum last timestamp to search for
    - Last Timestamp LTE: The maximum last timestamp to search for
    - Tags: The tags to search for
    - Note Modified Timestamp GTE: The minimum note modified timestamp to search for
    - Is Targeting Key Asset: Whether or not to search for hosts that are targeting key assets
    - Privilege Level: The minimum privilege level to search for
    - Privilege Category: The privilege category to search for
    - Active Traffic: Whether or not to search for hosts that have active traffic
    - Last Source: The last source of the host to search for
    - Limit: The maximum number of results to return

    Returns
    -------
    - A JSON object containing the results of the search
    - A data table containing the results of the search
    - An output message indicating the success or failure of the search
    - A result value indicating the success or failure of the search
    - An execution status indicating the success or failure of the search

    """
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_HOSTS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        input_type=str,
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Action Parameters
    order_by = extract_action_param(
        siemplify,
        param_name="Order By",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    fields = extract_action_param(
        siemplify,
        param_name="Fields",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    name = extract_action_param(
        siemplify,
        param_name="Name",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    state = extract_action_param(
        siemplify,
        param_name="State",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    threat_gte = extract_action_param(
        siemplify,
        param_name="Threat GTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    certainty_gte = extract_action_param(
        siemplify,
        param_name="Certainty GTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    last_detection_timestamp_gte = extract_action_param(
        siemplify,
        param_name="Last Detection Timestamp GTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    last_detection_timestamp_lte = extract_action_param(
        siemplify,
        param_name="Last Detection Timestamp LTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    tags = extract_action_param(
        siemplify,
        param_name="Tags",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    is_targeting_key_asset = extract_action_param(
        siemplify,
        param_name="Is Targeting Key Asset",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    note_modified_timestamp_gte = extract_action_param(
        siemplify,
        param_name="Note Modified Timestamp GTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    privilege_level_gte = extract_action_param(
        siemplify,
        param_name="Privilege Level GTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    privilege_category = extract_action_param(
        siemplify,
        param_name="Privilege Category",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    active_traffic = extract_action_param(
        siemplify,
        param_name="Active Traffic",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    last_source = extract_action_param(
        siemplify,
        param_name="Last Source",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    order = extract_action_param(
        siemplify,
        param_name="Order",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    field = ",".join(json.loads(fields))
    if order == "Descending" and order_by:
        order_by = "-" + order_by

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE

    try:
        limit = validate_limit_param(limit)
        threat_gte = validator(threat_gte, zero_allowed=True, name="Threat GTE")
        certainty_gte = validator(
            certainty_gte,
            zero_allowed=True,
            name="Certainty GTE",
        )
        privilege_level_gte = validator(privilege_level_gte, name="Privilege Level")
        limit = validator(limit, zero_allowed=True, name="Limit")
        privilege_category = privilege_category.lower() if privilege_category else None
        is_targeting_key_asset = (
            is_targeting_key_asset.lower() if is_targeting_key_asset else None
        )
        state = state.lower() if state else None
        active_traffic = active_traffic.lower() if active_traffic else None

        vectra_manager = VectraQUXManager(
            api_root,
            api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )
        hosts = vectra_manager.search_hosts(
            limit=limit,
            ordering=order_by,
            fields=field,
            name=name,
            state=state,
            threat_gte=threat_gte,
            last_detection_timestamp_gte=last_detection_timestamp_gte,
            last_detection_timestamp_lte=last_detection_timestamp_lte,
            certainty_gte=certainty_gte,
            tags=tags,
            is_targeting_key_asset=is_targeting_key_asset,
            note_modified_timestamp_gte=note_modified_timestamp_gte,
            privilege_level_gte=privilege_level_gte,
            privilege_category=privilege_category,
            active_traffic=active_traffic,
            last_source=last_source,
        )

        if not hosts:
            output_message = "No hosts were found with the provided parameters."
            siemplify.result.add_result_json({})
        else:
            output_message = (
                f"Successfully retrieved the details for {len(hosts)} hosts"
            )

            mendatory_fields = [
                "id",
                "last_source",
                "name",
                "severity",
                "state",
                "sensor",
                "threat",
                "certainty",
                "last_detection_timestamp",
                "ip",
            ]

            host_table = []
            for host in hosts:
                host = remove_api_version_from_url(host)
                host_table.append(extract_fields(host, mendatory_fields))
            siemplify.result.add_result_json(json.dumps(hosts, indent=4))
            siemplify.result.add_data_table(
                title="List Of Hosts",
                data_table=construct_csv(host_table),
            )

    except InvalidIntegerException as e:
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE
        output_message = f"{e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(SEARCH_HOSTS_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
