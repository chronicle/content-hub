from __future__ import annotations
import requests
import urllib.parse
from urllib.parse import urljoin
from tanium.core import datamodels
from tanium.core.TaniumParser import TaniumParser
from tanium.core.constants import (
    ASC_SORT_ORDER,
    BAD_REQUEST_STATUS_CODE,
    INTEGRATION_VERSION,
    MAX_QUESTION_RESULTS_DEFAULT,
    NOT_FOUND_STATUS_CODE,
    PROCESS_EVENT_TYPE,
    QUARANTINE_TASK,
    UNAUTHORIZED_STATUS_CODE,
)
from tanium.core.exceptions import TaniumBadRequestException, TaniumNotFoundException
from soar_sdk.SiemplifyDataModel import EntityTypes


HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

API_ENDPOINTS = {
    "ping": "/api/v2/session/management_rights",
    "create_question": "/api/v2/questions",
    "question_results": "/api/v2/result_data/question/{question_id}",
    "get_open_connections": "/plugin/products/threat-response/api/v1/conns",
    "get_endpoint_details": "/plugin/products/dec/v1/endpoints",
    "create_connection": "/plugin/products/threat-response/api/v1/conns/connect",
    "get_connection_events": "/plugin/products/threat-response/api/v1/conns/{connection_id}/views/{event_type}/events",
    "get_task_details": "/plugin/products/threat-response/api/v1/tasks/{task_id}",
    "create_file_evidence_task": "/plugin/products/threat-response/api/v1/conns/{connection_id}/file",
    "get_file_data": "/plugin/products/threat-response/api/v1/filedownload/data/{file_uuid}",
    "delete_file": "/plugin/products/threat-response/api/v1/conns/{connection_id}/file/delete/{file_path}",
    "initiate_quarantine": "/plugin/products/threat-response/api/v1/response-actions",
    "get_tasks": "/plugin/products/threat-response/api/v1/tasks",
}

HOSTNAME_TYPE_MACHINE_QUERY = (
    "Get Computer ID and Operating System and OS Platform and Service Pack and Domain Name "
    "and Uptime and System UUID and IP Address and Computer Name and Username"
    "{additional_fields} from all machines with Computer Name matches {entity_identifier}"
)

ADDRESS_TYPE_MACHINE_QUERY = (
    "Get Computer ID and Operating System and OS Platform and Service Pack and Domain Name "
    "and Uptime and System UUID and IP Address and Computer Name and Username"
    "{additional_fields} from all machines with IP Address matches {entity_identifier}"
)

QUERY_MAPPER = {
    EntityTypes.HOSTNAME: HOSTNAME_TYPE_MACHINE_QUERY,
    EntityTypes.ADDRESS: ADDRESS_TYPE_MACHINE_QUERY,
}


