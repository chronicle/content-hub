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
    SEARCH_ACCOUNTS_SCRIPT_NAME,
)
from ..core.UtilsManager import extract_fields, validate_limit_param, validator
from ..core.VectraQUXExceptions import InvalidIntegerException
from ..core.VectraQUXManager import VectraQUXManager


def remove_api_version_from_url(account):
    if account.get("url"):
        account["url"] = (
            account.get("url", "")
            .replace(API_VERSION_2_5, "")
            .replace(API_VERSION_2_1, "")
            .replace(API_VERSION_2_2, "")
        )
    if account.get("detection_set"):
        account["detection_set"] = [
            url.replace(API_VERSION_2_5, "")
            .replace(API_VERSION_2_1, "")
            .replace(API_VERSION_2_2, "")
            for url in account.get("detection_set", "")
        ]
    return account


@output_handler
def main():
    """Main function for the Accounts Search action.

    This function will query the Vectra API for accounts based on the parameters
    provided by the user.

    Parameters are:
        - API Root: The root URL of the Vectra API
        - API Token: The API token to use for authentication
        - Verify SSL: Whether or not to verify the SSL certificate of the API
        - Ordering: The field to order the results by
        - Fields: The fields to include in the results
        - Name: The name of the account to search for
        - State: The state of the account to search for
        - Threat GTE: The minimum threat level to search for
        - Certainty GTE: The minimum certainty level to search for
        - Last Timestamp GTE: The minimum last timestamp to search for
        - Last Timestamp LTE: The maximum last timestamp to search for
        - Tags: The tags to search for
        - Note Modified Timestamp GTE: The minimum note modified timestamp to search for
        - Privilege Level: The minimum privilege level to search for
        - Privilege Category: The privilege category to search for
        - Limit: The maximum number of results to return

    Returns:
        - A JSON object containing the results of the search
        - A data table containing the results of the search
        - An output message indicating the success or failure of the search
        - A result value indicating the success or failure of the search
        - An execution status indicating the success or failure of the search

    """
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_ACCOUNTS_SCRIPT_NAME
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
    note_modified_timestamp_gte = extract_action_param(
        siemplify,
        param_name="Note Modified Timestamp GTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    privilege_level = extract_action_param(
        siemplify,
        param_name="Privilege Level",
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
        privilege_level = validator(privilege_level, name="Privilege Level")
        limit = validator(limit, zero_allowed=True, name="Limit")
        state = state.lower() if state else None
        privilege_category = privilege_category.lower() if privilege_category else None

        vectra_manager = VectraQUXManager(
            api_root,
            api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )
        accounts = vectra_manager.search_accounts(
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
            note_modified_timestamp_gte=note_modified_timestamp_gte,
            privilege_level=privilege_level,
            privilege_category=privilege_category,
        )

        if not accounts:
            output_message = "No accounts were found with the provided parameters."
            siemplify.result.add_result_json({})
        else:
            output_message = (
                f"Successfully retrieved the details for {len(accounts)} accounts."
            )

            mendatory_fields = [
                "id",
                "name",
                "threat",
                "certainty",
                "state",
                "last_detection_timestamp",
                "severity",
            ]
            account_table = []
            for account in accounts:
                account = remove_api_version_from_url(account)
                account_table.append(extract_fields(account, mendatory_fields))
            siemplify.result.add_result_json(json.dumps(accounts, indent=4))
            siemplify.result.add_data_table(
                title="List Of Accounts",
                data_table=construct_csv(account_table),
            )

    except InvalidIntegerException as e:
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE
        output_message = f"{e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            SEARCH_ACCOUNTS_SCRIPT_NAME,
            e,
        )
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
