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

    # Creating an instance of AsanaManager object
    asana_manager = AsanaManager(personal_access_token, base_url)

    task_details = asana_manager.get_a_task(task_id)

    if task_details["data"] is not None:
        output_message = f"The task {task_id} was updated successfully"
        return_value = True
        # Adding the tasks URLs
        title = f"The task name: {task_details['data']['name']} , Due date: {task_details['data']['due_on']}"
        link = task_details["data"]["permalink_url"]
        siemplify.result.add_link(title, link)

    else:
        output_message = f"The task {task_id} wasn't found"
        return_value = False
    # Adding json result to the action
    siemplify.result.add_result_json(task_details)

    siemplify.end(output_message, return_value)


if __name__ == "__main__":
    main()
