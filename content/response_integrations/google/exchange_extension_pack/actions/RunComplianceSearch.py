from __future__ import annotations
import sys
import json
from datetime import timedelta
import pytz
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, utc_now
from ..core.constants import (
    PROVIDER_NAME,
    RUN_COMPLIANCE_SEARCH_SCRIPT_NAME,
    COMPLETED_STATUS,
    DATETIME_FORMAT,
    ASYNC_ACTION_MAX_RETRIES,
)
from ..core.ExchangeExtensionPackExceptions import (
    ExchangeExtensionPackPowershellException,
    ExchangeExtensionPackGssntlmsspException,
    ExchangeExtensionPackIncompleteInfoException,
    ExchangeExtensionPackNoResults,
    ExchangeExtensionPackAlreadyExist,
    ExchangeExtensionPackInvalidQuery,
)
from ..core.ExchangeExtensionPackManager import ExchangeExtensionPackManager
from ..core.UtilsManager import prevent_async_action_fail_in_case_of_network_error


def start_operation(
    manager,
    compliance_search_name,
    subject_filter,
    sender_filter,
    recipient_filter,
    time_filter,
    operator,
    location,
    advanced_query,
):
    """
    Main part of the action that create compliance search
    :param manager: ExchangeExtensionPackManager manager object
    :param compliance_search_name: {str} Name of compliance search
    :param subject_filter: {str} Filter by subject
    :param sender_filter: {str} Filter by sender
    :param recipient_filter: {str} Filter by recipient
    :param time_filter: {str} Filter by time
    :param operator: {str} Operator to use in query
    :param location: {str} Location to search emails in
    :param advanced_query: {str} Query to use in compliance search
    :return: {tuple} output_message, result_value, status
    """
    manager.create_compliance_search(
        compliance_search_name,
        subject_filter,
        sender_filter,
        recipient_filter,
        time_filter,
        operator,
        location,
        advanced_query,
    )
    status = EXECUTION_STATE_INPROGRESS
    result_value = json.dumps({"create_compliance_search": COMPLETED_STATUS})
    output_messages = (
        "Action was executed successfully and compliance search is created"
    )
    return output_messages, result_value, status


def query_operation_status(siemplify, manager, compliance_search_name, fetch_results):
    """
    Part of the action that periodically tries to check compliance search status
    :param siemplify: SiemplifyAction object
    :param manager: ExchangeExtensionPackManager manager object
    :param compliance_search_name: {str} Name of compliance search
    :param fetch_results: {bool} Specifies whether the action should fetch the results or no
    :return: {tuple} output_message, result_value, status
    """
    compliance_search_data = manager.get_compliance_search_status(
        compliance_search_name
    )
    status = EXECUTION_STATE_INPROGRESS
    result_value = json.dumps(
        {
            "create_compliance_search": COMPLETED_STATUS,
            "compliance_search_status": compliance_search_data.status,
        }
    )

    if compliance_search_data.status != COMPLETED_STATUS:
        output_messages = (
            "Action was executed successfully and compliance search is created"
        )
    elif fetch_results:
        output_messages = (
            f"Compliance Search {compliance_search_name} successfully completed. Continuing...waiting "
            f"for results"
        )
    else:
        siemplify.result.add_result_json(compliance_search_data.to_json())
        result_value = True
        status = EXECUTION_STATE_COMPLETED
        output_messages = (
            f"Compliance Search {compliance_search_name} successfully completed"
        )

    return output_messages, result_value, status


def start_preview_operation(manager, compliance_search_name):
    """
    Create compliance search preview action
    :param manager: ExchangeExtensionPackManager manager object
    :param compliance_search_name: {str} Name of compliance search
    :return: {tuple} output_message, result_value, status
    """
    manager.create_compliance_search_preview(compliance_search_name)
    status = EXECUTION_STATE_INPROGRESS
    result_value = json.dumps(
        {
            "create_compliance_search": COMPLETED_STATUS,
            "compliance_search_status": COMPLETED_STATUS,
            "create_compliance_search_preview": COMPLETED_STATUS,
        }
    )
    output_messages = f"Continuing...waiting for the Compliance Search {compliance_search_name} results"
    return output_messages, result_value, status


