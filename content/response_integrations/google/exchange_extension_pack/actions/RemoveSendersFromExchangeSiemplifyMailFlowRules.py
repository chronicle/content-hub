from __future__ import annotations
import json
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, extract_domain
from ..core.constants import (
    PROVIDER_NAME,
    REMOVE_SENDERS_FROM_EXCHANGE_SIEMPLIFY_MAIL_FLOW_RULES_SCRIPT_NAME,
    PARAMETERS_DEFAULT_DELIMITER,
    CONDITIONS,
    CORRESPONDING_RULES,
    DOMAIN_RULES,
    ASYNC_ACTION_MAX_RETRIES,
    COMPLETED_STATUS,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.ExchangeExtensionPackExceptions import (
    ExchangeExtensionPackIncompleteInfoException,
    ExchangeExtensionPackIncompleteParametersException,
    ExchangeExtensionPackPowershellException,
    ExchangeExtensionPackGssntlmsspException,
    ExchangeExtensionPackNotFound,
)
from ..core.ExchangeExtensionPackManager import ExchangeExtensionPackManager
from ..core.UtilsManager import validate_email_address
from ..core.UtilsManager import prevent_async_action_fail_in_case_of_network_error


# Constants
SUPPORTED_ENTITY_TYPES = [EntityTypes.USER]


def get_rules(manager, rules):
    """
    Get existing rules by rule names
    :param manager: ExchangeExtensionPackManager manager object
    :param rules: {list} List of rule names
    :return: {tuple} output_message, result_value, status
    """
    existing_rules = manager.get_rules_by_names(rules)
    existing_rules_names = [existing_rule.name for existing_rule in existing_rules]

    if not existing_rules:
        raise ExchangeExtensionPackNotFound

    status = EXECUTION_STATE_INPROGRESS
    result_value = {
        "get_rules": COMPLETED_STATUS,
        "existing_rules": existing_rules_names,
    }

    for existing_rule in existing_rules:
        result_value[existing_rule.name] = existing_rule.items

    output_message = "Found {} rules. Continuing...".format(
        PARAMETERS_DEFAULT_DELIMITER.join(
            [f'"{rule_name}"' for rule_name in existing_rules_names]
        )
    )

    return output_message, json.dumps(result_value), status


def remove_items_from_rule(
    siemplify,
    manager,
    rules,
    valid_items,
    invalid_items,
    remove_domains,
    additional_data,
):
    """
    Remove items from rule
    :param manager: ExchangeExtensionPackManager manager object
    :param rules: {list} List of rule names
    :param valid_items: {list} List of valid items
    :param invalid_items: {list} List of invalid items
    :param remove_domains: {bool} Specifies whether domains of the provided email addresses removed from corresponding rules
    :param additional_data: {dict} Additional data from previous iteration
    :return: {tuple} output_message, result_value, status
    """
    processed_rules = additional_data.get("processed_rules", [])
    existing_rules = additional_data.get("existing_rules", [])
    not_processed_rules = list(set(rules) - set(processed_rules))
    rule_name = not_processed_rules[0]
    existing_items = []

    if rule_name not in existing_rules:
        siemplify.LOGGER.info(f'"{rule_name}" rule was not found.')
    else:
        existing_items = additional_data.get(rule_name, [])

        if rule_name in DOMAIN_RULES:
            domains = list(
                set([extract_domain(email_address) for email_address in valid_items])
            )

            manager.remove_items_from_rule(
                rule_name=rule_name,
                rule_items=existing_items,
                condition=CONDITIONS.get("domain"),
                items=domains,
            )
        else:
            manager.remove_items_from_rule(
                rule_name=rule_name,
                rule_items=existing_items,
                condition=CONDITIONS.get("sender"),
                items=valid_items,
            )

    processed_rules.append(rule_name)

    if len(rules) == len(processed_rules):
        siemplify.result.add_result_json(
            {
                "success": list(set(existing_items).intersection(valid_items)),
                "didn't_exist": list(set(valid_items) - set(existing_items)),
                "invalid": invalid_items,
            }
        )

        result_value = True
        status = EXECUTION_STATE_COMPLETED
        output_message = prepare_output_messages(
            rules, valid_items, invalid_items, remove_domains
        )
    else:
        additional_data.update({"processed_rules": processed_rules})
        result_value = json.dumps(additional_data)
        status = EXECUTION_STATE_INPROGRESS
        output_message = f"Rules updated: {PARAMETERS_DEFAULT_DELIMITER.join(processed_rules)}. Continuing..."

    return output_message, result_value, status


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        REMOVE_SENDERS_FROM_EXCHANGE_SIEMPLIFY_MAIL_FLOW_RULES_SCRIPT_NAME
    )

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
    email_addresses_string = extract_action_param(
        siemplify, param_name="Email Addresses", print_value=True
    )
    rule_name = extract_action_param(
        siemplify,
        param_name="Rule to remove Senders from",
        is_mandatory=True,
        print_value=True,
    )
    remove_domains = extract_action_param(
        siemplify,
        param_name="Should remove senders' domains from the corresponding"
        " Domains List rule as well?",
        input_type=bool,
        print_value=True,
    )

    email_addresses = (
        [
            email_address.strip()
            for email_address in email_addresses_string.split(
                PARAMETERS_DEFAULT_DELIMITER
            )
            if email_address.strip()
        ]
        if email_addresses_string
        else []
    )

    rules = (
        [rule_name, CORRESPONDING_RULES[rule_name]] if remove_domains else [rule_name]
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = False
    status = EXECUTION_STATE_FAILED
    manager = None

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

        if not connection_uri and is_office365:
            raise ExchangeExtensionPackIncompleteInfoException(
                "Please specify Exchange Office365 Online Powershell Uri"
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

        if not email_addresses:
            siemplify.LOGGER.info(
                "No email addresses provided in action parameters. Action will work with User "
                "entities"
            )
            email_addresses = [
                entity.identifier
                for entity in siemplify.target_entities
                if entity.entity_type in SUPPORTED_ENTITY_TYPES
                and validate_email_address(entity.identifier)
            ]

        valid_email_addresses = [
            email_address
            for email_address in email_addresses
            if validate_email_address(email_address)
        ]
        invalid_email_addresses = list(
            set(email_addresses) - set(valid_email_addresses)
        )

        if not valid_email_addresses:
            raise ExchangeExtensionPackIncompleteParametersException

        additional_data = json.loads(
            extract_action_param(
                siemplify=siemplify, param_name="additional_data", default_value="{}"
            )
        )

        if additional_data.get("get_rules") != COMPLETED_STATUS:
            output_message, result_value, status = get_rules(manager, rules)
        else:
            output_message, result_value, status = remove_items_from_rule(
                siemplify,
                manager,
                rules,
                valid_email_addresses,
                invalid_email_addresses,
                remove_domains,
                additional_data,
            )

    except ExchangeExtensionPackNotFound:
        result_value = False
        output_message = "No rules were found matching the provided name"
        status = EXECUTION_STATE_COMPLETED
    except ExchangeExtensionPackIncompleteInfoException as e:
        output_message = str(e)
    except ExchangeExtensionPackIncompleteParametersException:
        output_message = (
            'No valid email addresses provided in "Email Addresses" parameter, or there are no valid '
            "email addresses found in the user entities. Please check action inputs and try again"
        )
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
            f"General error performing action "
            f"{REMOVE_SENDERS_FROM_EXCHANGE_SIEMPLIFY_MAIL_FLOW_RULES_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        output_message = (
            f'Error performing "{REMOVE_SENDERS_FROM_EXCHANGE_SIEMPLIFY_MAIL_FLOW_RULES_SCRIPT_NAME}" '
            f"action: {e}"
        )

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


def prepare_output_messages(
    rules, valid_email_addresses, invalid_email_addresses, remove_domains=None
):
    """
    Prepare output messages
    :param rules: {list} The list of rule names
    :param valid_email_addresses: {list} The list of valid email addresses
    :param invalid_email_addresses: {list} The list of invalid email addresses
    :param remove_domains: {bool} Specifies whether domains of the provided email addresses removed from corresponding rules
    :return: {str} The output messages
    """
    output_message = (
        f"Removed the following inputs from the corresponding rules: "
        f"\nEmail Addresses: {PARAMETERS_DEFAULT_DELIMITER.join(valid_email_addresses)}"
    )

    if remove_domains:
        domains = list(
            set(
                [
                    extract_domain(email_address)
                    for email_address in valid_email_addresses
                ]
            )
        )
        output_message += f"\nDomains: {PARAMETERS_DEFAULT_DELIMITER.join(domains)}"

    output_message += f"\nRules updated: {PARAMETERS_DEFAULT_DELIMITER.join(rules)}"

    if invalid_email_addresses:
        output_message += (
            f"\nCould not remove the following inputs from the rule: "
            f"{PARAMETERS_DEFAULT_DELIMITER.join(invalid_email_addresses)}"
        )

    return output_message


if __name__ == "__main__":
    main()
