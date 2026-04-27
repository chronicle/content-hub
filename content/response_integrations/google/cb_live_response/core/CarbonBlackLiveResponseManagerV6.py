from __future__ import annotations
from .CarbonBlackLiveResponseManager import (
    CarbonBlackLiveResponseManager,
    LIST_FILE_DEFAULT,
    PROCESSES_DEFAULT,
    GET_FILE_DEFAULT,
    MEMDUMP_DEFAULT,
    EXECUTE_FILE_DEFAULT,
)
from .constants import SHORT_PROVIDER_NAME, API_VERSION_V6

API_ENDPOINTS = {
    "sessions": "appservices/v6/orgs/{org_key}/liveresponse/sessions",
    "init_command": "/appservices/v6/orgs/{org_key}/liveresponse/sessions/{session_id}/commands",
    "get_session": "appservices/v6/orgs/{org_key}/liveresponse/sessions/{session_id}",
    "create_command": "appservices/v6/orgs/{org_key}/liveresponse/sessions/{session_id}/commands",
    "get_command": "appservices/v6/orgs/{org_key}/liveresponse/sessions/{session_id}/commands/{command_id}",
    "upload_file": "/appservices/v6/orgs/{org_key}/liveresponse/sessions/{session_id}/files",
    "get_file": "appservices/v6/orgs/{org_key}/liveresponse/sessions/{session_id}/files/{file_id}/content",
    "storage_files_list": "appservices/v6/orgs/{org_key}/liveresponse/sessions/{session_id}/files",
    "delete_file": "/appservices/v6/orgs/{org_key}/liveresponse/sessions/{session_id}/files/{file_id}",
}


