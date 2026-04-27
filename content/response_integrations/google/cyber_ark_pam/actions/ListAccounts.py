from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED
from ..core.CyberArkPamManager import CyberArkPamManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import INTEGRATION_NAME

SCRIPT_NAME = "List Accounts"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
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
    ca_certificate = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="CA Certificate"
    )
    client_certificate = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client Certificate"
    )
    client_certificate_passphrase = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Certificate Passphrase",
        remove_whitespaces=False,
    )

    search_query = extract_action_param(
        siemplify, param_name="Search Query", print_value=True
    )
    search_operator = extract_action_param(
        siemplify, param_name="Search operator", print_value=True
    )
    max_records_to_return = extract_action_param(
        siemplify, param_name="Max Records To Return", input_type=int, print_value=True
    )
    records_offset = extract_action_param(
        siemplify, param_name="Records Offset", input_type=int, print_value=True
    )
    filter_query = extract_action_param(
        siemplify, param_name="Filter Query", print_value=True
    )
    saved_filter = extract_action_param(
        siemplify, param_name="Saved Filter", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = "false"
    output_message = ""

    try:
        if filter_query and saved_filter:
            output_message += (
                "Both the Filter Query and Saved Filter parameters are provided, "
                "Saved Filter takes priority"
            )

        if max_records_to_return is not None and max_records_to_return <= 0:
            raise Exception(
                f"Invalid value was provided for “Max Records to Return”: "
                f"{max_records_to_return}. Positive number should be provided”."
            )

        if records_offset is not None and records_offset < 0:
            raise Exception(
                f"Invalid value was provided for “Records Offset to Return”: "
                f"{records_offset}. Non negative number should be provided"
            )

        cyber_ark_manager = CyberArkPamManager(
            api_root=api_root,
            username=username,
            password=password,
            siemplify=siemplify,
            verify_ssl=verify_ssl,
            ca_certificate=ca_certificate,
            client_certificate=client_certificate,
            client_certificate_passphrase=client_certificate_passphrase,
        )
        siemplify.LOGGER.info("Connected successfully.")

        accounts = cyber_ark_manager.list_accounts(
            search_query=search_query,
            search_operator=search_operator,
            max_records_to_return=max_records_to_return,
            records_offset=records_offset,
            filter_query=filter_query,
            saved_filter=saved_filter,
        )
        if accounts:
            siemplify.result.add_result_json(
                [account.to_flat() for account in accounts]
            )
            siemplify.result.add_data_table(
                "Available PAM Accounts",
                construct_csv([account.to_csv() for account in accounts]),
            )
            result_value = "true"
            log_message = (
                "Successfully found accounts for the provided criteria in CyberArk PAM"
            )
            output_message += log_message
            siemplify.LOGGER.info(log_message)
        else:
            log_message = (
                "No accounts were found for the provided criteria in CyberArk PAM"
            )
            output_message += log_message
            siemplify.LOGGER.info(log_message)

    except Exception as e:
        log_message = f"Error executing action “{SCRIPT_NAME}”. Reason: {e}"
        siemplify.LOGGER.error(log_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = log_message

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
