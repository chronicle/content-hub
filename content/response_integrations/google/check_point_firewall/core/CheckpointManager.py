# ==============================================================================
# title           :CheckpointManager.py
# description     :This Module contain all Checkpoint firewall's functionality
# author          :zivh@siemplify.co
# date            :2-28-18
# python_version  :3.7
# DOC             :https://sc1.checkpoint.com/documents/latest/APIs/index.html#web/show-objects~v1.1%20
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
from .exceptions import (
    CheckpointManagerNotFoundException,
    CheckpointManagerError,
    InvalidGroupException,
)
from .CheckpointParser import CheckpointParser
from .UtilsManager import validate_response
import requests
import base64
import time


# =====================================
#             CONSTANTS               #
# =====================================

BASE_URL = "https://{}/web_api/{}"
TIME_TO_SLEEP = 1
HEADERS = {"Content-Type": "application/json"}

TASK_FAILED_STATUS = "failed"
TASK_SUCCESS_STATUS = "succeeded"
TASK_SUCCESS_WITH_WARNINGS_STATUS = "succeeded with warnings"
TASK_PARTIAL_SUCCESS_STATUS = "partially succeeded"
TASK_PROGRESS_STATUS = "in progress"
LAYER_PAYLOAD = {"offset": 0, "details-level": "full"}


