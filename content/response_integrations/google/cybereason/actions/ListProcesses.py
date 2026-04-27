from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.CybereasonManager import CybereasonManager
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, LIST_PROCESSES_SCRIPT_NAME
from ..core.utils import string_to_multi_value, validate_positive_integer


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_PROCESSES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate Base64",
    )

    process_name = string_to_multi_value(
        extract_action_param(siemplify, param_name="Process Name", print_value=True)
    )
    machine_name = string_to_multi_value(
        extract_action_param(siemplify, param_name="Machine Name", print_value=True)
    )
    only_suspicious = extract_action_param(
        siemplify, param_name="Has Suspicions", input_type=bool, print_value=True
    )
    has_incoming_connection = extract_action_param(
        siemplify,
        param_name="Has Incoming Connection",
        input_type=bool,
        print_value=True,
    )
    has_outgoing_connection = extract_action_param(
        siemplify,
        param_name="Has Outgoing Connection",
        input_type=bool,
        print_value=True,
    )
    has_external_connection = extract_action_param(
        siemplify,
        param_name="Has External Connection",
        input_type=bool,
        print_value=True,
    )
    unsigned_unknown_reputation = extract_action_param(
        siemplify,
        param_name="Unsigned process with unknown reputation",
        input_type=bool,
        print_value=True,
    )
    from_temporary_folder = extract_action_param(
        siemplify,
        param_name="Running from temporary folder",
        input_type=bool,
        print_value=True,
    )
    privileges_escalation = extract_action_param(
        siemplify, param_name="Privilege Escalation", input_type=bool, print_value=True
    )
    malicious_psexec = extract_action_param(
        siemplify,
        param_name="Malicious use of PsExec",
        input_type=bool,
        print_value=True,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Results Limit",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    json_results = {}

    try:
        manager = CybereasonManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_b64=ca_certificate,
            force_check_connectivity=True,
        )
        validate_positive_integer(limit)
        processes = manager.get_processes(
            process_name=process_name,
            machine_name=machine_name,
            only_suspicious=only_suspicious,
            has_incoming_connection=has_incoming_connection,
            has_outgoing_connection=has_outgoing_connection,
            has_external_connection=has_external_connection,
            unsigned_unknown_reputation=unsigned_unknown_reputation,
            from_temporary_folder=from_temporary_folder,
            privileges_escalation=privileges_escalation,
            malicious_psexec=malicious_psexec,
            limit=limit,
        )

        if processes:
            processes = processes[:limit]
            csv_output = construct_csv([process.to_csv() for process in processes])
            siemplify.result.add_data_table("Processes", csv_output)
            output_message = (
                f"Successfully retrieved information about processes based on provided criteria in "
                f"{INTEGRATION_NAME}."
            )
            siemplify.result.add_result_json(
                [process.to_json() for process in processes]
            )

        else:
            output_message = f"No processes were found based on provided criteria in {INTEGRATION_NAME}."

        status = EXECUTION_STATE_COMPLETED
        result_value = len(processes)

    except Exception as e:
        output_message = (
            f"Error executing action {LIST_PROCESSES_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = 0

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  num_of_processes: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
