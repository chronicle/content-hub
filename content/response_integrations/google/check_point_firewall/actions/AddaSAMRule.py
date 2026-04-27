from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_unixtime_to_datetime
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.CheckpointManager import CheckpointManager
from ..core.constants import ADD_A_SAM_RULE_SCRIPT_NAME, INTEGRATION_NAME, SLEEP_TIME
import time


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_A_SAM_RULE_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
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
    domain_name = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Domain",
        is_mandatory=False,
        default_value="",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    target = extract_action_param(
        siemplify,
        param_name="Security Gateway to Create SAM Rule on",
        is_mandatory=True,
        print_value=True,
    )
    src_ip = extract_action_param(
        siemplify, param_name="Source IP", is_mandatory=False, print_value=True
    )
    src_netmask = extract_action_param(
        siemplify, param_name="Source Netmask", is_mandatory=False, print_value=True
    )
    dst_ip = extract_action_param(
        siemplify, param_name="Destination IP", is_mandatory=False, print_value=True
    )
    dst_netmask = extract_action_param(
        siemplify,
        param_name="Destination Netmask",
        is_mandatory=False,
        print_value=True,
    )
    port = extract_action_param(
        siemplify,
        param_name="Port",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )
    protocol = extract_action_param(
        siemplify, param_name="Protocol", is_mandatory=False, print_value=True
    )
    expiration = extract_action_param(
        siemplify,
        param_name="Expiration",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )
    action = extract_action_param(
        siemplify,
        param_name="Action for the Matching Connections",
        is_mandatory=True,
        print_value=True,
    )
    track_matching_connections = extract_action_param(
        siemplify,
        param_name="How to Track Matching Connections",
        is_mandatory=True,
        print_value=True,
    )
    close_connections = extract_action_param(
        siemplify,
        param_name="Close Connections",
        is_mandatory=False,
        print_value=True,
        default_value=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    json_results = {}
    checkpoint_manager = None
    result_value = "false"
    task_errors = []
    task_messages = []
    status = EXECUTION_STATE_COMPLETED

    try:
        siemplify.LOGGER.info("Connecting to Checkpoint Firewall")
        checkpoint_manager = CheckpointManager(
            server_address, username, password, domain_name, verify_ssl
        )
        siemplify.LOGGER.info("Constructing command for adding SAM rule.")
        criteria = checkpoint_manager.construct_criteria(
            src_ip, src_netmask, dst_ip, dst_netmask, port, protocol
        )
        command = checkpoint_manager.construct_add_sam_rule_command(
            criteria, action, track_matching_connections, close_connections, expiration
        )
        siemplify.LOGGER.info(f"Command: {command}")
        siemplify.LOGGER.info("Initiating run-script command.")
        task_id = checkpoint_manager.run_script(command, [target])

        siemplify.LOGGER.info(f"Task ID: {task_id}. Waiting for completion.")

        while not checkpoint_manager.is_task_completed(task_id):
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                output_message = (
                    f"Timeout waiting for addition of the following SAM rule: {command}"
                )
                break

            siemplify.LOGGER.info(f"Task {task_id} is not yet completed. Waiting.")
            time.sleep(SLEEP_TIME)

        else:
            # Task has completed and no timeout occurred (no break)
            siemplify.LOGGER.info(
                f"Task {task_id} has finished with status {checkpoint_manager.get_task_status(task_id)}"
            )

            siemplify.LOGGER.info("Publishing changes.")
            checkpoint_manager.publish_changes()

            json_results = checkpoint_manager.get_task_details(task_id)
            try:
                # Collect errors from responseError fields from task details
                task_errors = checkpoint_manager.get_task_response_errors(task_id)
            except Exception as e:
                siemplify.LOGGER.error("Unable to collect errors from task details.")
                siemplify.LOGGER.exception(e)

            try:
                # Collect messages from responseMessage fields from task details
                task_messages = checkpoint_manager.get_task_response_messages(task_id)
            except Exception as e:
                siemplify.LOGGER.error("Unable to collect messages from task details.")
                siemplify.LOGGER.exception(e)

            if checkpoint_manager.is_task_succeeded(task_id):
                # Task completed successfully
                output_message = (
                    f"Successfully added SAM rule with the following command: {command}"
                )
                result_value = "true"

            elif checkpoint_manager.is_task_succeeded_with_warnings(task_id):
                # Task has completed only partially
                output_message = f"SAM rule addition with the following fw sam command succeeded with warnings: {command}"

            elif checkpoint_manager.is_task_partially_succeeded(task_id):
                # Task has completed only partially
                output_message = f"SAM rule addition with the following fw sam command partially succeeded: {command}"

            else:
                # Task has failed
                output_message = (
                    f"Failed to add SAM rule with the following command: {command}"
                )

            if task_messages:
                output_message += "\n\nfw sam command output:\n   {}".format(
                    "\n   ".join([msg for msg in task_messages])
                )

            if task_errors:
                output_message += "\n\nfw sam command errors:\n   {}".format(
                    "\n   ".join([str(error) for error in task_errors])
                )
        checkpoint_manager.log_out()
    except Exception as e:
        siemplify.LOGGER.error(f"Failed to execute Add SAM Rule action! Error is {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to execute Add SAM Rule action! Error is {e}"

    if json_results:
        siemplify.result.add_result_json(json_results)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
