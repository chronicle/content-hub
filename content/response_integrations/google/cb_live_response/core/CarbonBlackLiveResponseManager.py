from __future__ import annotations
import requests
import time
from typing import Optional, List
from urllib.parse import urljoin
from .exceptions import (
    CBLiveResponseException,
    CBLiveResponseUnauthorizedError,
    CBLiveResponseTimeoutException,
)
from . import datamodels
from .constants import DEFAULT_PAGE_SIZE, SLEEP_TIME, SHORT_PROVIDER_NAME
from .CBLiveResponseParser import CBLiveResponseParser

SENSOR_ID_NOT_FOUND_ERROR_MESSAGE = "Unable to find: sensorId"
NOT_FOUND_STATUS_CODE = 404
LIST_FILE_DEFAULT = "directory list"
PROCESSES_DEFAULT = "process list"
GET_FILE_DEFAULT = "get file"
MEMDUMP_DEFAULT = "memdump"
EXECUTE_FILE_DEFAULT = "create process"

API_ENDPOINTS = {
    # Endpoints for cb_cloud_session
    "appservice_search": "appservices/v6/orgs/{org_key}/alerts/_search",
    "devices_search": "appservices/v6/orgs/{org_key}/devices/_search",
    # Endpoints for lr_session
    "service_session": "integrationServices/v3/cblr/session/123132131232",
    "sessions": "integrationServices/v3/cblr/session/{device_id}",
    "get_session": "integrationServices/v3/cblr/session/{session_id}",
    "create_command": "integrationServices/v3/cblr/session/{session_id}/command",
    "get_command": "integrationServices/v3/cblr/session/{session_id}/command/{command_id}",
    "upload_file": "/integrationServices/v3/cblr/session/{session_id}/file",
    "init_command": "/integrationServices/v3/cblr/session/{session_id}/command",
    "get_file": "integrationServices/v3/cblr/session/{session_id}/file/{file_id}/content",
    "storage_files_list": "integrationServices/v3/cblr/session/{session_id}/file",
}