def query_preview_operation_status(
    siemplify, manager, compliance_search_name, limit, create_table
):
    """
    Periodically tries to check compliance search preview action status
    :param siemplify: SiemplifyAction object
    :param manager: ExchangeExtensionPackManager manager object
    :param compliance_search_name: {str} Name of compliance search
    :param limit: {int} Specifies limit for results
    :param create_table: {bool} Specifies if action should create case wall output table
    :return: {tuple} output_message, result_value, status
    """
    compliance_search_preview_status, results = (
        manager.get_compliance_search_preview_results(compliance_search_name, limit)
    )
    status = EXECUTION_STATE_INPROGRESS
    result_value = json.dumps(
        {
            "create_compliance_search": COMPLETED_STATUS,
            "compliance_search_status": COMPLETED_STATUS,
            "create_compliance_search_preview": COMPLETED_STATUS,
        }
    )

    if compliance_search_preview_status != COMPLETED_STATUS:
        output_messages = f"Continuing...waiting for the Compliance Search {compliance_search_name} results"
    else:
        if results:
            siemplify.result.add_result_json([result.to_json() for result in results])

            if create_table:
                siemplify.result.add_entity_table(
                    "Compliance Search Action Results",
                    construct_csv([result.to_table() for result in results]),
                )

        result_value = True
        status = EXECUTION_STATE_COMPLETED
        output_messages = f"Results for the Compliance Search {compliance_search_name} were successfully fetched"

    return output_messages, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = RUN_COMPLIANCE_SEARCH_SCRIPT_NAME
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
    subject_filter = extract_action_param(
        siemplify, param_name="Subject Filter", print_value=True
    )
    sender_filter = extract_action_param(
        siemplify, param_name="Sender Filter", print_value=True
    )
    recipient_filter = extract_action_param(
        siemplify, param_name="Recipient Filter", print_value=True
    )
    time_frame = extract_action_param(
        siemplify, param_name="Time Frame (hours)", input_type=int, print_value=True
    )
    operator = extract_action_param(siemplify, param_name="Operator", print_value=True)
    location = extract_action_param(
        siemplify,
        param_name="Location to Search Emails In",
        is_mandatory=True,
        print_value=True,
    )
    fetch_results = extract_action_param(
        siemplify,
        param_name="Fetch Compliance Search Results?",
        input_type=bool,
        print_value=True,
    )
    limit = extract_action_param(
        siemplify, param_name="Max Emails To Return", input_type=int, print_value=True
    )
    create_table = extract_action_param(
        siemplify,
        param_name="Create Case Wall Output Table?",
        input_type=bool,
        print_value=True,
    )
    advanced_query = extract_action_param(
        siemplify, param_name="Advanced Query", print_value=True
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")
    result_value = False
    status = EXECUTION_STATE_FAILED
    time_filter = (
        (
            utc_now().replace(tzinfo=pytz.utc) - timedelta(hours=int(time_frame))
        ).strftime(DATETIME_FORMAT)
        if time_frame
        else None
    )
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
                manager,
                compliance_search_name,
                subject_filter,
                sender_filter,
                recipient_filter,
                time_filter,
                operator,
                location,
                advanced_query,
            )
        else:
            if additional_data.get("create_compliance_search") != COMPLETED_STATUS:
                output_message, result_value, status = start_operation(
                    manager,
                    compliance_search_name,
                    subject_filter,
                    sender_filter,
                    recipient_filter,
                    time_filter,
                    operator,
                    location,
                    advanced_query,
                )
            elif additional_data.get("compliance_search_status") != COMPLETED_STATUS:
                output_message, result_value, status = query_operation_status(
                    siemplify, manager, compliance_search_name, fetch_results
                )
            elif (
                additional_data.get("create_compliance_search_preview")
                != COMPLETED_STATUS
            ):
                output_message, result_value, status = start_preview_operation(
                    manager, compliance_search_name
                )
            else:
                output_message, result_value, status = query_preview_operation_status(
                    siemplify, manager, compliance_search_name, limit, create_table
                )

    except ExchangeExtensionPackNoResults:
        output_message = (
            f"The Compliance Search {compliance_search_name} didn't return any results. Please update"
            f" the search results or edit the Compliance search query and run the search again"
        )
        result_value = False
        status = EXECUTION_STATE_COMPLETED
    except ExchangeExtensionPackAlreadyExist:
        output_message = f"The Compliance Search {compliance_search_name} already exist"
        result_value = False
        status = EXECUTION_STATE_COMPLETED
    except ExchangeExtensionPackInvalidQuery as e:
        output_message = (
            f"Failed to create a compliance search with the provided advanced query. Please check "
            f"the query syntax or/and query properties. Error is {e}"
        )
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
            f"General error performing action {RUN_COMPLIANCE_SEARCH_SCRIPT_NAME}"
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


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