# =====================================
#              CLASSES                #
# =====================================
class CheckpointManager:
    """
    Responsible for all checkpoint firewall operations
    """

    def __init__(self, server_address, username, password, domain="", verify_ssl=False):
        """
        The method is used to init an object of Manager class
        :param server_address: {str} Server address of Checkpoint
        :param username: {str} Specify username of the IBoss account
        :param password: {str} Specify password of the IBoss account
        :param domain: {str} Specify password of the IBoss account
        :param verify_ssl: {bool} Enable (True) or disable (False). If enabled, verify the SSL certificate for the
            connection to the Checkpoint public cloud server is valid
        """
        self.session = requests.session()
        self.server_address = server_address  # Port: 443
        self.username = username
        self.password = password
        self.domain = domain
        self.session.verify = verify_ssl
        self.session.headers.update(HEADERS)
        self.parser = CheckpointParser()
        self.__set_authorization()

    def __set_authorization(self):
        """
        Set authorization.
        """
        json_payload = {
            "user": self.username,
            "password": self.password,
            "domain": self.domain,
        }
        # Login to the server with username and password. The server shows your session unique identifier.
        response = self._api_call(command="login", json_payload=json_payload)
        validate_response(response)
        login_result = response.json()
        # Add session id header
        self.session.headers.update({"X-chkp-sid": login_result["sid"]})

    def test_connectivity(self):
        """
        Test connectivity.
        :return: {bool} True if successful else raise exception.
        """
        return bool(self.session.headers.get("X-chkp-sid"))

    def _api_call(self, command, json_payload=None):
        """
        Responsible for all checkpoint requests
        :param command: {str} Dynamic endpoint for call from server address
        :param json_payload: {dict} Parameters for given endpoint
        :return: {requests.Response} Request response
        """
        response = self.session.post(
            BASE_URL.format(self.server_address, command), json=json_payload or {}
        )

        return response

    def check_the_progress_of_task(self, task_id, json_payload=None):
        """
        Using the show-task command to check the progress of the task.
        :param task_id: {dict} The task id parameter
        :param json_payload: {dict} The json payload parameter
        :return: {bool} task status is succeeded
        """
        json_payload = json_payload if json_payload else task_id
        in_progress = True
        while in_progress:
            in_progress = False
            response = self._api_call(command="show-task", json_payload=json_payload)
            validate_response(response)
            tasks_list = response.json()

            if tasks_list:
                task_status = tasks_list.get("tasks")[0]["status"]
                if task_status == TASK_FAILED_STATUS:
                    raise CheckpointManagerError(
                        f"Failed to complete task - {tasks_list['tasks'][0]['task-name']}"
                    )

                if task_status == TASK_PROGRESS_STATUS:
                    in_progress = True
                    # Wait before next iteration
                    time.sleep(TIME_TO_SLEEP)

        # Task status is succeeded
        return True

    def install_policy(self, name_of_policy_package):
        """
        Install policy
        :param name_of_policy_package: {str} The name of the Policy Package to be installed.
        :return: {bool} Is task completed or no
        """
        json_payload = {
            "policy-package": name_of_policy_package,
            "access": True,
            "threat-prevention": True,
        }
        response = self._api_call(command="install-policy", json_payload=json_payload)
        validate_response(response)
        # check the progress of the task.
        return self.check_the_progress_of_task(task_id=response.json())

    def publish_changes(self):
        """
        Checkpoint demands a publish action for changes to take effect
        :return: {bool} Is task completed or no
        """
        response = self._api_call(command="publish", json_payload={})
        validate_response(response)
        # check the progress of the task.
        return self.check_the_progress_of_task(task_id=response.json())

    def show_group(self, group_name):
        """
        Retrieve existing object using object name
        :param group_name: {str} The name of group
        :return: {dict} Given Group data
        """
        response = self._api_call(
            command="show-group", json_payload={"name": group_name}
        )
        validate_response(response)

        return response.json()

    def is_address_range_exists(self, address):
        """
        Retrieve existing object using object name
        :param address: {str} ip address
        :return: {bool} Is address exists or no
        """
        try:
            response = self._api_call(
                "show-address-range", json_payload={"name": address}
            )
            validate_response(response)

            return True
        except CheckpointManagerNotFoundException:
            return False

    def create_address_range(self, address_object, group_name):
        """
        Create new address-range object with group
        :param address_object: {str} Ip address
        :param group_name: {str} Name of the group
        """
        json_payload = {
            "name": address_object,
            "ip-address-first": address_object,
            "ip-address-last": address_object,
            "groups": [group_name],
        }
        response = self._api_call(
            command="add-address-range", json_payload=json_payload
        )
        validate_response(response)

    def add_address_range_to_group(self, address_to_block, group_name):
        """
        Create new address-range object with group
        :param address_to_block: {str} Ip address
        :param group_name: {str} Name of the group
        """
        # Edit group - add address range object to group
        json_payload = {"name": group_name, "members": {"add": address_to_block}}
        response = self._api_call(command="set-group", json_payload=json_payload)
        validate_response(response)

    def validate_if_group_editable(self, group_name, group):
        """
        Validate group name, raise exception is group is not valid
        :param group_name: {str} Name of the group to validate
        :param group: {str} group to validate
        :return: {bool} Return True if valid, else raise exception
        """
        # Check if group exist
        if not group:
            raise InvalidGroupException(f"Error. Cannot find {group_name} Group.")

        # Check if group is block for editing
        if group.get("read-only"):
            raise InvalidGroupException(
                f"Group {group_name} cannot be edited, set to readonly"
            )

        return True

    def block_ip_in_policy_group(self, address_to_block, group_name):
        """
        Add address range object to group
        :param address_to_block: {str} Name of the IP address range object to add to the group
        :param group_name: {str} Name of the group to add the address range object in
        :return: {bool} Is ip added successfully to the group
        """
        # Check if group exist
        try:
            group = self.show_group(group_name)
        except:
            raise InvalidGroupException(f"Error. Cannot find {group_name} Group.")

        self.validate_if_group_editable(group_name=group_name, group=group)

        # Check if address object already exist
        is_exist = self.is_address_range_exists(address_to_block)
        if is_exist:
            self.add_address_range_to_group(address_to_block, group_name)
        else:
            # This will also add the new address to the given group
            self.create_address_range(address_to_block, group_name)

        self.publish_changes()
        return True

    def unblock_ip_in_policy_group(self, address_to_unblock_name, group_name):
        """
        Remove ip entry from policy group
        :param address_to_unblock_name: {str} Name of the address range object to remove from the group
        :param group_name: {str} Name of the group to remove the address range object from
        :return: {bool} Ip removed successfully from the group
        """
        # Check if group exist and if is block for editing
        try:
            group = self.show_group(group_name)
        except:
            raise InvalidGroupException(f"Error. Cannot find {group_name} Group.")

        self.validate_if_group_editable(group=group, group_name=group_name)
        # Edit group - remove address range object from the group
        json_payload = {
            "name": group_name,
            "members": {"remove": address_to_unblock_name},
        }
        response = self._api_call(command="set-group", json_payload=json_payload)

        validate_response(response)

        self.publish_changes()
        return True

    def discard(self):
        """
        All changes done by user are discarded and removed from database.
        """
        response = self._api_call(command="discard", json_payload={})

        validate_response(response)

    def log_out(self):
        """
        Log out from the current session. After logging out the session id is not valid any more.
        """
        response = self._api_call(command="logout", json_payload={})
        validate_response(response)

    def get_access_layers(self, limit=50):
        """
        Returns a json with access layers
        :param: {int} Limit of the layers
        :return: {list} list of AccessLayer object
        """
        json_payload = LAYER_PAYLOAD
        json_payload["limit"] = limit
        response = self._api_call(
            command="show-access-layers", json_payload=json_payload
        )
        validate_response(response)

        return self.parser.get_access_layers(response.json())

    def get_threat_layers(self, limit=50):
        """
        Returns a json with threat layers
        :param: {int} Limit of the layers
        :return: {list} list of ThreatLayer object
        """
        json_payload = LAYER_PAYLOAD
        json_payload["limit"] = limit
        response = self._api_call(
            command="show-threat-layers", json_payload=json_payload
        )
        validate_response(response)

        return self.parser.get_threat_layers(response.json())

    def get_policies_parsed(self, policies):
        """
        Returns a json with all policies
        :param: {dict} Policies should be parsed
        :return: {list} list of Policy object
        """
        return self.parser.get_policies(policies)

    def get_policies(self, limit):
        """
        Returns a json with all policies
        :param: {int} Limit of the policies
        :return: {dict} list of policies result
        """
        json_payload = LAYER_PAYLOAD
        json_payload["limit"] = limit
        response = self._api_call(command="show-packages", json_payload=json_payload)
        validate_response(response)

        return response.json()

    def show_application_site_group(self, application_group_name):
        """
        Retrieve existing object using application group name
        :param application_group_name: {str} Application group name.
        :return: {dict} application site group details
        """
        response = self._api_call(
            "show-application-site-group", json_payload={"name": application_group_name}
        )
        validate_response(response)

        return response.json()

    def show_application_site(self, application_name):
        """
        Retrieve existing object using application name
        :param application_name: {str} Application name.
        :return: {dict} application site details
        """
        try:
            response = self._api_call(
                "show-application-site", json_payload={"name": application_name}
            )
            validate_response(response)

            return response.json()
        except CheckpointManagerNotFoundException:
            return False

    def create_application_site(self, application_name, application_url):
        """
        Creates new application site, which can be initialized with 'url-list' or 'application-signature' (not both)
        :param application_name: {str} Application name. Should be unique in domain.
        :param application_url: {str} URL that determine this particular application.
        :return: {dict} application site details
        """
        json_payload = {
            "name": application_name,
            "url-list": application_url,
            "primary-category": "Custom_Application_Site",
        }
        response = self._api_call(
            command="add-application-site", json_payload=json_payload
        )
        validate_response(response)

        return response.json()

    def add_application_site_to_group(
        self, application_name, application_url, application_group_name
    ):
        """
        Edit existing group.
        It's impossible to set 'application-signature' when the application was initialized
            with 'url-list' and vice-verse.
        :param application_name: {str} Application name. Should be unique in domain.
        :param application_url: {str} URL that determine this particular application.
        :param application_group_name: {str} Object name. Should be unique in domain.
        :return: {dict} application site group details
        """
        application = self.show_application_site(application_name)
        # Check if application site exist
        if not application:
            application = self.create_application_site(
                application_name, application_url
            )

        json_payload = {
            "name": application_group_name,
            "members": {"add": application["name"]},
        }
        response = self._api_call(
            command="set-application-site-group", json_payload=json_payload
        )
        validate_response(response)

        return response.json()

    def block_url_in_group(self, url_name, url_to_block, application_group_name):
        """
        Add url to application site group object
        :param url_name: {str} URL address name
        :param url_to_block: {str} URL to block
        :param application_group_name: {str} Name of the group
        :return: {bool} url was added successfully to group
        """
        # Check if group exist
        try:
            group = self.show_application_site_group(application_group_name)
        except:
            raise InvalidGroupException(
                f"Error. Cannot find {application_group_name} Group."
            )

        self.validate_if_group_editable(group=group, group_name=application_group_name)
        # Check if group is block for editing
        self.add_application_site_to_group(
            url_name, url_to_block, application_group_name
        )
        self.publish_changes()
        return True

    def unblock_url_in_group(self, application_name_to_unblock, application_group_name):
        """
        Remove ip entry from policy group
        :param application_name_to_unblock: {str} Name of the url object to remove from the group
        :param application_group_name: {str} Name of the group to remove the url object from
        :return: {bool} removed successfully from the group
        """
        # Check if group exist and if is block for editing
        try:
            group = self.show_application_site_group(application_group_name)
        except:
            raise InvalidGroupException(
                f"Error. Cannot find {application_group_name} Group."
            )

        self.validate_if_group_editable(group_name=application_group_name, group=group)

        is_member = self.show_application_site(application_name_to_unblock)
        if not is_member:
            raise CheckpointManagerError(
                f"Error. Cannot find {application_name_to_unblock} application site."
            )

        json_payload = {
            "name": application_group_name,
            "members": {"remove": application_name_to_unblock},
        }
        response = self._api_call(
            command="set-application-site-group", json_payload=json_payload
        )
        validate_response(response)

        self.publish_changes()
        return True

    def run_script(self, command, targets, script_name="Siemplify-generated-script"):
        """
        Run a script (command)
        :param command: {str} The command to run
        :param targets: {list} The targets of the script (to run it on them)
        :param script_name: {str} The name of the script to run
        :return:
        """
        json_payload = {
            "script-name": script_name,
            "script": command,
            "targets": targets,
        }
        response = self._api_call(command="run-script", json_payload=json_payload)
        validate_response(response)
        task_ids = response.json()

        if not task_ids.get("tasks"):
            raise CheckpointManagerError("No task ID was returned.")

        return task_ids.get("tasks")[0].get("task-id")

    def get_task_details(self, task_id):
        """
        Get task full details
        :param task_id: {str} The task ID
        :return: {dict} The task full details
        """
        response = self._api_call(
            command="show-task",
            json_payload={"task-id": task_id, "details-level": "full"},
        )
        validate_response(response)

        return response.json()

    def get_task_status(self, task_id):
        """
        Using the show-task command to check the progress of the task.
        :param task_id: {str} Task id
        :return: {bool} Get task status
        """
        tasks = self.get_task_details(task_id=task_id)

        if tasks.get("tasks", []):
            return tasks["tasks"][0].get("status")

        raise CheckpointManagerError(f"Task {task_id} was not found")

    def is_task_completed(self, task_id):
        """
        Check whether the task has completed
        :param task_id: {str} The task ID
        :return: {bool} True if completed, False otherwise.
        """
        task_status = self.get_task_status(task_id)
        return task_status != TASK_PROGRESS_STATUS

    def is_task_failed(self, task_id):
        """
        Check whether the task has failed
        :param task_id: {str} The task ID
        :return: {bool} True if failed, False otherwise.
        """
        task_status = self.get_task_status(task_id)
        return task_status == TASK_FAILED_STATUS

    def is_task_succeeded(self, task_id):
        """
        Check whether the task has succeeded
        :param task_id: {str} The task ID
        :return: {bool} True if succeeded, False otherwise.
        """
        task_status = self.get_task_status(task_id)
        return task_status == TASK_SUCCESS_STATUS

    def is_task_partially_succeeded(self, task_id):
        """
        Check whether the task has partially succeeded
        :param task_id: {str} The task ID
        :return: {bool} True if partially succeeded, False otherwise.
        """
        task_status = self.get_task_status(task_id)
        return task_status == TASK_PARTIAL_SUCCESS_STATUS

    def is_task_succeeded_with_warnings(self, task_id):
        """
        Check whether the task has succeeded with warnings
        :param task_id: {str} The task ID
        :return: {bool} True if succeeded with warnings, False otherwise.
        """
        task_status = self.get_task_status(task_id)
        return task_status == TASK_SUCCESS_WITH_WARNINGS_STATUS

    def get_task_response_errors(self, task_id):
        """
        Get a task's response errors from the task details
        :param task_id: {str} The task ID
        :return: {list} List of the response errors
        """
        tasks = self.get_task_details(task_id=task_id)

        if tasks.get("tasks", []):
            task_details = tasks["tasks"][0].get("task-details", [])

            errors = []

            for detail in task_details:
                if detail.get("responseError"):
                    errors.append(base64.b64decode(detail["responseError"]))

            return errors

        raise CheckpointManagerError(f"Task {task_id} was not found")

    def get_task_response_messages(self, task_id):
        """
        Get a task's response messages from the task details
        :param task_id: {str} The task ID
        :return: {list} List of the response messages
        """
        tasks = self.get_task_details(task_id=task_id)

        if tasks.get("tasks", []):
            task_details = tasks["tasks"][0].get("task-details", [])

            errors = []

            for detail in task_details:
                if detail.get("responseMessage"):
                    errors.append(base64.b64decode(detail["responseMessage"]))

            return errors

        raise CheckpointManagerError(f"Task {task_id} was not found")

    def get_logs(self, query_filter, time_frame, log_type, max_logs_limit):
        """
        Get logs for given parameters
        :param query_filter: {str} filter query.
        :param time_frame: {str} time duration by const TIME_FRAME_MAPPING.
        :param log_type: {str} log type by const LOG_MAPPING.
        :param max_logs_limit: {str} max logs per request.
        :return: {dict} list of LogResult model
        """
        json_payload = {
            "new-query": {
                "time-frame": time_frame,
                "max-logs-per-request": max_logs_limit,
                "type": log_type,
                "filter": query_filter,
            }
        }
        response = self._api_call("show-logs", json_payload=json_payload)
        validate_response(response)

        return self.parser.get_logs(response.json())

    def get_task_process_data(self, log_id):
        """
        Create task for log_id
        :param log_id: {str} The Log Id
        :return: {dict} Created Task details.
        """
        response = self._api_call("get-attachment", {"id": log_id})
        validate_response(response)

        return self.parser.get_task(response.json(), log_id)

    def get_task_details_parsed(self, task_id, folder_path, log_id):
        """
        Get Task task details for given log already parsed
        :param task_id: {str} The Task Id
        :param log_id: {str} The Log Id
        :return: {list} Completed Task details parsed.
        """
        raw_data = self.get_task_details(task_id)
        # Add absolute path for each task
        for item in raw_data.get("tasks"):
            item.update({"absolute_path": folder_path})

        return self.parser.get_task(raw_data, log_id=log_id)

    @staticmethod
    def construct_criteria(
        src_ip=None,
        src_netmask=None,
        dst_ip=None,
        dst_netmask=None,
        port=None,
        protocol=None,
    ):
        """
        Construct a criteria for SAM rule addition command, as described in
        https://sc1.checkpoint.com/documents/R80.40/WebAdminGuides/EN/CP_R80.40_CLI_ReferenceGuide/Content/Topics-CLIG/MDSG/fw-sam.htm
        :param src_ip: {str}
        :param src_netmask: {str}
        :param dst_ip: {str}
        :param dst_netmask: {str}
        :param port: {int}
        :param protocol: {str}
        :return: {str} The criteria
        """
        if (
            src_ip
            and not src_netmask
            and not dst_ip
            and not dst_netmask
            and not port
            and not protocol
        ):
            return f"src {src_ip}"

        elif (
            src_ip
            and src_netmask
            and not dst_ip
            and not dst_netmask
            and not port
            and not protocol
        ):
            return f"subsrc {src_ip} {src_netmask}"

        elif (
            dst_ip
            and not src_ip
            and not src_netmask
            and not dst_netmask
            and not port
            and not protocol
        ):
            return f"dst {dst_ip}"

        elif (
            dst_ip
            and dst_netmask
            and not src_ip
            and not src_netmask
            and not port
            and not protocol
        ):
            return f"subdst {dst_ip} {dst_netmask}"

        elif (
            src_ip
            and dst_ip
            and port
            and protocol
            and not src_netmask
            and not dst_netmask
        ):
            return f"srv {src_ip} {dst_ip} {port} {protocol}"

        elif src_ip and src_netmask and dst_ip and dst_netmask and port and protocol:
            return f"subsrv {src_ip} {src_netmask} {dst_ip} {dst_netmask} {port} {protocol}"

        elif (
            src_ip and src_netmask and dst_ip and port and protocol and not dst_netmask
        ):
            return f"subsrvs {src_ip} {src_netmask} {dst_ip} {port} {protocol}"

        elif (
            src_ip and dst_ip and dst_netmask and port and protocol and not src_netmask
        ):
            return f"subsrvd {src_ip} {dst_ip} {dst_netmask} {port} {protocol}"

        elif (
            dst_ip
            and port
            and protocol
            and not src_ip
            and not src_netmask
            and not dst_netmask
        ):
            return f"dstsrv {dst_ip} {port} {protocol}"

        elif (
            dst_ip
            and dst_netmask
            and port
            and protocol
            and not src_ip
            and not src_netmask
        ):
            return f"subdstsrv {dst_ip} {dst_netmask} {port} {protocol}"

        elif (
            src_ip
            and protocol
            and not src_netmask
            and not dst_ip
            and not dst_netmask
            and not port
        ):
            return f"srcpr {src_ip} {protocol}"

        elif (
            dst_ip
            and protocol
            and not src_ip
            and not src_netmask
            and not dst_netmask
            and not port
        ):
            return f"dstpr {dst_ip} {protocol}"

        elif (
            src_ip
            and src_netmask
            and protocol
            and not dst_ip
            and not dst_netmask
            and not port
        ):
            return f"subsrcpr {src_ip} {src_netmask} {protocol}"

        elif (
            dst_ip
            and dst_netmask
            and protocol
            and not src_ip
            and not src_netmask
            and not port
        ):
            return f"subdstpr {dst_ip} {dst_netmask} {protocol}"

        else:
            raise CheckpointManagerError(
                "Given parameters do not match any valid criteria combination."
            )

    @staticmethod
    def construct_add_sam_rule_command(
        criteria,
        action,
        track_matching_connections,
        close_connections=False,
        expiration=None,
    ):
        """
        Construct the add SAM rule command as described in
        https://sc1.checkpoint.com/documents/R80.40/WebAdminGuides/EN/CP_R80.40_CLI_ReferenceGuide/Content/Topics-CLIG/MDSG/fw-sam.htm
        :param criteria: {str} The criteria of the command
        :param action: {str} Notify / Drop / Reject
        :param track_matching_connections: {str} No Log / Log / Alert
        :param close_connections: {bool} Whether to close connections or not
        :param expiration: {int} Timeout for the rule
        :return: {str} The command
        """
        command = "fw sam"

        if expiration:
            command += f" -t {expiration}"

        if track_matching_connections == "No Log":
            command += " -l nolog"

        elif track_matching_connections == "Log":
            command += " -l long_noalert"

        elif track_matching_connections == "Alert":
            command += " -l long_alert"

        if action == "Notify":
            command += " -n"

        elif action == "Reject":
            if close_connections:
                command += " -I"

            else:
                command += " -i"

        elif action == "Drop":
            if close_connections:
                command += " -J"

            else:
                command += " -j"

        command += f" {criteria}"
        return command

    @staticmethod
    def construct_remove_sam_rule_command(
        criteria, action, track_matching_connections, close_connections=False
    ):
        """
        Construct the remove SAM rule command
        :param criteria: {str} The criteria of the command
        :param action: {str} Notify / Drop / Reject
        :param track_matching_connections: {str} No Log / Log / Alert
        :param close_connections: {bool} Whether to close connections or not
        :return: {str} The command
        """
        command = "fw sam"

        if track_matching_connections == "No Log":
            command += " -l nolog"

        elif track_matching_connections == "Log":
            command += " -l long_noalert"

        elif track_matching_connections == "Alert":
            command += " -l long_alert"

        command += " -C"

        if action == "Notify":
            command += " -n"

        elif action == "Reject":
            if close_connections:
                command += " -I"

            else:
                command += " -i"

        elif action == "Drop":
            if close_connections:
                command += " -J"

            else:
                command += " -j"

        command += f" {criteria}"
        return command
