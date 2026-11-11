from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from hashi_corp_vault.core.HashiCorpVaultManager import HashiCorpVaultManager
from hashi_corp_vault.core.HashiCorpVaultExceptions import NotFoundException
from hashi_corp_vault.core.constants import (
    INTEGRATION_NAME,
    LIST_KEY_VALUE_SCRIPT_NAME,
    RECORDS_DEFAULT_LIMIT,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_KEY_VALUE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Token",
        is_mandatory=False,
        remove_whitespaces=False,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=False,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    key_value_secret_engine_path = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Key-Value Secret Engine Path",
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters
    key_value_secret_engine_path_for_action = extract_action_param(
        siemplify,
        param_name="Key-Value Secret Engine Path",
        is_mandatory=False,
        print_value=True,
    )
    secret_path = extract_action_param(
        siemplify, param_name="Secret Path", is_mandatory=False, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Records To Return",
        input_type=int,
        default_value=RECORDS_DEFAULT_LIMIT,
        is_mandatory=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""

    try:
        if limit is not None and limit < 1:
            raise Exception(
                f'Invalid value was provided for "Max Records to Return": {limit}. '
                f"Positive number should be provided"
            )

        manager = HashiCorpVaultManager(
            api_root=api_root,
            api_token=api_token,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            key_value_secret_engine_path=key_value_secret_engine_path,
            siemplify=siemplify,
        )
        kv_store = (
            key_value_secret_engine_path_for_action or key_value_secret_engine_path
        )
        kv_response = manager.list_key_value_secret_keys(
            key_value=kv_store, secret_path=secret_path
        )

        if kv_response and kv_response.keys:
            kv_response.raw_data["data"]["keys"] = kv_response.keys[:limit]
            siemplify.result.add_result_json(kv_response.to_json())
            output_message += (
                f"Successfully found the following secret keys for the "
                f"provided criteria in the key-value store {kv_store}."
            )
        else:
            raise NotFoundException

    except NotFoundException:
        result = False
        output_message = f"No secret keys were found for the provided criteria in Key-Value Secret Engine Path."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_KEY_VALUE_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{LIST_KEY_VALUE_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
