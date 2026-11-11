from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.validation import ParameterValidator
from hashi_corp_vault.core import constants
from hashi_corp_vault.core.HashiCorpVaultManager import HashiCorpVaultManager
from hashi_corp_vault.core.HashiCorpVaultExceptions import InvalidJsonBuilderExpression, NotFoundException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = constants.GENERATE_AWS_CREDENTIALS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Token",
        is_mandatory=False,
        remove_whitespaces=False,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=False,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    key_value_secret_engine_path = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Key-Value Secret Engine Path",
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters
    aws_secret_engine_path = extract_action_param(
        siemplify,
        param_name="AWS Secret Engine Path",
        is_mandatory=False,
        print_value=True,
    )
    aws_role_name = extract_action_param(
        siemplify, param_name="AWS Role Name", is_mandatory=True, print_value=True
    )
    aws_role_arn = extract_action_param(
        siemplify, param_name="AWS Role ARN", is_mandatory=False, print_value=True
    )
    aws_role_session_name = extract_action_param(
        siemplify,
        param_name="AWS Role Session Name",
        is_mandatory=False,
        print_value=True,
    )
    ttl_seconds = extract_action_param(
        siemplify,
        param_name="TTL (seconds)",
        is_mandatory=False,
        print_value=True,
        default_value=str(constants.DEFAULT_TTL_SECONDS),
    )
    json_expression_builder = extract_action_param(
        siemplify,
        param_name="JSON Expression Builder",
        is_mandatory=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    kv_store = aws_secret_engine_path or key_value_secret_engine_path

    try:
        param_validator = ParameterValidator(siemplify)

        ttl_seconds = param_validator.validate_potsitive(
            param_name="TTL (seconds)", value=ttl_seconds
        )

        json_expression_builder = string_to_multi_value(
            json_expression_builder, constants.EXPRESSION_DELIMITER
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

        kv_response = manager.generate_aws_creds(
            key_value=kv_store,
            role_name=aws_role_name,
            role_arn=aws_role_arn,
            session_name=aws_role_session_name,
            ttl_seconds=ttl_seconds,
        )

        if kv_response.data is None:
            raise NotFoundException

        json_response = kv_response.to_json()
        if json_expression_builder:
            for key in json_expression_builder:
                try:
                    json_response = json_response[key]
                except Exception as e:
                    raise InvalidJsonBuilderExpression(
                        f"Incorrect JSON value is provided for the "
                        f"Expression Builder: {e}"
                    )

        siemplify.result.add_result_json({"content": json_response})
        output_message += (
            f"Successfully generated credentials for the " f"{aws_role_name} role."
        )

    except NotFoundException:
        result = False
        output_message = (
            f"The following AWS role {aws_role_name} was not found under "
            f"specified AWS Secret Engine Path {aws_secret_engine_path} "
            f"in {constants.INTEGRATION_DISPLAY_NAME}."
        )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action "
            f"{constants.GENERATE_AWS_CREDENTIALS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action "
            f'"{constants.GENERATE_AWS_CREDENTIALS_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
