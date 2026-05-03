# ==============================================================================
# title           :FortiManager.py
# description     :This Module contain all Elastic search functionality
# author          :victor@siemplify.co
# date            :3-9-18
# python_version  :2.7
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import copy

# =====================================
#            Json payloads            #
# =====================================
PAYLOAD = {
    "method": None,
    "params": [{"url": None, "data": None, "option": None}],
    "id": None,
    "verbose": None,
    "jsonrpc": "2.0",
    "session": None,
}

LOGIN_DATA = {"user": None, "paswwd": None}
ADDRESS_OBJ_DATA = {
    "name": "",
    "start-ip": "",
    "end-ip": "",
    "type": 1,  # Type 1 means Range Of Addresses.
}

URL_ENTRY_DATA = {"url": "www.test.com", "action": 1, "type": 0, "status": 1}


EXCECUTE_SCRIPT_DATA = {
    "adom": "",  # ADOM Name
    "package": "",  # The full path to the package, including package name and any parent folders
    "scope": {"name": "", "vdom": ""},
    "script": "",  # Script Name
}

# =====================================
#             CONSTANTS               #
# =====================================
# URLs.
LOGIN_URL = "/sys/login/user"
LOGOUT_URL = "/sys/logout/"
ADDRESS_GROUPS_OBJ_URL = "/pm/config/adom/{0}/obj/firewall/addrgrp"  # {0} - ADOM Name
SPECIFIC_ADDRESS_GROUPS_OBJ_URL = "/pm/config/adom/{0}/obj/firewall/addrgrp/{1}"  # {0} - ADOM Name, {1} - Address Group Name
GET_ADOMS_URL = "/dvmdb/adom"
LOCK_ADOM_URL = "/dvmdb/adom/{0}/workspace/lock"
UNLOCK_ADOM_URL = "/dvmdb/adom/{0}/workspace/unlock"
START_WORKFLOW_SESSION_URL = "/dvmdb/adom/{0}/workflow/start"
SUBMIT_WORKFLOW_SESSION_URL = "/dvmdb/adom/{0}/workflow/submit/{1}"
APPROVE_WORKFLOW_SESSION_URL = "/dvmdb/adom/{0}/workflow/approve/{1}"
COMMIT_ADOM_CHANGES_URL = "/dvmdb/adom/{0}/workspace/commit"
ADDRESS_OBJ_URL = "/pm/config/adom/{0}/obj/firewall/address"  # {0} - ADOM Name
SPECIFIC_ADDRESS_OBJ_URL = "/pm/config/adom/{0}/obj/firewall/address/{1}"  # {0} - ADOM Name, {1} - Address Object Name
URLFILTER_OBJECT_URL = "/pm/config/adom/{0}/obj/webfilter/urlfilter"  # {0} - ADOM Name
SPECIFIC_URLFILTER_OBJECT_URL = "/pm/config/adom/{0}/obj/webfilter/urlfilter/{1}"  # {0} - ADOM Name, {1} - URL Filter Name
SPECIFIC_URLFILTER_OBJECT_ENTRIES_URL = "/pm/config/adom/{0}/obj/webfilter/urlfilter/{1}/entries"  # {0} - ADOM Name, {1} - URL Filter Name
SPECIFIC_ENTRY_URL = "/pm/config/adom/{0}/obj/webfilter/urlfilter/{1}/entries/{2}"  # {0} - ADOM Name, {1} - URL Filter Name, {2} - Entry ID.
SCRIPT_OBJECT_URL = "/dvmdb/adom/{0}/script"  # {0} - ADOM Name
SCRIPT_EXCECUTE_URL = "/dvmdb/adom/{0}/script/execute"  # {0} - ADOM Name
GET_TASK_OBJECT_URL = "/task/task/{0}"  # {0} - Task ID

ADDRESS_OBJ_NAME_PATTERN = "Siemplify_{0}"  # {0} - IP Address


