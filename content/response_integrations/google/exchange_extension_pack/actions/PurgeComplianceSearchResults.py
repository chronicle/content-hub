from __future__ import annotations
import json
import sys
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.constants import (
    PROVIDER_NAME,
    PURGE_COMPLIANCE_SEARCH_RESULTS_SCRIPT_NAME,
    COMPLETED_STATUS,
    DELETE_STATE,
    ASYNC_ACTION_MAX_RETRIES,
)
from ..core.ExchangeExtensionPackExceptions import (
    ExchangeExtensionPackPowershellException,
    ExchangeExtensionPackGssntlmsspException,
    ExchangeExtensionPackIncompleteInfoException,
    ExchangeExtensionPackNotFound,
    ExchangeExtensionPackNoResults,
)
from ..core.ExchangeExtensionPackManager import ExchangeExtensionPackManager
from ..core.UtilsManager import prevent_async_action_fail_in_case_of_network_error


def start_operation(manager, compliance_search_name, state):
    """
    Create compliance search purge action
    :param manager: ExchangeExtensionPackManager manager object
    :param compliance_search_name: {str} Name of compliance search
    :param state: {str} Specifies state for purge, can be SoftDelete/HardDelete
    :return: {tuple} output_message, result_value, status
    """
    manager.create_compliance_search_purge(compliance_search_name, state)

    status = EXECUTION_STATE_INPROGRESS
    result_value = json.dumps({"create_compliance_search_purge": COMPLETED_STATUS})
    output_messages = (
        "Action was executed successfully and task to purge emails found with the compliance search"
        " is created"
    )
    return output_messages, result_value, status


def query_operation_status(
    siemplify, manager, compliance_search_name, remove_compliance_search
):
    """
    Periodically tries to check compliance search purge action status
    :param siemplify: SiemplifyAction object
    :param manager: ExchangeExtensionPackManager manager object
    :param compliance_search_name: {str} Name of compliance search
    :param remove_compliance_search: {bool} Specifies if action should remove the compliance search
    :return: {tuple} output_message, result_value, status
    """
    compliance_search_purge_status, results = (
        manager.get_compliance_search_purge_results(compliance_search_name)
    )
    results_count = results.get("Item count") if results else None
    status = EXECUTION_STATE_INPROGRESS
    result_value = json.dumps(
        {
            "create_compliance_search_purge": COMPLETED_STATUS,
            "compliance_search_purge_status": compliance_search_purge_status,
            "results_count": results_count,
        }
    )

    if compliance_search_purge_status != COMPLETED_STATUS:
        output_messages = (
            "Action was executed successfully and task to purge emails found with the compliance search"
            " is created"
        )
    elif remove_compliance_search:
        output_messages = prepare_output_message(
            compliance_search_name, results_count, remove_compliance_search
        )
    else:
        result_value = True
        status = EXECUTION_STATE_COMPLETED
        output_messages = prepare_output_message(compliance_search_name, results_count)

    if results and results_count != "0":
        siemplify.result.add_result_json(results)

    return output_messages, result_value, status


def remove_compliance_search_operation(manager, compliance_search_name, results_count):
    """
    Remove compliance search
    :param manager: ExchangeExtensionPackManager manager object
    :param compliance_search_name: {str} Name of compliance search
    :param results_count: {str} The results count
    :return: {tuple} output_message, result_value, status
    """
    manager.remove_compliance_search(compliance_search_name)
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_messages = prepare_output_message(
        compliance_search_name, results_count, True, COMPLETED_STATUS
    )
    return output_messages, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = PURGE_COMPLIANCE_SEARCH_RESULTS_SCRIPT_NAME
    mode = "Main" if is_first_run else "QueryState"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

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
        param_name="Exchange Office365" " Compliance Uri",
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
    compliance_search_name = extract_action_param(
        siemplify,
        param_name="Compliance Search Name",
        is_mandatory=True,
        print_value=True,
    )
    perform_hard_delete = extract_action_param(
        siemplify,
        param_name="Perform a HardDelete for deleted emails?",
        input_type=bool,
        print_value=True,
    )
    remove_compliance_search = extract_action_param(
        siemplify,
        param_name="Remove Compliance Search Once Action " "Completes?",
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")
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
                "Please specify Exchange Office365 Compliance Uri"
            )

        state = (
            DELETE_STATE.get("hard_delete")
            if perform_hard_delete
            else DELETE_STATE.get("soft_delete")
        )

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

        additional_data = (
            json.loads(siemplify.parameters.get("additional_data"))
            if siemplify.parameters.get("additional_data")
            else {}
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                manager, compliance_search_name, state
            )
        else:
            if (
                additional_data.get("create_compliance_search_purge")
                != COMPLETED_STATUS
            ):
                output_message, result_value, status = start_operation(
                    manager, compliance_search_name, state
                )
            elif (
                additional_data.get("compliance_search_purge_status")
                != COMPLETED_STATUS
            ):
                output_message, result_value, status = query_operation_status(
                    siemplify, manager, compliance_search_name, remove_compliance_search
                )
            else:
                output_message, result_value, status = (
                    remove_compliance_search_operation(
                        manager,
                        compliance_search_name,
                        additional_data.get("results_count"),
                    )
                )

    except ExchangeExtensionPackNotFound:
        output_message = (
            f"Action was not able to find compliance search {compliance_search_name}"
        )
        result_value = False
        status = EXECUTION_STATE_COMPLETED
    except ExchangeExtensionPackNoResults:
        output_message = (
            f"The Compliance Search {compliance_search_name} didn't return any results. Please update"
            f" the search results or edit the Compliance search query and run the search again"
        )
        result_value = False
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
            f"General error performing action {PURGE_COMPLIANCE_SEARCH_RESULTS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        output_message = f"Failed to execute action! Error is {e}"

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

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


def prepare_output_message(
    compliance_search_name,
    results_count,
    remove_compliance_search=False,
    remove_compliance_search_status=None,
):
    """
    Prepare output message
    :param compliance_search_name: {str} Name of compliance search
    :param results_count: {str} The count of search results
    :param remove_compliance_search: {bool} Specifies if action should remove the compliance search
    :param remove_compliance_search_status: {str} Specifies if remove compliance search action completed
    :return: {str} Output message
    """
    if results_count != "0":
        output_message = f"Results for the Compliance Search {compliance_search_name} were successfully purged."
    else:
        output_message = (
            f"The Compliance Search {compliance_search_name} didn't return any results. Please update "
            f"the search results or edit the Compliance search query and run the search again."
        )

    if remove_compliance_search and remove_compliance_search_status == COMPLETED_STATUS:
        output_message += (
            f"\nCompliance Search {compliance_search_name} was successfully removed"
        )
    elif remove_compliance_search:
        output_message += "\nProcessing compliance search removing"

    return output_message


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
