from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    string_to_multi_value,
)
from hashi_corp_vault.core.HashiCorpVaultManager import HashiCorpVaultManager
from hashi_corp_vault.core.HashiCorpVaultExceptions import NotFoundException
from hashi_corp_vault.core.constants import INTEGRATION_NAME, READ_KEY_VALUE_SCRIPT_NAME, EXPRESSION_DELIMITER


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = READ_KEY_VALUE_SCRIPT_NAME
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
        siemplify, param_name="Secret Path", is_mandatory=True, print_value=True
    )
    secret_version = extract_action_param(
        siemplify,
        param_name="Secret Version",
        input_type=int,
        is_mandatory=False,
        print_value=True,
    )
    json_expression_builder = extract_action_param(
        siemplify,
        param_name="JSON Expression Builder",
        is_mandatory=False,
        print_value=True,
    )
    json_expression_builder = string_to_multi_value(
        json_expression_builder, EXPRESSION_DELIMITER
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED

    try:
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
        try:
            kv_response = manager.read_key_value_secret(
                key_value=kv_store, secret_path=secret_path, version=secret_version
            )

            if json_expression_builder:
                for key in json_expression_builder:
                    try:
                        kv_response = kv_response.get(key)
                        if not kv_response:
                            raise Exception
                    except Exception:
                        raise Exception(
                            f"Incorrect JSON value is provided for the Expression Builder."
                        )

            siemplify.result.add_result_json({"content": kv_response})
            output_message = f"Successfully fetched secret {secret_path}."
        except NotFoundException:
            result = False
            output_message = f"The following secret {secret_path} was not found in the HashiCorp Vault."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {READ_KEY_VALUE_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{READ_KEY_VALUE_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