# =====================================
#              CLASSES                #
# =====================================
class MethodTypes:
    EXEC = "exec"
    GET = "get"
    ADD = "add"
    SET = "set"
    DELETE = "delete"
    UPDATE = "update"


class FortiManagerError(Exception):
    def __init__(self, *args, **kwargs):
        self.code = kwargs.get("code", 0)
        super(Exception, self).__init__(*args)


class WorkflowError(FortiManagerError):
    pass


class FortiManager:
    def __init__(
        self,
        api_root,
        username,
        password,
        verify_ssl=False,
        workflow_mode=False,
        siemplify=None,
    ):
        """
        :param api_root: {string} FortiManager API root https://{}:{}/jsonrpc
        :param username: {string} FortiManager Username
        :param password: {string} FortiManager Password
        :param verify_ssl: {bool} Verify SSL
        :param workflow_mode: {bool} If enabled, integration will use workflow sessions to execute API requests
        """
        self.siemplify = siemplify
        self.api_root = self.adjust_api_root(api_root)
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.token = self.obtain_token(username, password)
        self.workflow_mode = workflow_mode
        self.workflow_session = None

    def log_info(self, message):
        if self.siemplify:
            self.siemplify.LOGGER.info(message)

    @staticmethod
    def adjust_api_root(api_root):
        api_root = api_root.strip()
        return api_root if not api_root.endswith("/") else api_root[:-1]

    @staticmethod
    def remove_url_prefix(url):
        """
        Remove 'http' and 'https' from url
        :param url: {string} url to fetch
        :return: {string} url
        """
        splited_url = url.split("//")
        if len(splited_url) > 1:
            return splited_url[1]
        return url

    @staticmethod
    def construct_address_object_name(ip_address):
        """
        Construct a Siemplify address object name
        :param ip_address: {string} ip address
        :return: {string} address object name
        """
        return ADDRESS_OBJ_NAME_PATTERN.format(ip_address)

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()
            if response.json().get("result"):
                status = response.json().get("result")[0].get("status")
                if status.get("code") != 0:
                    raise FortiManagerError(
                        f'Error accrued, Status Code: {status.get("code")}, Error: {status.get("message")}',
                        code=status.get("code"),
                    )

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise FortiManagerError(
                    f"{error_msg}: {error} - {error.response.content}"
                )

            raise FortiManagerError(
                f"{error_msg}: {response.json().get('name')} {response.json().get('message')}"
            )

    def generate_payload(
        self,
        method,
        url,
        option=None,
        data=None,
        request_id=1,
        verbose=False,
        session=1,
    ):
        """
        :param self:
        :param method:
        :param url: Internal URL
        :param option:
        :param data: Data of the request
        :param request_id:
        :param verbose:
        :return:
        """
        payload = copy.deepcopy(PAYLOAD)
        payload["method"] = method
        payload["id"] = request_id
        payload["session"] = session
        payload["verbose"] = verbose
        payload["params"][0]["url"] = url
        payload["params"][0]["data"] = data
        payload["params"][0]["option"] = option

        return payload

    def obtain_token(self, username, password):
        """
        Get connection
        :param username: {string}
        :param password: {string}
        :return:
        """
        login_data = LOGIN_DATA
        login_data["user"] = username
        login_data["passwd"] = password
        payload = self.generate_payload(MethodTypes.EXEC, LOGIN_URL, data=login_data)
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        if response.json().get("session"):
            return response.json().get("session")
        else:
            raise FortiManagerError("Error logging in.No token received.")

    def logout(self):
        payload = self.generate_payload(
            MethodTypes.EXEC, LOGOUT_URL, session=self.token
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return True

    def lock_adom(self, adom_name):
        """
        Lock adom.
        :param adom_name: {string} relevant adom name
        :return: {bool} whether the lock was successful
        """
        payload = self.generate_payload(
            method=MethodTypes.EXEC,
            url=LOCK_ADOM_URL.format(adom_name),
            session=self.token,
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return True

    def unlock_adom(self, adom_name):
        """
        Unlock adom.
        :param adom_name: {string} relevant adom name
        :return: {bool} whether the lock was successful
        """
        payload = self.generate_payload(
            method=MethodTypes.EXEC,
            url=UNLOCK_ADOM_URL.format(adom_name),
            session=self.token,
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return True

    def start_workflow_session(self, adom_name):
        """
        Start workflow session under specified adom.
        :param adom_name: {string} relevant adom name
        :return: {bool} whether the lock was successful
        """
        payload = self.generate_payload(
            method=MethodTypes.EXEC,
            url=START_WORKFLOW_SESSION_URL.format(adom_name),
            session=self.token,
        )
        payload["params"][0]["workflow"] = {
            "desc": "Chronicle SOAR API Changes",
            "name": "Chronicle SOAR API",
        }
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return response.json()["result"][0]["data"]["sessionid"]

    def submit_workflow_session(self, adom_name):
        """
        Submit workflow session under specified adom.
        :param adom_name: {string} relevant adom name
        :return: {bool} whether the lock was successful
        """
        payload = self.generate_payload(
            method=MethodTypes.EXEC,
            url=SUBMIT_WORKFLOW_SESSION_URL.format(adom_name, self.workflow_session),
            session=self.token,
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return True

    def approve_workflow_session(self, adom_name):
        """
        Approve workflow session under specified adom.
        :param adom_name: {string} relevant adom name
        :return: {bool} whether the lock was successful
        """
        payload = self.generate_payload(
            method=MethodTypes.EXEC,
            url=APPROVE_WORKFLOW_SESSION_URL.format(adom_name, self.workflow_session),
            session=self.token,
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return True

    def commit_adom_changes(self, adom_name):
        """
        Commit changes to adom.
        :param adom_name {string} relevant adom name
        :return: {bool} whether the lock was successful
        """
        payload = self.generate_payload(
            method=MethodTypes.EXEC,
            url=COMMIT_ADOM_CHANGES_URL.format(adom_name),
            session=self.token,
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return True

    def check_session(self, adom_name):
        if self.workflow_mode and self.workflow_session is None:
            try:
                self.lock_adom(adom_name)
                session_id = self.start_workflow_session(adom_name)
                self.workflow_session = session_id
            except FortiManagerError as err:
                if err.code != -20055:
                    self.unlock_adom(adom_name)
                raise WorkflowError(err, code=err.code)

        return True

    def finish_session(self, adom_name):
        if not self.workflow_mode:
            return

        try:
            if not self.workflow_session:
                return
            self.submit_workflow_session(adom_name)
            self.commit_adom_changes(adom_name)
            self.approve_workflow_session(adom_name)
        except FortiManagerError as err:
            raise WorkflowError(err, code=err.code)
        finally:
            self.unlock_adom(adom_name)

    def create_address_object(self, adom_name, ip_address):
        """
        Create a firewall address object.
        :param adom_name: {string} relevant adom name
        :param ip_address: {string} ip address to block
        :return: {string} address object name
        """
        address_object_name = ADDRESS_OBJ_NAME_PATTERN.format(ip_address)
        data = copy.deepcopy(ADDRESS_OBJ_DATA)
        data["start-ip"] = data["end-ip"] = ip_address
        data["name"] = address_object_name
        payload = self.generate_payload(
            MethodTypes.ADD,
            ADDRESS_OBJ_URL.format(adom_name),
            session=self.token,
            data=data,
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return address_object_name

    def get_adoms(self):
        payload = self.generate_payload(
            MethodTypes.GET, GET_ADOMS_URL, session=self.token
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return response.json()

    def get_firewall_addresses_for_adom(self, adom_name):
        """
        Get all address objects for adom
        :param adom_name: {string} relevant adom name
        :return: {list} list of address objects
        """
        payload = self.generate_payload(
            MethodTypes.GET, ADDRESS_OBJ_URL.format(adom_name), session=self.token
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return response.json().get("result")[0].get("data")

    def is_address_object_exist(self, adom_name, address_obj_name):
        """
        Check if address object already exists.
        :param adom_name: {string} relevant adom name
        :param address_obj_name: {string} address object name
        :return: {bool} is exists
        """
        address_objects = self.get_firewall_addresses_for_adom(adom_name)
        for address in address_objects:
            if address.get("name") == address_obj_name:
                return True
        return False

    def get_address_group_by_name(self, adom_name, address_group_name):
        """
        Get address group name.
        :param adom_name: {string} relevant adom name
        :param address_group_name: {string} address group name
        :return: {dict} address group object
        """
        payload = self.generate_payload(
            MethodTypes.GET,
            SPECIFIC_ADDRESS_GROUPS_OBJ_URL.format(adom_name, address_group_name),
            session=self.token,
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return response.json().get("result")[0].get("data")

    def add_address_object_to_address_group(
        self, adom_name, address_group_name, address_object_name
    ):
        """
        Add address object to address group.
        :param adom_name: {string}
        :param address_group_name: {string}
        :param address_object_name: {string}
        :return: {bool} is success
        """
        address_group_object = self.get_address_group_by_name(
            adom_name, address_group_name
        )
        members = address_group_object["member"]
        if address_object_name not in members:
            members.append(address_object_name)
        payload = self.generate_payload(
            MethodTypes.UPDATE,
            SPECIFIC_ADDRESS_GROUPS_OBJ_URL.format(adom_name, address_group_name),
            data={"member": members},
            session=self.token,
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return True

    def remove_address_object_from_address_group(
        self, adom_name, address_group_name, address_object_name
    ):
        """
        Add address object to address group.
        :param adom_name: {string}
        :param address_group_name: {string}
        :param address_object_name: {string}
        :return: {bool} is success
        """
        address_group_object = self.get_address_group_by_name(
            adom_name, address_group_name
        )
        members = address_group_object["member"]
        if address_object_name in members:
            # Address group must contain at least one address object.
            if len(members) > 1:
                members.remove(address_object_name)
            else:
                raise FortiManagerError(
                    f'Error accrued, Error: Group cannot be empty. Group - "{address_group_name}"'
                )
        payload = self.generate_payload(
            MethodTypes.UPDATE,
            SPECIFIC_ADDRESS_GROUPS_OBJ_URL.format(adom_name, address_group_name),
            data={"member": members},
            session=self.token,
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return True

    def delete_address_object(self, adom_name, address_object_name):
        """
        Delete an address object by its name
        :param adom_name:
        :param address_object_name:
        :return:
        """
        payload = self.generate_payload(
            MethodTypes.DELETE,
            SPECIFIC_ADDRESS_OBJ_URL.format(adom_name, address_object_name),
            session=self.token,
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return True

    def get_urlfilters_for_admom(self, adom_name):
        """
        Get urlfilters for adom.
        :param adom_name: {string} relevant adom name.
        :return: {list} list of urlfilters
        """
        payload = self.generate_payload(
            MethodTypes.GET, URLFILTER_OBJECT_URL.format(adom_name), session=self.token
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return response.json().get("result")[0].get("data")

    def get_urlfilter_id_by_name(self, adom_name, urlfilter_name):
        """
        Get urlfilter id by name.
        :param adom_name: {string} relevant adom name
        :param urlfilter_name: {string} urlfilter name
        :return: {string} urlfilter id
        """
        urlfilter_objects = self.get_urlfilters_for_admom(adom_name)
        for urlfilter_object in urlfilter_objects:
            if urlfilter_object.get("name") == urlfilter_name:
                return urlfilter_object.get("id")
        raise FortiManagerError(
            f'Error occurred, Error: No urlfilter with name "{urlfilter_name}" was found on ADOM "{adom_name}"'
        )

    def get_urlfilter_object_by_id(self, adom_name, urlfilter_id):
        """
        Get
        :param adom_name: {string}
        :param urlfilter_id: {string}
        :return: {dict} urlfilter object
        """
        payload = self.generate_payload(
            MethodTypes.GET,
            SPECIFIC_URLFILTER_OBJECT_URL.format(adom_name, urlfilter_id),
            session=self.token,
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return response.json().get("result")[0].get("data")

    def get_entries_for_urlfilter_by_id(self, adom_name, urlfilter_id):
        """
        :param adom_name: {string}
        :param urlfilter_id: {string}
        :return:
        """
        payload = self.generate_payload(
            MethodTypes.GET,
            SPECIFIC_URLFILTER_OBJECT_ENTRIES_URL.format(adom_name, urlfilter_id),
            session=self.token,
        )
        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)
        return response.json().get("result")[0].get("data")

    def add_block_url_record_to_urlfilter_by_id(self, adom_name, urlfilter_id, url):
        """
        Add block url record to urlfilter by it's id
        :param adom_name: {string} relevant adom name
        :param urlfilter_id: {string}  urlfilter id that will contain the block record
        :return: {bool} is success
        """
        url_entry = copy.deepcopy(URL_ENTRY_DATA)
        url_entry["url"] = url
        payload = self.generate_payload(
            MethodTypes.ADD,
            SPECIFIC_URLFILTER_OBJECT_ENTRIES_URL.format(adom_name, urlfilter_id),
            session=self.token,
            data=url_entry,
        )

        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)

        return True

    def delete_block_url_record_from_urlfilter_by_id(
        self, adom_name, urlfilter_id, url
    ):
        """
        Delete block url record from urlfilter by it's id
        :param adom_name: {string} relevant adom name
        :param urlfilter_id: {string}  urlfilter id that will contain the block record
        :return: {bool} is success
        """
        urlfilter_entries = self.get_entries_for_urlfilter_by_id(
            adom_name, urlfilter_id
        )
        for entry in urlfilter_entries:
            if entry.get("url") == url:
                payload = self.generate_payload(
                    MethodTypes.DELETE,
                    SPECIFIC_ENTRY_URL.format(adom_name, urlfilter_id, entry.get("id")),
                    session=self.token,
                    data=entry,
                )
                response = self.session.post(self.api_root, json=payload)
                self.validate_response(response)

        return True

    def get_scripts(self, adom_name):
        """
        Get all scripts for adom.
        :param adom_name: {string} relevant adom name
        :return: {list} list of script objects.
        """
        payload = self.generate_payload(
            MethodTypes.GET, SCRIPT_OBJECT_URL.format(adom_name), session=self.token
        )

        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)

        return response.json().get("result")[0].get("data")

    def execute_script(
        self, adom_name, policy_package_name, script_name, device_name, vdom=None
    ):
        """
        Execute script on a device or a device group.
        :param adom_name: {string} relevant adom name
        :param policy_package_name: {string}  The full path to the package, including package name and any parent folders
        :param script_name: {string} script name  to execute.
        :param device_name: {string} can be a single device or a device group name.
        :param vdom: {string} VDOM
        :return: {string} task id
        """
        data = copy.deepcopy(EXCECUTE_SCRIPT_DATA)
        data["adom"] = adom_name
        data["package"] = policy_package_name
        data["scope"]["name"] = device_name
        if vdom:  # Only if running on single device.
            data["scope"]["name"] = device_name
        else:  # Else remove from data.
            data["scope"].pop("vdom")
        data["script"] = script_name
        payload = self.generate_payload(
            MethodTypes.EXEC,
            url=SCRIPT_EXCECUTE_URL.format(adom_name),
            data=data,
            session=self.token,
        )
        response = self.session.post(self.api_root, json=payload)

        self.validate_response(response)

        return response.json().get("result")[0].get("data").get("task")

    def get_task(self, task_id):
        """
        Get task by id.
        :param task_id: {string} relevant task id
        :return: {dict} task object
        """
        payload = self.generate_payload(
            MethodTypes.GET, GET_TASK_OBJECT_URL.format(task_id), session=self.token
        )

        response = self.session.post(self.api_root, json=payload)
        self.validate_response(response)

        return response.json().get("result")[0].get("data")