class CarbonBlackLiveResponseManagerV6(CarbonBlackLiveResponseManager):
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
        super(CarbonBlackLiveResponseManagerV6, self).__init__(
            api_root,
            org_key,
            cb_cloud_api_id,
            cb_cloud_api_secret_key,
            lr_api_id,
            lr_api_secret_key,
            verify_ssl,
            force_check_connectivity=False,
        )
        self.api_endpoints.update(API_ENDPOINTS)

        if force_check_connectivity:
            self.test_connectivity()

    def test_connectivity(self):
        """
        Test connectivity to Cb Live Response with given creds
        :return: {bool} True if successful, exception otherwise
        """
        response = self.cb_cloud_session.get(self._get_full_url("sessions"))
        self.validate_response(
            response,
            f"Unable to connect to {SHORT_PROVIDER_NAME}. Please validate your Live Response credentials.",
        )

        return True

    def start_session(self, device_id):
        """
        Start a Live Response session
        :param device_id: {str} The ID of the device on which session creating
        :return: {Session} The session object
        """
        payload = {"device_id": device_id}
        response = self.cb_cloud_session.post(
            self._get_full_url("sessions"), json=payload
        )
        self.validate_response(
            response, f"Unable to create a session for provided {device_id} device_id"
        )

        return self.parser.build_siemplify_session_obj(response.json())

    def get_session(self, session_id):
        """
        Get a Live Response session info
        :param session_id: {str} The ID of the Session
        :return: {Session} The session object
        """
        response = self.cb_cloud_session.get(
            self._get_full_url("get_session", session_id=session_id)
        )
        self.validate_response(response, f"Unable to get session {session_id}")

        return self.parser.build_siemplify_session_obj(response.json())

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
        response = self.cb_cloud_session.post(
            self._get_full_url("create_command", session_id=session_id), json=payload
        )
        self.validate_response(
            response, f"Unable to initiate list files command in session {session_id}"
        )

        return self.parser.build_siemplify_command_obj(
            response.json(), version=API_VERSION_V6
        )

    def start_command_for_process_list(self, session_id):
        """
        Initiate a list processes command in a given session (ps command)
        :param session_id: {str} The ID of the LR session
        :return: {ListProcessesCommand} The command object
        """
        payload = {"name": PROCESSES_DEFAULT, "session_id": session_id}
        response = self.cb_cloud_session.post(
            self._get_full_url("create_command", session_id=session_id), json=payload
        )
        self.validate_response(
            response, f"Unable to initiate list files command in session {session_id}"
        )

        return self.parser.build_siemplify_command_obj(
            response.json(), version=API_VERSION_V6
        )

    def start_command_for_get_file(self, session_id, path):
        """
        Initiate a get file command for a given session
        :param session_id: {str} The ID of the LR session
        :param path: {str} Remote directory path to get file
        :return: {Command} The command object
        """
        payload = {"name": GET_FILE_DEFAULT, "session_id": session_id, "object": path}
        response = self.cb_cloud_session.post(
            self._get_full_url("create_command", session_id=session_id), json=payload
        )
        self.validate_response(
            response, f"Unable to initiate list files command in session {session_id}"
        )

        return self.parser.build_siemplify_command_obj(
            response.json(), version=API_VERSION_V6
        )

    def get_file_content(self, session_id, file_id):
        """
        Get file content
        :param session_id: {str} The ID of the LR session
        :param file_id: {str} File id
        :return: File content
        """
        response = self.cb_cloud_session.get(
            self._get_full_url("get_file", session_id=session_id, file_id=file_id)
        )
        self.validate_response(response)

        return response.content

    def get_command_by_id(self, session_id, command_id, start_from=0, limit=None):
        """
        Get a command by id and session id
        :param session_id: {str} The ID of the LR session
        :param command_id: {str} The ID of the command
        :param start_from: {str} Start from getting
        :param limit: {str} Limit results
        :return: {Command} The command object
        """
        response = self.cb_cloud_session.get(
            self._get_full_url(
                "get_command", session_id=session_id, command_id=command_id
            )
        )
        self.validate_response(
            response, f"Unable to get command {command_id} for session {session_id}"
        )

        return self.parser.build_siemplify_command_obj(
            response.json(), start_from=start_from, limit=limit, version=API_VERSION_V6
        )

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
        response = self.cb_cloud_session.post(
            self._get_full_url("create_command", session_id=session_id), json=payload
        )
        self.validate_response(
            response, f"Unable to initiate delete file command in session {session_id}"
        )

        return self.parser.build_siemplify_command_obj(
            response.json(), version=API_VERSION_V6
        )

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
        response = self.cb_cloud_session.post(
            self._get_full_url("init_command", session_id=session_id), json=payload
        )
        self.validate_response(
            response, f"Unable to initiate put file command in session {session_id}"
        )
        return self.parser.build_siemplify_command_obj(
            response.json(), version=API_VERSION_V6
        )

    def upload_file(self, session_id, file_path):
        """
        Upload file to server
        :param session_id: {str} The ID of the LR session
        :param file_path: {str} Source file path to get the file to upload
        :return: {UploadFile} UploadFile object
        """

        files = {"file": open(file_path, "rb")}
        response = self.cb_cloud_session.post(
            self._get_full_url("upload_file", session_id=session_id), files=files
        )
        self.validate_response(
            response, f"Unable to upload file in session {session_id}"
        )

        return self.parser.build_siemplify_upload_file_obj(response.json())

    def get_process_command_by_id(
        self, session_id, command_id, process_name=None, limit=None
    ):
        """
        Get a command by id and session id
        :param session_id: {str} The ID of the LR session
        :param command_id: {str} The ID of the command
        :param process_name: {str} Process name for filter processes
        :param limit: {str} Limit results
        :return: {Command} The command object
        """
        response = self.cb_cloud_session.get(
            self._get_full_url(
                "get_command", session_id=session_id, command_id=command_id
            )
        )
        self.validate_response(
            response, f"Unable to get command {command_id} for session {session_id}"
        )

        return self.parser.build_siemplify_process_command_obj(
            response.json(),
            process_name=process_name,
            limit=limit,
            version=API_VERSION_V6,
        )

    def initiate_kill_process_command(self, session_id, pid):
        """
        Initiate a list processes command in a given session (ps command)
        :param session_id: {str} The ID of the LR session
        :param pid: {str} The PID of the process to kill
        :return: {ListProcessesCommand} The command object
        """
        payload = {"name": "kill", "session_id": session_id, "pid": pid}
        response = self.cb_cloud_session.post(
            self._get_full_url("create_command", session_id=session_id), json=payload
        )
        self.validate_response(
            response, f"Unable to initiate kill process command in session {session_id}"
        )
        return self.parser.build_siemplify_kill_process_command_obj(response.json())

    def get_kill_process_command_by_id(self, session_id, command_id):
        """
        Get a kill process command object
        :param session_id: {str} The ID of the LR session
        :param command_id: {str} The ID of the command
        :return: {KillProcessCommand} The command object
        """
        command = self.get_command_by_id(session_id, command_id)
        return self.parser.build_siemplify_kill_process_command_obj(command.raw_data)

    def get_storage_files_for_session(self, session_id, start_from=0, limit=None):
        """
        Get list of files by session id
        :param session_id: {str} The ID of the session
        :param start_from: {str} Start from getting
        :param limit: {str} Limit results
        :return: {list} List of files for session
        """
        response = self.cb_cloud_session.get(
            self._get_full_url("storage_files_list", session_id=session_id)
        )
        self.validate_response(
            response,
            f"Unable to initiate get files from storage for session {session_id}",
        )

        return self.parser.get_files_objects(response.json(), start_from, limit)

    def start_command_to_create_memdump(self, session_id, path):
        """
        Initiate a memdump file
        :param session_id: {str} The ID of the LR session
        :param path: {str} Remote directory path to create memdump
        :return: {Command} The command object
        """
        payload = {"name": MEMDUMP_DEFAULT, "session_id": session_id, "object": path}
        response = self.cb_cloud_session.post(
            self._get_full_url("create_command", session_id=session_id), json=payload
        )
        self.validate_response(
            response,
            f"Unable to initiate create memdump command in session {session_id}",
        )

        return self.parser.build_siemplify_command_obj(
            response.json(), version=API_VERSION_V6
        )

    def get_memdump_command_by_id(self, session_id, command_id):
        """
        Get a command by id and session id
        :param session_id: {str} The ID of the LR session
        :param command_id: {str} The ID of the command
        :return: {Command} The command object
        """
        command = self.get_command_by_id(session_id, command_id)

        return self.parser.build_siemplify_memdump_command_obj(command.raw_data)

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
        response = self.cb_cloud_session.post(
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

        return self.parser.build_siemplify_execute_file_command_obj(
            command.raw_data, version=API_VERSION_V6
        )

    def delete_file_from_storage(self, session_id, file_id):
        """
        Delete file from storage by session id
        :param session_id: {str} The ID of the LR session
        :param file_id: {str} File id
        """
        response = self.cb_cloud_session.delete(
            self._get_full_url("delete_file", session_id=session_id, file_id=file_id)
        )
        self.validate_response(
            response, f"Unable to delete file in session {session_id}"
        )
        return True