class CarbonBlackLiveResponseManager:
    """
    CB Live Response Manager
    """

    def __init__(
        self,
        api_root,
        org_key,
        cb_cloud_api_id,
        cb_cloud_api_secret_key,
        lr_api_id,
        lr_api_secret_key,
        verify_ssl=False,
        force_check_connectivity=False,
    ):
        self.api_root = api_root
        self.cb_cloud_session = requests.session()
        self.cb_cloud_session.headers["X-Auth-Token"] = (
            f"{cb_cloud_api_secret_key}/{cb_cloud_api_id}"
        )
        self.cb_cloud_session.verify = verify_ssl

        self.lr_session = requests.session()
        self.lr_session.headers["X-Auth-Token"] = f"{lr_api_secret_key}/{lr_api_id}"
        self.lr_session.verify = verify_ssl
        self.org_key = org_key
        self.parser = CBLiveResponseParser()
        self.api_endpoints = API_ENDPOINTS

        if force_check_connectivity:
            self.test_connectivity()

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier
        :param url_id: {str} the id of url
        :param kwargs: {dict} variables passed for string formatting
        :return: {str} the full url
        """
        if "org_key" not in kwargs:
            kwargs["org_key"] = self.org_key

        return urljoin(self.api_root, self.api_endpoints[url_id].format(**kwargs))

    @staticmethod
    def _get_adjusted_root_url(api_root):
        return api_root[:-1] if api_root.endswith("/") else api_root

    def test_connectivity(self):
        """
        Test connectivity to Cb Live Response with given creds
        :return: {bool} True if successful, exception otherwise
        """
        # First test connectivity to Device API to check creds + org key
        json_payload = {"rows": 3, "start": 0}
        response = self.cb_cloud_session.post(
            self._get_full_url("appservice_search"), json=json_payload
        )
        self.validate_response(
            response,
            f"Unable to connect to {SHORT_PROVIDER_NAME}.Please validate your CB Cloud credentials.",
        )

        response = self.lr_session.post(self._get_full_url("service_session"))
        # Second test connectivity to LR service specifically
        # Defined by product - running a request to create a session with the wrong device id (hostname id) that will
        # return a 404 error if integration configuration is correct with specific error text.
        if self.is_sensor_id_not_found(response):
            return True

        self.validate_response(
            response,
            f"Unable to connect to {SHORT_PROVIDER_NAME}. Please validate your Live Response credentials.",
        )

    def is_sensor_id_not_found(self, response):
        return (
            response.status_code == NOT_FOUND_STATUS_CODE
            and self.parser.get_reason(response.json())
            == SENSOR_ID_NOT_FOUND_ERROR_MESSAGE
        )

    def get_devices(
        self,
        query: Optional[str] = None,
        sort_by: str = "last_contact_time",
        sort_order: str = "DESC",
        limit: Optional[int] = None,
    ) -> List[datamodels.Device]:
        """
        Get an device by query
        :param query: {str} The query to use for
        :param sort_order: {str} Field to order results by
        :param sort_by: {str} Order of the sort (ASC / DESC)
        :param limit: {int} Max amount of devices to return
        :return: {[Device]} The matching devices
        """
        devices = self._paginate_results(
            self.cb_cloud_session,
            "POST",
            self._get_full_url("devices_search"),
            err_msg="Unable to get devices",
            limit=limit,
            body={"query": query, "sort": [{"field": sort_by, "order": sort_order}]},
        )

        return self.parser.build_results(
            devices, "build_siemplify_device_obj", pure_data=True
        )

    def start_session(self, device_id):
        """
        Start an LR session in a sensor by its ID
        :param device_id: {str} The ID of the sensor (device) to start the LR with
        :return: {LRSession} The created LRSession
        """
        payload = {"sensor_id": device_id}
        response = self.lr_session.post(
            self._get_full_url("sessions", device_id=device_id), json=payload
        )
        self.validate_response(
            response, f"Unable to establish session with device {device_id}"
        )

        return self.parser.build_siemplify_lr_session_obj(response.json())

    def get_session(self, session_id):
        """
        Get a Live Response session info
        :param session_id: {str} The ID of the LR session
        :return: {LRSession} The session object
        """
        response = self.lr_session.get(
            self._get_full_url("get_session", session_id=session_id)
        )
        self.validate_response(response, f"Unable to get session {session_id}")

        return self.parser.build_siemplify_lr_session_obj(response.json())

    def upload_file(self, session_id, file_path):
        """
        Upload file to server
        :param session_id: {str} The ID of the LR session
        :param file_path: {str} Source file path to get the file to upload
        :return: {UploadFile} UploadFile object
        """
        files = {"file": open(file_path, "rb")}
        response = self.lr_session.post(
            self._get_full_url("upload_file", session_id=session_id), files=files
        )
        self.validate_response(
            response, f"Unable to upload file in session {session_id}"
        )

        return self.parser.build_siemplify_upload_file_obj(response.json())

    def wait_for_session(
        self, session_id: str, retries: int = 10
    ) -> datamodels.LRSession:
        """
        Wait for a LR session to become active
        :param session_id: {str} The ID of the LR session
        :param retries: {int} Max number of retries before we consider the session as timed out
        :return: {datamodels.LRSession} The session object
        """
        session = self.get_session(session_id)
        count = 1

        while session.is_pending:
            if count > retries:
                raise CBLiveResponseTimeoutException(
                    f"Timeout while waiting for session {session_id} to become active."
                )

            count += 1
            time.sleep(SLEEP_TIME)
            session = self.get_session(session_id)

        if session.is_closed:
            raise CBLiveResponseException(f"Session {session_id} has closed.")

        return session

    def get_list_processes_command_by_id(
        self, session_id: str, command_id: str
    ) -> datamodels.ListProcessesCommand:
        """
        Get a list processes command object
        :param session_id: {str} The ID of the LR session
        :param command_id: {str} The ID of the command
        :return: {datamodels.ListProcessesCommand} The command object
        """
        command = self.get_command_by_id(session_id, command_id)
        return self.parser.build_siemplify_list_processes_command_obj(command.raw_data)

    def get_memdump_command_by_id(self, session_id, command_id):
        """
        Get a command by id and session id
        :param session_id: {str} The ID of the LR session
        :param command_id: {str} The ID of the command
        :return: {Command} The command object
        """
        command = self.get_command_by_id(session_id, command_id)

        return self.parser.build_siemplify_memdump_command_obj(command.raw_data)

    def get_command_by_id(self, session_id, command_id, start_from=0, limit=None):
        """
        Get a command by id and session id
        :param session_id: {str} The ID of the LR session
        :param command_id: {str} The ID of the command
        :param start_from: {str} Start from getting
        :param limit: {str} Limit results
        :return: {Command} The command object
        """
        response = self.lr_session.get(
            self._get_full_url(
                "get_command", session_id=session_id, command_id=command_id
            )
        )
        self.validate_response(
            response, f"Unable to get command {command_id} for session {session_id}"
        )

        return self.parser.build_siemplify_command_obj(
            response.json(), start_from=start_from, limit=limit
        )

    def get_process_command_by_id(
        self, session_id, command_id, process_name=None, limit=None
    ):
        """
        Get a command by id and session id
        :param session_id: {str} The ID of the LR session
        :param command_id: {str} The ID of the command
        :param process_name: {str} Process name for filter processes
        :param limit: {str} Process name for filter processes
        :return: {Command} The command object
        """
        response = self.lr_session.get(
            self._get_full_url(
                "get_command", session_id=session_id, command_id=command_id
            )
        )
        self.validate_response(
            response, f"Unable to get command {command_id} for session {session_id}"
        )

        return self.parser.build_siemplify_process_command_obj(
            response.json(), process_name=process_name, limit=limit
        )

    def get_kill_process_command_by_id(self, session_id, command_id):
        """
        Get a kill process command object
        :param session_id: {str} The ID of the LR session
        :param command_id: {str} The ID of the command
        :return: {KillProcessCommand} The command object
        """
        command = self.get_command_by_id(session_id, command_id)
        return self.parser.build_siemplify_kill_process_command_obj(command.raw_data)

    def start_command_for_process_list(self, session_id):
        """
        Initiate a list processes command in a given session (ps command)
        :param session_id: {str} The ID of the LR session
        :return: {ListProcessesCommand} The command object
        """
        payload = {"name": PROCESSES_DEFAULT, "session_id": session_id}
        response = self.lr_session.post(
            self._get_full_url("create_command", session_id=session_id), json=payload
        )
        self.validate_response(
            response,
            f"Unable to initiate list processes command in session {session_id}",
        )

        return self.parser.build_siemplify_command_obj(response.json())

    def initiate_put_file_command(self, session_id, file_id, destination_file_path):
        """
        Initiate a put file command for a given session
        :param session_id: {str} The ID of the LR session
        :param destination_file_path: {str} Remote directory path to put file
        :param file_id: {str} The ID of the file to put
        :return: {Command} The command object
        """
        payload = {
            "name": "put file",
            "session_id": session_id,
            "object": destination_file_path,
            "file_id": file_id,
        }
        response = self.lr_session.post(
            self._get_full_url("init_command", session_id=session_id), json=payload
        )
        self.validate_response(
            response, f"Unable to initiate put file command in session {session_id}"
        )
        return self.parser.build_siemplify_command_obj(response.json())

    def start_command_for_list_files(self, session_id, directory_path):
        """
        Initiate a list files command for a given session
        :param session_id: {str} The ID of the LR session
        :param directory_path: {str} Remote directory path to get from
        :return: {ListProcessesCommand} The command object
        """
        payload = {
            "name": LIST_FILE_DEFAULT,
            "session_id": session_id,
            "object": directory_path,
        }
        response = self.lr_session.post(
            self._get_full_url("create_command", session_id=session_id), json=payload
        )
        self.validate_response(
            response, f"Unable to initiate list files command in session {session_id}"
        )

        return self.parser.build_siemplify_command_obj(response.json())

    def start_command_for_get_file(self, session_id, path):
        """
        Initiate a get file command for a given session
        :param session_id: {str} The ID of the LR session
        :param path: {str} Remote directory path to get file
        :return: {Command} The command object
        """
        payload = {"name": GET_FILE_DEFAULT, "session_id": session_id, "object": path}
        response = self.lr_session.post(
            self._get_full_url("create_command", session_id=session_id), json=payload
        )
        self.validate_response(
            response, f"Unable to initiate list files command in session {session_id}"
        )

        return self.parser.build_siemplify_command_obj(response.json())

    def start_command_to_create_memdump(self, session_id, path):
        """
        Initiate a memdump file
        :param session_id: {str} The ID of the LR session
        :param path: {str} Remote directory path to create memdump
        :return: {Command} The command object
        """
        payload = {"name": MEMDUMP_DEFAULT, "session_id": session_id, "object": path}
        response = self.lr_session.post(
            self._get_full_url("create_command", session_id=session_id), json=payload
        )
        self.validate_response(
            response,
            f"Unable to initiate create memdump command in session {session_id}",
        )

        return self.parser.build_siemplify_command_obj(response.json())

    def get_file_content(self, session_id, file_id):
        """
        Get file content
        :param session_id: {str} The ID of the LR session
        :param file_id: {str} File id
        :return: File content
        """
        response = self.lr_session.get(
            self._get_full_url("get_file", session_id=session_id, file_id=file_id)
        )
        response.raise_for_status()

        return response.content

    def start_command_for_delete_file(self, session_id, remote_file_path):
        """
        Initiate a list files command for a given session
        :param session_id: {str} The ID of the LR session
        :param remote_file_path: {str} Remote path to delete from
        :return: {ListProcessesCommand} The command object
        """
        payload = {
            "name": "delete file",
            "session_id": session_id,
            "object": remote_file_path,
        }
        response = self.lr_session.post(
            self._get_full_url("create_command", session_id=session_id), json=payload
        )
        self.validate_response(
            response, f"Unable to initiate delete file command in session {session_id}"
        )

        return self.parser.build_siemplify_command_obj(response.json())

    def start_command_to_execute_file(
        self, session_id, path, output_file, wait_for_result
    ):
        """
        Initiate a command for execute file
        :param session_id: {str} The ID of the LR session
        :param path: {str} Remote directory path
        :param output_file: {str} path for output
        :param wait_for_result: {str} should wait for result
        :return: {Command} The command object
        """
        payload = {
            "name": EXECUTE_FILE_DEFAULT,
            "session_id": session_id,
            "object": path,
            "output_file": output_file,
            "wait": wait_for_result,
        }
        response = self.lr_session.post(
            self._get_full_url("create_command", session_id=session_id), json=payload
        )
        self.validate_response(
            response, f"Unable to initiate execute file command in session {session_id}"
        )

        return self.parser.build_siemplify_command_obj(response.json())

    def get_command_for_execute_file(self, session_id, command_id):
        """
        Get execute file command object
        :param session_id: {str} The ID of the LR session
        :param command_id: {str} The ID of the command
        :return: {Command} The command object
        """
        command = self.get_command_by_id(session_id, command_id)

        return self.parser.build_siemplify_execute_file_command_obj(command.raw_data)

    def get_command_for_list_files(self, session_id, command_id):
        """
        Get a files list command object
        :param session_id: {str} The ID of the LR session
        :param command_id: {str} The ID of the command
        :return: {FilesCommand} The command object
        """
        command = self.get_command_by_id(session_id, command_id)

        return self.parser.build_siemplify_list_files_command_obj(command.raw_data)

    def get_storage_files_for_session(self, session_id, start_from=0, limit=None):
        """
        Get list of files by session id
        :param session_id: {str} The ID of the LR session
        :param start_from: {str} Start from getting
        :param limit: {str} Limit results
        :return: {list} List of files for session
        """
        response = self.lr_session.get(
            self._get_full_url("storage_files_list", session_id=session_id)
        )
        self.validate_response(
            response,
            f"Unable to initiate get files from storage for session {session_id}",
        )

        return self.parser.get_files_objects(response.json(), start_from, limit)

    def wait_for_command(self, session_id: str, command_id: str) -> datamodels.Command:
        """
        Wait for a command to complete
        :param session_id: {str} The ID of the LR session
        :param command_id: {str} The ID of the command
        :return: {datamodels.Command} The command object
        """
        command = self.get_command_by_id(session_id, command_id)

        while command.is_pending or command.is_in_progress:
            time.sleep(SLEEP_TIME)
            command = self.get_command_by_id(session_id, command_id)

        if command.is_canceled:
            raise CBLiveResponseException(
                f"Command {command_id} in session {session_id} was canceled."
            )

        if command.is_failed:
            raise CBLiveResponseException(
                f"Command {command_id} in session {session_id}  has failed."
            )

        if not command.is_completed:
            # Unknown status
            raise CBLiveResponseException(
                f"Command {command_id} in session {session_id} has completed with unexpected status: {command.status}."
            )

        # Command has completed
        return command

    def initiate_kill_process_command(self, session_id, pid):
        """
        Initiate a list processes command in a given session (ps command)
        :param session_id: {str} The ID of the LR session
        :param pid: {str} The PID of the process to kill
        :return: {ListProcessesCommand} The command object
        """
        payload = {"name": "kill", "session_id": session_id, "object": pid}
        response = self.lr_session.post(
            self._get_full_url("create_command", session_id=session_id), json=payload
        )
        self.validate_response(
            response, f"Unable to initiate kill process command in session {session_id}"
        )
        return self.parser.build_siemplify_kill_process_command_obj(response.json())

    def _paginate_results(
        self,
        session,
        method,
        url,
        params=None,
        body=None,
        limit=None,
        err_msg="Unable to get results",
    ):
        """
        Paginate the results of a job
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param limit: {int} The limit of the results to fetch
        :param err_msg: {str} The message to display on error
        :return: {list} List of results
        """
        if body is None:
            body = {}

        body.update(
            {
                "start": 1,
                "rows": min(DEFAULT_PAGE_SIZE, limit) if limit else DEFAULT_PAGE_SIZE,
            }
        )

        response = session.request(method, url, params=params, json=body)
        self.validate_response(response, err_msg)
        results = self.parser.get_results(response.json())

        while True:
            if limit and len(results) >= limit:
                break

            if not self.parser.get_results(response.json()):
                break

            body.update({"start": len(results) + 1})

            response = session.request(method, url, params=params, json=body)
            self.validate_response(response, err_msg)
            results.extend(self.parser.get_results(response.json()))

        return results[:limit] if limit else results

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {unicode} Default message to display on error
        """
        try:
            if response.status_code == 401:
                raise CBLiveResponseUnauthorizedError(
                    "Unauthorized. Please check given credentials."
                )

            response.raise_for_status()

        except requests.HTTPError as error:
            raise CBLiveResponseException(f"{error_msg}: {error} {response.text}")
