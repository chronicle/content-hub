from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.WorkflowToolsManager import WorkflowToolsManager

SCRIPT_NAME = "Workflow Tools Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    result_value = False
    status = EXECUTION_STATE_FAILED
    output_message = "output message: "

    # A Siemplify API key is required to interact with the API
    api_key = siemplify.extract_configuration_param(
        "Workflow Tools",
        "Siemplify API Key",
    )
    api_root = siemplify.extract_configuration_param(
        "Workflow Tools",
        "Siemplify API Root",
    )
    siemplify_hostname = siemplify.extract_configuration_param(
        "Workflow Tools",
        "Siemplify Instance Hostname",
    )
    slack_webhook_url = siemplify.extract_configuration_param(
        "Workflow Tools",
        "Slack Webhook URL",
    )
    # The approval manager that the case/alert should be assigned to
    reviewer = siemplify.extract_configuration_param(
        "Workflow Tools",
        "Approval Manager",
    )
    reviewer_secondary = siemplify.extract_configuration_param(
        "Workflow Tools",
        "Secondary Approval Manager",
        default_value="",
        input_type=str,
    )

    try:
        manager = WorkflowToolsManager(
            siemplify_hostname=siemplify_hostname,
            api_root=api_root,
            api_key=api_key,
            siemplify=siemplify,
            slack_webhook_url=slack_webhook_url,
        )

        manager.check_user(current_user=reviewer, approval_manager=reviewer)
        manager.check_user(current_user=reviewer, approval_manager=reviewer_secondary)
        manager.log_slack_message(f"This is a test message. Posted by {SCRIPT_NAME}.")
        status = EXECUTION_STATE_COMPLETED
        output_message = f"Output Message: Action {SCRIPT_NAME} completed successfully."
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SCRIPT_NAME}. Error: {e}",
        )
        siemplify.LOGGER.exception(e)
        output_message = (
            f"Output Message: General error performing action {SCRIPT_NAME}. Error: {e}"
        )

    result_value = True

    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
