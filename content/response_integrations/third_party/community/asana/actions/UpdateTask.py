from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AsanaManager import AsanaManager

IDENTIFIER = "Asana"


@output_handler
def main():
    siemplify = SiemplifyAction()

    personal_access_token = siemplify.extract_configuration_param(IDENTIFIER, "Token")
    base_url = siemplify.extract_configuration_param(IDENTIFIER, "Base URL")

    task_id = siemplify.extract_action_param("Task ID")
    task_assignee = siemplify.extract_action_param("Assignee")
    task_due_date = siemplify.extract_action_param("Due Date")
    task_description = siemplify.extract_action_param("Description")

    # Creating an instance of AsanaManager object
    asana_manager = AsanaManager(personal_access_token, base_url)

    assignee_user_id = asana_manager.get_user_id(task_assignee)

    updated_task = asana_manager.update_task(
        task_id,
        assignee_user_id,
        task_due_date,
        task_description,
    )

    if updated_task["data"] is not None:
        output_message = f"The task {task_id} was updated successfully"
        return_value = True

    # Adding json result to the action
    siemplify.result.add_result_json(updated_task)

    siemplify.end(output_message, return_value)


if __name__ == "__main__":
    main()
