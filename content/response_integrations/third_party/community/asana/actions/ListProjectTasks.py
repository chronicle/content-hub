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

    project_name = siemplify.extract_action_param("Project Name")
    task_to_show = siemplify.extract_action_param("Completed Status")

    # Creating an instance of AsanaManager object
    asana_manager = AsanaManager(personal_access_token, base_url)

    project_id = asana_manager.get_project_id(project_name)

    all_tasks_list = asana_manager.get_tasks_from_a_project(project_id)

    if all_tasks_list["data"] is not None:
        for task in all_tasks_list["data"]:
            task_id = task["gid"]
            task_detail = asana_manager.get_a_task(task_id)  # Task details
            if (
                str(task_detail.get("data", {}).get("completed")).lower()
                == task_to_show
            ):
                task_name = task_detail["data"]["name"]

                # Adding the task to the json result
                json_result[f"Task name: {task_name}"] = task_detail
                output_message = f"The tasks for the project: {project_name} were fetched successfully"
                return_value = True

                # Adding the tasks URLs
                title = f"The task name: {task_name} , Due date: {task_detail['data']['due_on']}"
                link = task_detail["data"]["permalink_url"]
                siemplify.result.add_link(title, link)

    else:
        output_message = f"No tasks were found for this project {project_name}"
        return_value = False
        # Adding json result to the action
    siemplify.result.add_result_json(json_result)

    siemplify.end(output_message, return_value)


if __name__ == "__main__":
    main()
