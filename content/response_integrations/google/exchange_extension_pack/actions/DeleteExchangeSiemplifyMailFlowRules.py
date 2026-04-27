from __future__ import annotations
import json
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.constants import (
    PROVIDER_NAME,
    DELETE_EXCHANGE_SIEMPLIFY_MAIL_FLOW_RULES_SCRIPT_NAME,
    ALL_AVAILABLE_RULES_STRING,
    SENDER_RULES,
    DOMAIN_RULES,
    PARAMETERS_DEFAULT_DELIMITER,
    ASYNC_ACTION_MAX_RETRIES,
)
from ..core.ExchangeExtensionPackExceptions import (
    ExchangeExtensionPackIncompleteInfoException,
    ExchangeExtensionPackPowershellException,
    ExchangeExtensionPackGssntlmsspException,
    ExchangeExtensionPackNotFound,
)
from ..core.ExchangeExtensionPackManager import ExchangeExtensionPackManager
from ..core.UtilsManager import prevent_async_action_fail_in_case_of_network_error


def delete_rule(manager, rule_names, successful_rule_names, not_found_rule_names):
    """
    Delete Rule
    :param manager: ExchangeExtensionPackManager manager object
    :param rule_names: {list} List of provided rule names
    :param successful_rule_names: {list} List of successfully processed rule names
    :param not_found_rule_names: {list} List of not found rule names
    :return: {tuple} output_message, result_value, status
    """
    not_processed_rule_names = list(
        set(rule_names) - set(successful_rule_names) - set(not_found_rule_names)
    )
    rule = not_processed_rule_names[0]

    try:
        manager.delete_rule(rule)
        successful_rule_names.append(rule)
    except ExchangeExtensionPackNotFound:
        not_found_rule_names.append(rule)

    if len(not_found_rule_names) == len(rule_names):
        raise ExchangeExtensionPackNotFound
    elif len(successful_rule_names) + len(not_found_rule_names) == len(rule_names):
        result_value = True
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"Successfully deleted the following rules: "
            f"{PARAMETERS_DEFAULT_DELIMITER.join(successful_rule_names)}"
        )

        if not_found_rule_names:
            output_message += (
                f"\nCould not delete the following rules: "
                f"{PARAMETERS_DEFAULT_DELIMITER.join(not_found_rule_names)}, "
                f"since they were not found in Exchange. Please make sure you have chosen the "
                f"appropriate rule names and try again"
            )
    else:
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps(
            {
                "successful_rule_names": successful_rule_names,
                "not_found_rule_names": not_found_rule_names,
            }
        )

        output_message = "Continuing processing the rules"

        if successful_rule_names:
            output_message += (
                f"\nSuccessfully deleted the following rules: "
                f"{PARAMETERS_DEFAULT_DELIMITER.join(successful_rule_names)}."
            )
        if not_found_rule_names:
            output_message += (
                f"\nCould not delete the following rules: "
                f"{PARAMETERS_DEFAULT_DELIMITER.join(not_found_rule_names)}, "
                f"since they were not found in Exchange. Please make sure you have chosen the "
                f"appropriate rule names and try again"
            )

    return output_message, result_value, status


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DELETE_EXCHANGE_SIEMPLIFY_MAIL_FLOW_RULES_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    server_address = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Exchange On-Prem " "Server Address",
        is_mandatory=False,
        print_value=True,
    )
    connection_uri = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Exchange Office365" " Online Powershell" " Uri",
        is_mandatory=False,
        print_value=True,
    )
    domain = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Domain", print_value=True
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="User name",
        is_mandatory=False,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Password",
        is_mandatory=False,
    )
    is_on_prem = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Is Exchange On-Prem?",
        input_type=bool,
        print_value=True,
    )
    is_office365 = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Is Office365 (Exchange Online)?",
        input_type=bool,
        print_value=True,
    )

    # Action parameters
    rule_name = extract_action_param(
        siemplify, param_name="Rule Name To Delete", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = False
    status = EXECUTION_STATE_FAILED
    manager = None

    rules = (
        SENDER_RULES + DOMAIN_RULES
        if rule_name == ALL_AVAILABLE_RULES_STRING
        else [rule_name]
    )

    try:
        if not is_on_prem and not is_office365:
            raise ExchangeExtensionPackIncompleteInfoException(
                "Please specify type of mail server to connect to - "
                "Exchange on-prem or Office 365"
            )

        if is_on_prem and is_office365:
            raise ExchangeExtensionPackIncompleteInfoException(
                "Only one mail server type is supported at a time. "
                "Please specify type of mail server to connect to - "
                "Exchange on-prem or Office 365"
            )

        # Create manager instance
        manager = ExchangeExtensionPackManager(
            server_address=server_address,
            connection_uri=connection_uri,
            domain=domain,
            username=username,
            password=password,
            is_on_prem=is_on_prem,
            is_office365=is_office365,
            siemplify_logger=siemplify.LOGGER,
        )
        additional_data = json.loads(
            extract_action_param(
                siemplify=siemplify, param_name="additional_data", default_value="{}"
            )
        )

        output_message, result_value, status = delete_rule(
            manager,
            rules,
            additional_data.get("successful_rule_names", []),
            additional_data.get("not_found_rule_names", []),
        )

    except ExchangeExtensionPackNotFound:
        result_value = False
        output_message = (
            "Could not delete any of the provided rule names, since they were not found in Exchange. "
            "Please make sure you have chosen the appropriate rule names and try again"
        )
        status = EXECUTION_STATE_COMPLETED
    except ExchangeExtensionPackIncompleteInfoException as e:
        output_message = str(e)
    except ExchangeExtensionPackPowershellException as e:
        output_message = (
            f"Failed to execute action because powershell is not installed on Siemplify server! Please"
            f" see the configuration instructions on how to install powershell. Error is {e}"
        )
    except ExchangeExtensionPackGssntlmsspException as e:
        output_message = (
            f"Failed to execute action because gssntlmssp package is not installed on Siemplify server!"
            f" Please see the configuration instructions on how to install powershell. Error is {e}"
        )
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {DELETE_EXCHANGE_SIEMPLIFY_MAIL_FLOW_RULES_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        output_message = f'Error performing "{DELETE_EXCHANGE_SIEMPLIFY_MAIL_FLOW_RULES_SCRIPT_NAME}" action: {e}'

        additional_data_json = extract_action_param(
            siemplify=siemplify, param_name="additional_data", default_value="{}"
        )
        output_message, result_value, status = (
            prevent_async_action_fail_in_case_of_network_error(
                e,
                additional_data_json,
                ASYNC_ACTION_MAX_RETRIES,
                output_message,
                result_value,
                status,
            )
        )
    finally:
        if manager:
            manager.disconnect()

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
