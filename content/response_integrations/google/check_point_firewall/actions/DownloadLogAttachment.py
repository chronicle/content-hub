from __future__ import annotations
from base64 import b64decode
from ..core.CheckpointManager import CheckpointManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.UtilsManager import save_attachment
from ..core.constants import (
    DOWNLOAD_LOG_ATTACHMENT_SCRIPT_NAME,
    INTEGRATION_NAME,
    PARAMETERS_DEFAULT_DELIMITER,
    PARAMETERS_NEW_LINE_DELIMITER,
    ATTACHMENT_SIZE_LIMIT_MB,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DOWNLOAD_LOG_ATTACHMENT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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
    log_ids_string = extract_action_param(
        siemplify, param_name="Log IDs", is_mandatory=True, print_value=True
    )
    log_ids = (
        [
            log_id.strip()
            for log_id in log_ids_string.split(PARAMETERS_DEFAULT_DELIMITER)
            if log_id.strip()
        ]
        if log_ids_string
        else []
    )
    download_path = extract_action_param(
        siemplify,
        param_name="Download Folder Path",
        is_mandatory=True,
        print_value=True,
    )
    case_wall_attachment = extract_action_param(
        siemplify,
        param_name="Create Case Wall Attachment",
        input_type=bool,
        default_value=False,
        is_mandatory=False,
        print_value=True,
    )

    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    downloaded_attachments, succeeded_tasks, failed_tasks, pending_tasks = (
        [],
        [],
        [],
        [],
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        # Get manager's instance
        manager = CheckpointManager(
            server_address=server_address,
            username=username,
            password=password,
            domain=domain_name,
            verify_ssl=verify_ssl,
        )
        # Crate Pending Tasks for log_ids
        for log_id in log_ids:
            try:
                processed_task = manager.get_task_process_data(log_id)
                pending_tasks.append((processed_task.task_id, log_id))
            except Exception as err:
                siemplify.LOGGER.error(f"API failed the request: Reason: {err}")
                siemplify.LOGGER.exception(err)

        # Wait for task completing and get task details if it has already completed
        for pending_task_id, log_id in pending_tasks:
            try:
                if manager.check_the_progress_of_task(
                    pending_task_id, json_payload={"task-id": pending_task_id}
                ):
                    task = manager.get_task_details_parsed(
                        pending_task_id, download_path, log_id
                    )
                    succeeded_tasks.append(task)
            except Exception as err:
                failed_tasks.append((f"{err}", log_id))
                siemplify.LOGGER.error(f"API failed the request: Reason: {err}")
                siemplify.LOGGER.exception(err)

        for task in succeeded_tasks:
            for attachment in task.attachments:
                try:
                    # Save attachment to given path
                    save_attachment(
                        path=download_path,
                        name=attachment.filename,
                        content=b64decode(attachment.content),
                    )
                    downloaded_attachments.append(attachment)
                except Exception as err:
                    siemplify.LOGGER.error(f"Failed request: Reason: {err}")
                    siemplify.LOGGER.exception(err)

        if case_wall_attachment:
            for downloaded_attachment in downloaded_attachments:
                if downloaded_attachment.size < ATTACHMENT_SIZE_LIMIT_MB:
                    # Add content to file
                    siemplify.result.add_attachment(
                        title=f"{downloaded_attachment.filename}",
                        filename=downloaded_attachment.filename,
                        file_contents=downloaded_attachment.content,
                    )

        if succeeded_tasks:
            output_message += (
                "Successfully retrieved attachments in Checkpoint FireWall from the following logs: "
                "\n{}\n".format(
                    PARAMETERS_NEW_LINE_DELIMITER.join(
                        task.log_id for task in succeeded_tasks
                    )
                )
            )

        if failed_tasks:
            output_message += (
                "Action wasn't able to retrieve attachments in Checkpoint FireWall "
                "from the following logs: \n{}\n".format(
                    PARAMETERS_NEW_LINE_DELIMITER.join(
                        log_id for msg, log_id in failed_tasks
                    )
                )
            )

        if not succeeded_tasks:
            output_message = "No attachments were downloaded"

        siemplify.result.add_result_json([data.to_json() for data in succeeded_tasks])
        manager.log_out()
    except Exception as err:
        output_message = f"Error executing action {DOWNLOAD_LOG_ATTACHMENT_SCRIPT_NAME}. Reason: {err}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"status: {status}\nresult_value: {result_value}\noutput_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
