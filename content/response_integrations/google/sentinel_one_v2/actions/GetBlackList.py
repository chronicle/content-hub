from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv
from sentinel_one_v2.core.constants import (
    INTEGRATION_NAME,
    GET_BLACK_LIST_SCRIPT_NAME,
    MAX_BLACK_LIST_LIMIT,
    PRODUCT_NAME,
    BLACKLIST_HASHES_TABLE_NAME,
)
from sentinel_one_v2.core.exceptions import SentinelOneV2ValidationError, SentinelOneV2PermissionError
from sentinel_one_v2.core.utils import string_to_multi_value
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_BLACK_LIST_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    hashes = string_to_multi_value(
        extract_action_param(siemplify, param_name="Hash", print_value=True)
    )
    site_ids = string_to_multi_value(
        extract_action_param(siemplify, param_name="Site IDs", print_value=True)
    )
    group_ids = string_to_multi_value(
        extract_action_param(siemplify, param_name="Group IDs", print_value=True)
    )
    account_ids = string_to_multi_value(
        extract_action_param(siemplify, param_name="Account IDs", print_value=True)
    )
    limit = extract_action_param(
        siemplify, param_name="Limit", input_type=int, print_value=True
    )
    limit = limit and max(0, min(limit, MAX_BLACK_LIST_LIMIT)) or None
    query = extract_action_param(siemplify, param_name="Query", print_value=True)
    use_global_blacklist = extract_action_param(
        siemplify, param_name="Use Global Blacklist", input_type=bool, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = f"Successfully retrieved blacklisted hashes based on the provided filter criteria in {PRODUCT_NAME}."
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    results = []

    try:
        if (
            not site_ids
            and not group_ids
            and not account_ids
            and not use_global_blacklist
        ):
            raise SentinelOneV2ValidationError(
                'at least one value should be provided for "Site IDs" or "Group IDs" or "Account IDs" parameters '
                'or "Use Global Blacklist" should be enabled.'
            )

        manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        if not hashes:
            results = manager.get_blacklist_items(
                hash_value=hashes,
                site_ids=site_ids,
                group_ids=group_ids,
                account_ids=account_ids,
                limit=limit,
                query=query,
                tenant=use_global_blacklist,
            )
        else:
            for hash_value in hashes:
                try:
                    results.extend(
                        manager.get_blacklist_items(
                            hash_value=hash_value,
                            site_ids=site_ids,
                            group_ids=group_ids,
                            account_ids=account_ids,
                            limit=limit,
                            query=query,
                            tenant=use_global_blacklist,
                        )
                    )
                except Exception as err:
                    if isinstance(err, SentinelOneV2PermissionError):
                        raise
                    siemplify.LOGGER.error(f"An error occurred on hash: {hash_value}")
                    siemplify.LOGGER.exception(err)
        if results:
            siemplify.result.add_result_json([threat.to_json() for threat in results])
            siemplify.result.add_data_table(
                BLACKLIST_HASHES_TABLE_NAME,
                construct_csv([threat.to_csv() for threat in results]),
            )
        else:
            output_message = f"No blacklisted hashes were found for the provided criteria in {PRODUCT_NAME}."
            result_value = False

    except Exception as e:
        output_message = (
            f"Error executing action {GET_BLACK_LIST_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
