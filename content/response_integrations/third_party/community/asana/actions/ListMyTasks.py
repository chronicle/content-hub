from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AsanaManager import AsanaManager

IDENTIFIER = "Asana"


@output_handler
def main():
    siemplify = SiemplifyAction()

    json_result = {}

    personal_access_token = siemplify.extract_configuration_param(IDENTIFIER, "Token")
    base_url = siemplify.extract_configuration_param(IDENTIFIER, "Base URL")

    workspace_name = siemplify.extract_action_param("Workspace Name")
    user_email = siemplify.extract_action_param("User's Email")
    task_status_to_show = siemplify.extract_action_param("Completed Status")

    # Creating an instance of AsanaManager object
    asana_manager = AsanaManager(personal_access_token, base_url)

    user_id = asana_manager.get_user_id(user_email)
    workspace_id = asana_manager.get_workspace_id_by_name(workspace_name)

    user_tasks_list_id = asana_manager.get_users_tasks_list_id(user_id, workspace_id)

    user_tasks_list = asana_manager.get_tasks_from_a_user_tasks_list(user_tasks_list_id)

    if user_tasks_list["data"] is not None:
        output_message = (
            f"The tasks for the user {user_email} were fetched successfully"
        )
        return_value = True

        for task in user_tasks_list["data"]:
            task_id = task["gid"]
            task_detail = asana_manager.get_a_task(task_id)  # Task details

            if str(task_detail["data"]["completed"]).lower() == task_status_to_show:
                task_name = task_detail["data"]["name"]

                # Adding the task to the json result
                json_result[f"Task name: {task_name}"] = task_detail
                output_message = (
                    f"The tasks for the user: {user_email} were fetched successfully"
                )
                return_value = True

                # Adding the tasks URLs
                title = f"The task name: {task_name} , Due date: {task_detail['data']['due_on']}"
                link = task_detail["data"]["permalink_url"]
                siemplify.result.add_link(title, link)

    else:
        output_message = f"The user {user_email} has no associated tasks"
        return_value = False

    # Adding json result to the action
    siemplify.result.add_result_json(json_result)

    siemplify.end(output_message, return_value)


if __name__ == "__main__":
    main()
