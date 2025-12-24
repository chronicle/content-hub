from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.WorkflowToolsManager import WorkflowToolsManager


@output_handler
def main():
    SYSTEM_USER = "System"
    siemplify = SiemplifyAction()

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

    manager = WorkflowToolsManager(
        siemplify_hostname=siemplify_hostname,
        api_root=api_root,
        api_key=api_key,
        siemplify=siemplify,
    )
    # The ID of the case
    case_id = siemplify.case.identifier
    # The ID of the current alert
    alert_id = siemplify.current_alert.identifier
    # The user that executed this action
    requesting_user = siemplify.original_requesting_user
    if requesting_user != SYSTEM_USER:
        siemplify.LOGGER.info(
            f"Attempting to assign case {case_id} to user: {requesting_user}",
        )
        manager.assign_case(requesting_user, case_id, alert_id)
    else:
        e = f'"Assign Case to Current User" action failed on case {case_id} because the user was "{requesting_user}": This playbook action must be set to manual excecution to work.'
        siemplify.LOGGER.error(e)
        siemplify.LOGGER.exception(e)
        raise ValueError(e)

    status = EXECUTION_STATE_COMPLETED
    output_message = f"output message : Assigned case to {requesting_user}"
    result_value = requesting_user
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
