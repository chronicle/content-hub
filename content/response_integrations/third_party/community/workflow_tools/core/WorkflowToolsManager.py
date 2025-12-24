from __future__ import annotations

import requests

API_MOVE_ALERT = "{0}/api/external/v1/cases/MoveAlertToNewCase"
API_GET_USER_PROFILES = "{0}/api/external/v1/settings/GetUserProfiles"


class WorkflowToolsManager:
    def __init__(
        self,
        api_root=None,
        api_key=None,
        verify_ssl=False,
        siemplify=None,
        slack_webhook_url=None,
        siemplify_hostname="https://localhost",
    ):
        self.api_root = api_root
        self.api_key = api_key
        self.slack_webhook_url = slack_webhook_url
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(
            {
                "accept": "application/json",
                "AppKey": f"{api_key}",
                "Content-Type": "application/json",
            },
        )
        self.siemplify = siemplify
        self.siemplify_hostname = siemplify_hostname

    def move_alert(self, case_id, alert_id):
        data = {"sourceCaseId": case_id, "alertIdentifier": f"{alert_id}"}
        response = self.query_api(
            query_url=API_MOVE_ALERT.format(self.api_root),
            json_payload=data,
        )

        if response.status_code != 200:
            e = f"Failed to move alert {alert_id} from case {case_id}. Got HTTP error {response.status_code}. \nResponse Content: \n{response.content}"
            self.siemplify.LOGGER.error(e)
            self.siemplify.LOGGER.exception(e)
            raise ValueError(e)

        return response.json().get("newCaseId", None)

    def assign_case(self, user, case_id, alert_id):
        self.siemplify.assign_case(user, case_id, alert_id)

    def check_user(self, current_user, approval_manager):
        result = False
        # Check if the approval manager name is a role
        if current_user.startswith("@") and current_user == approval_manager:
            result = True
        elif approval_manager.startswith("@"):
            result = self.check_user_role(
                username=current_user,
                role_name=approval_manager,
            )
        elif current_user == approval_manager and approval_manager != "":
            result = True
        return result

    def check_user_role(self, username, role_name):
        self.siemplify.LOGGER.info(
            f"Checking whether user {username} is a member of the role {role_name}",
        )
        ## Checks if a given username belongs to a given role.

        # First find the users ID
        result = False

        payload = {
            "searchTerm": f"{username}",
            "filterRole": True,
            "requestedPage": 0,
            "pageSize": 1,
            "shouldHideDisabledUsers": True,
        }

        response = self.query_api(
            query_url=API_GET_USER_PROFILES.format(self.api_root),
            json_payload=payload,
        )

        user_json = response.json().get("objectsList", None)
        if user_json:
            query_user_name = user_json[0].get("userName", None)
            query_user_id = user_json[0].get("id", None)
            query_user_role = user_json[0].get("socRole", None)
            # Check for partial match of usernames to ensure we don't falsely retrieve the ID of a person with a similar username.
            if username == query_user_name:
                self.siemplify.LOGGER.info(
                    f"The user ID of {username} is {query_user_id}",
                )
                # Check if the role matches
                if role_name == query_user_role:
                    result = True
            else:
                msg = f"When querying for the username {username} we found a username of {query_user_name} with ID {query_user_id}. These usernames do not match"
                self.siemplify.LOGGER.error(msg)

        return result

    def query_api(self, query_url, json_payload):
        ## Modular function to query the Siemplify API and handle non 200 responses

        response = self.session.post(query_url, json=json_payload)
        if response.status_code != 200:
            e = f"Failed to query Siemplify API with URL {query_url}\nHTTP code: {response.status_code}\nResponse Content:\n{response.content}\n"
            self.siemplify.LOGGER.error(e)
            self.siemplify.LOGGER.exception(e)
            raise ValueError(e)
        return response

    def log_slack_message(self, message):
        # Basic implementation of a slack Webhook. A Webhook custom integration must be configured in Slack, and the Webhook URL given in the Siemplify integration settings.
        if self.slack_webhook_url:
            payload = {"text": "Workflow Approvals:" + "\n> " + str(message)}
            response = requests.post(self.slack_webhook_url, json=payload)
            if response.status_code != 200:
                e = f'Failed to send the following slack message: \n"{message}" \nHTTP Code: {response.status_code} \nResponse Content: \n{response.content}\n'
                self.siemplify.LOGGER.error(e)
                self.siemplify.LOGGER.exception(e)
                raise ValueError(e)
        else:
            self.siemplify.LOGGER.info(
                "No Slack Webhook URL was given in the integration settings. Skipping log_slack_message.",
            )
