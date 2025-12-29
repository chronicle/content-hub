from __future__ import annotations

import requests

headers = {
    "content-type": "application/json",
    "Accept": "application/json",
    "Authorization": "Bearer token",
}


class AsanaManager:
    """Asana Manager"""

    def __init__(self, token, base_url):
        """Init function
        :param token: String, the personal access token (PAT)
        """
        self.session = requests.Session()
        self.session.headers.update(headers)
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.base_url = base_url

    def test_connectivity(self):
        """Test connectivity to Asana
        :return: {bool} True if successful, exception otherwise.
        """
        url = f"{self.base_url}/users/me"
        response = self.session.get(url)
        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_project_id(self, project_name):
        """Getting the project id by a given project name
        :param project_name: String
        :return: String, the project id
        """
        project_id = None

        url = f"{self.base_url}/projects"
        response = self.session.get(url)
        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)

        all_projects_for_a_user = response.json()

        for project in all_projects_for_a_user["data"]:
            if project.get("name") == project_name:
                project_id = project.get("gid")

        return project_id

    def get_user_id(self, user_email):
        """Getting the user id by a given user email
        :param user_email: The user's email you would like to get the information from.
        :return: String, the user id
        """
        url = f"{self.base_url}/users/{user_email}"
        response = self.session.get(url)
        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)
        user_data = response.json()

        return user_data["data"]["gid"]

    def get_workspace_id_by_name(self, workspace_name):
        """Getting the workspace id by a given workspace name
        :param workspace_name: String, Note: Its case sensitive
        :return: String, the workspace id
        """
        workspace_id = ""
        url = f"{self.base_url}/workspaces"
        response = self.session.get(url)

        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)

        all_workspaces = response.json()
        for workspace in all_workspaces["data"]:
            if workspace.get("name") == workspace_name:
                workspace_id = workspace.get("gid")

        return workspace_id

    def add_user_to_workspace(self, workspace_id, user_email):
        """Adding a user to a workspace
        :param workspace_id: String, the workspace ID to which the user is added (Note: this is case sensitive).
        :param user_email: String, the user's email you would like to add.
        :return: dict, the added user information.
        """
        url = f"{self.base_url}/workspaces/{workspace_id}/addUser"
        data = {"data": {"user": user_email}}

        response = self.session.post(url, json=data)
        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def remove_user_from_workspace(self, workspace_id, user_email):
        """Removing a user from a workspace
        :param workspace_id: String, the workspace ID to which the user is added (Note: this is case sensitive).
        :param user_email: String, the user's email you would like to remove.
        :return: Dict, an empty user data (data:{})
        """
        url = f"{self.base_url}/workspaces/{workspace_id}/removeUser"
        data = {"data": {"user": user_email}}

        response = self.session.post(url, json=data)
        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def create_task(
        self,
        task_subject,
        project_id,
        description,
        assignee=None,
        due_date=None,
    ):
        """Creating a new task in a project
        :param task_subject: String, The task subject
        :param assignee: String, The assignee's ID
        :param due_date: String, YYYY-MM-DD format
        :param project_id: String, the project ID to which the task is created
        :param description: String, the description of the task
        :return: Dict, the created task information
        """
        data = {
            "data": {
                "name": task_subject,
                "assignee": assignee,
                "due_on": due_date,
                "projects": [project_id],
                "notes": description,
            },
        }
        url = f"{self.base_url}/tasks"
        response = self.session.post(url, json=data)
        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def update_task(self, task_id, assignee, due_date, description):
        """Updating a task by updating each wanted field of the task
        :param task_id: String, the task id to update
        :param assignee: String, the new assignee to assign the task
        :param due_date: String, the new due date to update
        :param description: String, the new description to update
        :return: Dict, the updated task information
        """
        data = {
            "data": {"assignee": assignee, "due_on": due_date, "notes": description},
        }
        url = f"{self.base_url}/tasks/{task_id}"

        response = self.session.put(url, json=data)
        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_tasks_from_a_project(self, project_id):
        """Getting all the tasks from a project
        :param project_id: String, the project id to which getting all the tasks from
        :return: Dict, the tasks information
        """
        url = f"{self.base_url}/projects/{project_id}/tasks"
        response = self.session.get(url)
        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_users_tasks_list_id(self, user_id, workspace_id):
        """Getting user's tasks list id
        :param user_id: String, the user id to whom the tasks list is associated
        :param workspace_id: String, the workspace id of the user
        :return: String, the user's tasks list ID
        """
        url = f"{self.base_url}/users/{user_id}/user_task_list"
        params = {"workspace": workspace_id}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)

        users_tasks_list_id = response.json()["data"]["gid"]
        return users_tasks_list_id

    def get_tasks_from_a_user_tasks_list(self, users_tasks_list_id):
        """Getting all the tasks from a user's tasks list
        :param users_tasks_list_id: String, the user's tasks list ID
        :return: Dict, all the task information
        """
        url = f"{self.base_url}/user_task_lists/{users_tasks_list_id}/tasks"
        response = self.session.get(url)
        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_a_task(self, task_id):
        """Getting a task details
        :param task_id: int, the task id.
        """
        url = f"{self.base_url}/tasks/{task_id}"
        response = self.session.get(url)
        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_custom_field_list(self, workspace_id):
        """Getting a cutom field list
        :param workspace_id: int, the workspace id .
        """
        url = f"{self.base_url}/workspaces/{workspace_id}/custom_fields"
        response = self.session.get(url)
        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_custom_field(self, custom_field_id):
        """Getting a custom field details
        :param custom_field_id: int, the custom field id.
        """
        url = f"{self.base_url}/custom_fields/{custom_field_id}"
        response = self.session.get(url)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()