class TaniumManager:
    def __init__(
        self,
        api_token,
        api_root,
        verify_ssl=False,
        force_check_connectivity=False,
        logger=None,
    ):
        self.api_token = api_token
        self.api_root = api_root
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(HEADERS)
        self.session.headers.update({
            "session": self.api_token,
            "x-tanium-integration": f"googlesecops-taniumrest-{INTEGRATION_VERSION}",
        })
        self.logger = logger
        self.parser = TaniumParser()
        if force_check_connectivity:
            self.test_connectivity()

    def _get_full_url(self, url_key, **kwargs) -> str:
        """
        Get full url from url key.
        :param url_key: {str} The key of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, API_ENDPOINTS[url_key].format(**kwargs))

    def test_connectivity(self):
        """
        Test connection with Tanium server
        :return: {bool} true if successfully connected to Tanium
            raise general exception if failed to validate response status code
        """
        response = self.session.post(self._get_full_url("ping"))
        self.validate_response(response)

    def create_question(self, question):
        """
        Create Question
        :param question: {str} question text
        :return: {int} return question_id if created or
            raise general exception if failed to validate response status code
        """
        payload = {"query_text": question}
        response = self.session.post(
            self._get_full_url("create_question"), json=payload
        )
        self.validate_response(response)

        return self.parser.build_question_obj(response.json())

    def create_question_for_machine(
        self, entity_identifier, entity_type, additional_fields
    ):
        """
        Create Question for machine
        :param entity_identifier: {str} entity identifier
        :param entity_type: {str} entity type
        :param additional_fields: {list} fields that should be added to main query text
        :return: {int} return question_id if created or
            raise general exception if failed to validate response status code
        """
        additional_string = ""
        if additional_fields:
            additional_string = f" and {' and '.join(additional_fields)}"
        payload = {
            "query_text": QUERY_MAPPER[entity_type].format(
                additional_fields=additional_string, entity_identifier=entity_identifier
            )
        }

        response = self.session.post(
            self._get_full_url("create_question"), json=payload
        )
        self.validate_response(response)

        return self.parser.build_question_obj(response.json())

    def get_question_result_full_data(
        self, question_id, limit: int = MAX_QUESTION_RESULTS_DEFAULT
    ) -> datamodels.QuestionResultFullData:
        """Fetches the full results data for a specific question ID.

        Makes a GET request to retrieve the results for the given question,
        validates the API response, and then parses the JSON payload into a
        `QuestionResultFullData` object.

        Args:
            question_id: The unique identifier (int) for the question.
            limit (int): The maximum number of result rows to process and
                return in the parsed object. Defaults to `MAX_QUESTION_RESULTS_DEFAULT`.

        Returns:
            datamodels.QuestionResultFullData: An object containing the parsed
                results for the question.

        Raises:
            Exception: An exception is raised by `self.validate_response` if
                the API request fails or returns an unsuccessful status code.
        """
        response = self.session.get(
            self._get_full_url("question_results", question_id=question_id)
        )
        self.validate_response(response)

        question_result = datamodels.QuestionResultFullData.from_raw_response(
            raw_data=response.json(), limit=limit
        )
        if question_result.expire_seconds < question_result.seconds_since_issued:
            raise TaniumNotFoundException("Question result has expired.")

        return question_result

    def get_question_result(self, question_id, limit=None):
        """
        Get Question results
        :param question_id: {int} The question id
        :param limit: {int} limit how rows should be returned, limit works on Siemplify side
        :return: {Question} true if successfully connected to Tanium
            raise general exception if failed to validate response status code
        """
        response = self.session.get(
            self._get_full_url("question_results", question_id=question_id)
        )
        self.validate_response(response)

        return self.parser.build_question_result_obj(response.json(), limit)

    def get_open_connections(self):
        """
        Get open connections
        :return: {Connection} true if successfully connected to Tanium
            raise general exception if failed to validate response status code
        """
        response = self.session.get(self._get_full_url("get_open_connections"))
        self.validate_response(response)

        return self.parser.build_results(
            raw_json=response.json(), method="build_connection_obj", pure_data=True
        )

    def get_endpoint_details(self, entity_type, entity_identifier) -> list:
        """Get endpoint details by ip or hostname

        Args:
            entity_type: The type of entity processed
            entity_identifier: The identifier of entity processed

        Returns:
            list: endpoint details
        """
        params = {entity_type: entity_identifier}
        response = self.session.get(
            self._get_full_url("get_endpoint_details"), params=params
        )
        self.validate_response(response)

        return self.parser.build_results(
            raw_json=response.json(), method="build_endpoint_details_obj"
        )

    def create_conection(self, hostname, ip, client_id, platform):
        """
        Create Connection
        :param hostname: {str} Hostname to connect
        :param ip: {str} IP address to use for connection
        :param client_id: {str} Client ID to use for connection
        :param platform: {str} Platform to use for connection
        :return: {str} return connection_id if created or
            raise general exception if failed to validate response status code
        """
        payload = {
            "target": {
                "hostname": hostname,
                "ip": ip,
                "clientId": client_id,
                "platform": platform,
            }
        }

        response = self.session.post(
            self._get_full_url("create_connection"), json=payload
        )
        self.validate_response(response)

        return response.json()

    def get_connection_events(
        self,
        connection_id,
        start_time,
        end_time,
        sort_field,
        sort_order,
        event_type,
        limit,
    ):
        """
        Get Connection Events
        :param connection_id: {str} Id of the connection
        :param start_time: {str} Start time for results
        :param end_time: {str} End time for results
        :param sort_field: {str} Field to sort results with
        :param sort_order: {str} Sort order to apply
        :param event_type: {str} Type of events to return
        :return: {list} return list of events or
            raise general exception if failed to validate response status code
        """
        url = self._get_full_url(
            "get_connection_events", connection_id=connection_id, event_type=event_type
        )
        params = {
            "match": "all",
            "f1": (
                "create_time_raw"
                if event_type == PROCESS_EVENT_TYPE
                else "timestamp_raw"
            ),
            "o1": "gte",
            "v1": start_time,
            "f2": (
                "create_time_raw"
                if event_type == PROCESS_EVENT_TYPE
                else "timestamp_raw"
            ),
            "o2": "lte",
            "v2": end_time,
        }

        if sort_field:
            params["sort"] = (
                f"+{sort_field}" if sort_order == ASC_SORT_ORDER else f"-{sort_field}"
            )

        response = self.session.get(url, params=params)
        self.validate_response(response)

        return response.json()[:limit]

    def get_task_details(self, task_id):
        """
        Get task details by id
        :param task_id: {str} Task ID
        :return: {Task} Task object if successfully connected to Tanium
            raise general exception if failed to validate response status code
        """
        url = self._get_full_url("get_task_details", task_id=task_id)
        response = self.session.get(url)
        self.validate_response(response)

        return self.parser.build_task_obj(raw_json=response.json())

    def get_tasks(self):
        """
        Get all tasks
        :return: {list} List of Task objects if successfully connected to Tanium
            raise general exception if failed to validate response status code
        """
        url = self._get_full_url("get_tasks")
        response = self.session.get(url)
        self.validate_response(response)

        return self.parser.build_tasks_list(raw_json=response.json())

    def create_file_evidence_task(self, connection_id, file_path):
        """
        Create file evidence task
        :param connection_id: {str} Id of the connection
        :param file_path: {str} File path to create task for
        :return: {Task} return Task object if successfully connected to Tanium or
            raise general exception if failed to validate response status code
        """
        url = self._get_full_url(
            "create_file_evidence_task", connection_id=connection_id
        )
        payload = {"path": file_path}

        response = self.session.post(url, json=payload)
        self.validate_response(response)

        return response.json().get("taskInfo", {}).get("id")

    def get_file(self, file_uuid: str) -> bytes:
        """Download file

        Args:
          file_uuid(str): File UUID.

        Returns:
          bytes: Text of the response.
        """
        url = self._get_full_url("get_file_data", file_uuid=file_uuid)
        response = self.session.get(url)
        self.validate_response(response)

        return response.content

    def delete_file(self, connection_id, file_path):
        """
        Delete file
        :param connection_id: {str} Id of the connection
        :param file_path: {str} Path of the file
        :return: {}
            raise general exception if failed to validate response status code
        """
        url = self._get_full_url(
            "delete_file",
            connection_id=connection_id,
            file_path=urllib.parse.quote_plus(file_path),
        )
        response = self.session.delete(url)
        self.validate_response(response)

    def initiate_quarantine(
        self, computer_name, package_name, expiration_time, package_params
    ):
        """
        Initiate quarantine on an endpoint
        :param computer_name: {str} Hostname to initiate the quarantine on
        :param package_name: {str} Package name to apply
        :param expiration_time: {str} Expiration time for the task
        :param package_params: {list} List of parameters for the package being deployed
        :return: {str} return ID of the task if successfully connected to Tanium or
            raise general exception if failed to validate response status code
        """
        url = self._get_full_url("initiate_quarantine")
        payload = {
            "type": QUARANTINE_TASK,
            "computerName": computer_name,
            "expirationTime": expiration_time,
            "options": {
                "packageName": package_name,
                "packageParameters": package_params,
            },
        }

        response = self.session.post(url, json=payload)
        self.validate_response(response)

        return response.json().get("data", {}).get("id")

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} Default message to display on error
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            if (
                hasattr(response, "status_code")
                and response.status_code == UNAUTHORIZED_STATUS_CODE
            ):
                raise Exception(f"{error_msg}: {error} {error.response.content}")

            if BAD_REQUEST_STATUS_CODE in response.json().get("text", ""):
                raise TaniumBadRequestException

            if NOT_FOUND_STATUS_CODE in response.json().get("text", ""):
                raise TaniumNotFoundException

            raise Exception(f"{error_msg}: {error} {error.response.content}")

        return True
