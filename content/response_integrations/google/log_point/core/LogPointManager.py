from __future__ import annotations
import base64
import json
import requests
from . import datamodels
from . import consts
import time
import copy
from urllib.parse import urljoin
from typing import List, Optional, Union
from .LogPointParser import LogPointParser
from .exceptions import (
    LogPointApiException,
    LogPointUnsuccessfulQueryResultsException,
    LogPointCredentialsException,
)
from .utils import remove_empty_kwargs


ENDPOINTS = {
    "ping": "/getalloweddata",
    "list_repos": "/getalloweddata",
    "incidents": "/incidents",
    "incident_data": "/get_data_from_incident",
    "create_query_job": "/getsearchlogs",
    "get_query_results": "/getsearchlogs",
    "close_incident": "/close_incident",
    "resolve_incident": "/resolve_incident",
    "get_users": "/get_users",
}

HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}
HEADERSCONTENTTYPEJSON = {"Content-Type": "application/json"}

# Certificate file temp path
CA_CERTIFICATE_FILE_PATH = "cert.crt"


class LogPointManager:
    def __init__(
        self,
        ip_address,
        username,
        secret,
        ca_certificate_file=None,
        verify_ssl=False,
        force_check_connectivity=False,
        logger=None,
    ):
        """
        The method is used to init an object of Manager class
        """
        self.host_api = ip_address[:-1] if ip_address.endswith("/") else ip_address
        self.username = username
        self.secret = secret
        self.session = requests.Session()
        self.set_original_headers()
        self.session.verify = self.__get_verification(
            verify_ssl=verify_ssl, certificate=ca_certificate_file
        )

        self.parser = LogPointParser()
        self.logger = logger

        if force_check_connectivity:
            self.test_connectivity()

    def __get_verification(self, verify_ssl, certificate=None):
        """
        Validate the verification in case that VerifySSL is enabled.
        :param verify_ssl: {bool} If true, verify the SSL certificate for the connection to the LogPoint server is valid.
        :param certificate: {str} Base 64 encoded CA certificate file. Located in *.crt file and need to be encoded to base64
        :return CA_CERTIFICATE_FILE_PATH: {str} The path to the certification file that was created.
        """
        if certificate and verify_ssl:
            try:
                file_content = base64.b64decode(certificate)
                with open(CA_CERTIFICATE_FILE_PATH, "w+") as f:
                    f.write(file_content.decode())
            except Exception as e:
                raise LogPointApiException(
                    f"Unable to decode the certificate file. Reason: {e}"
                ) from e
            return CA_CERTIFICATE_FILE_PATH

        return verify_ssl

    def _get_full_url(self, url_key, **kwargs):
        """
        Get full url from url key.
        :param url_key: {str} the key of url
        :param kwargs: {dict}  Variables passed for string formatting
        :return: {str} The full url
        """
        api_root = self.host_api
        return urljoin(api_root, ENDPOINTS.get(url_key).format(**kwargs))

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} Default message to display on error
        """
        try:
            if response.status_code == consts.VALID_RESPONSE:
                if not json.loads(response.text).get("success"):
                    raise LogPointCredentialsException(
                        json.loads(response.text).get("message")
                    )

            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise LogPointApiException(
                    f"{error_msg}: {error} - {error.response.content}"
                )

            raise LogPointApiException(
                f"{error_msg}: {error} {response.json().get('message')}"
            )

    def test_connectivity(self):
        """
        Test connectivity to the Logpoint with parameters provided at the integration configuration page on the
        Marketplace tab.
        """
        payload = {
            "username": self.username,
            "secret_key": self.secret,
            "type": consts.USER_PREFERENCE,
        }

        response = self.session.post(self._get_full_url("ping"), data=payload)

        self.validate_response(response)

    def set_original_headers(self):
        """
        Set request header
        """
        self.session.headers = copy.deepcopy(HEADERS)

    def set_json_header(self):
        """
        Set request header
        """
        self.session.headers.update(HEADERSCONTENTTYPEJSON)

    def list_repos(
        self, max_repos_to_return: Optional[int] = None
    ) -> List[datamodels.Repo]:
        """
        List available repos in Logpoint.
        :param max_repos_to_return: {int} Maximum, number of repos to return
        :return: [{datamodels.Repo}] list of Repos
        """
        request_url = self._get_full_url("list_repos")
        payload = {
            "username": self.username,
            "secret_key": self.secret,
            "type": "logpoint_repos",
        }

        response = self.session.post(request_url, data=payload)
        self.validate_response(response, "Unable to list repos")
        return self.parser.build_repo_objs(response, max_repos=max_repos_to_return)

    def create_query_job(
        self,
        time_range: Union[List[int], str],
        query: str,
        limit: Optional[int] = None,
        repos: List[str] = None,
    ) -> datamodels.QueryJob:
        """
        Create query job in Logpoint. Timeout of the query is 300 seconds.
        :param time_range: {[int,int] or str} Time range of the query. Can be list of 2 timestamps [1609496280,1610274480] or custom
        range represented as string for example: "Last 24 Hours"
        :param query: {str} Valid search query to execute in Logpoint
        :param limit: {int} Max records of search results to return
        :param repos: {[str]} List of IP addresses of the repos
        :return: {datamodels.QueryJob} Query job that was successfully executed
        """
        request_url = self._get_full_url("create_query_job")

        payload = {
            "username": self.username,
            "secret_key": self.secret,
            "requestData": json.dumps(
                {
                    # indicates the the waiting time (seconds) for a request before
                    # canceling it
                    "timeout": 300,
                    "client_name": "gui",
                    "repos": repos or [],
                    "starts": {},
                    "time_range": time_range,
                    "limit": limit,
                    "query": query,
                }
            ),
        }

        response = self.session.post(request_url, data=remove_empty_kwargs(**payload))

        # Check if creating query job was not successful
        try:
            json_response = response.json()
            if not json_response.get("success", True):
                raise LogPointUnsuccessfulQueryResultsException(
                    json_response.get("message") or "Failed to create query job"
                )
        except LogPointUnsuccessfulQueryResultsException:
            raise
        except Exception:
            pass

        self.validate_response(response, error_msg="Failed to create query job")
        return self.parser.build_query_job_obj(response.json())

    def get_query_results(self, search_id: str) -> datamodels.QueryResults:
        """
        Get search results logs based on search id.
        :param search_id: {str} Unique search id to retrieve results for
        :return: {datamodels.QueryResults}
            raise LogPointApiException if failed to validate response or querying for results didn't succeeded
        """
        request_url = self._get_full_url("get_query_results")
        payload = {
            "username": self.username,
            "secret_key": self.secret,
            "requestData": json.dumps({"search_id": search_id}),
        }
        response = self.session.post(request_url, data=payload)
        # Check if querying results is not successful
        try:
            json_response = response.json()
            if not json_response.get("success", True):
                raise LogPointUnsuccessfulQueryResultsException(
                    json_response.get("message")
                    or f"Failed to get query results for search job with id {search_id}"
                )
        except LogPointUnsuccessfulQueryResultsException:
            raise
        except Exception:
            pass

        self.validate_response(
            response,
            error_msg=f"Failed to get query results for search job with id {search_id}",
        )
        return self.parser.build_query_results_obj(response)

    def close_incident_status(self, incident_id: str) -> bool:
        """
        Close incident based on incident id.
        :param incident_id: {str} Id of the incident, which should be closed
        :return: {bool}
        """
        self.set_json_header()
        payload = {
            "username": self.username,
            "secret_key": self.secret,
            "requestData": {"incident_ids": [incident_id]},
        }

        response = self.session.post(self._get_full_url("close_incident"), json=payload)
        self.validate_response(response, "Unable to close incident")
        self.set_original_headers()

        return True

    def resolve_incident_status(self, incident_id: str) -> bool:
        """
        Resolve incident based on incident id.
        :param incident_id: {str} Id of the incident, which should be closed
        :return: {bool}
        """
        self.set_json_header()
        payload = {
            "username": self.username,
            "secret_key": self.secret,
            "requestData": {"incident_ids": [incident_id]},
        }

        response = self.session.post(
            self._get_full_url("resolve_incident"), json=payload
        )
        self.validate_response(response, "Unable to resolve incident")
        self.set_original_headers()

        return True

    def resolve_and_close_incident(self, incident_id: str) -> bool:
        """
        Resolve and Close incident based on Incident Id.
        :param incident_id: {str} Id of the incident, which should be resolved and closed
        :return: {bool}
        """
        try:
            self.resolve_incident_status(incident_id)
        except:
            pass

        self.close_incident_status(incident_id)

        return True

    def get_information_about_incident(self, id, incident_id, detection_timestamp):
        """
        Get Incident details
        :param id: {str}
        :param incident_id: {str}
        :param detection_timestamp: {int} unix
        :return: {list} List instance of IncidentDetails objects
        """
        self.set_json_header()
        data = {
            "username": self.username,
            "secret_key": self.secret,
            "requestData": {
                "incident_id": incident_id,
                "incident_obj_id": id,
                "date": detection_timestamp,
            },
        }
        response = self.session.get(self._get_full_url("incident_data"), json=data)
        self.validate_response(
            response, error_msg=f"Failed to get incident details for {incident_id}"
        )
        self.set_original_headers()
        return self.parser.build_incident_information(response.json())

    def get_incidents(self, start_time, end_time):
        """
        Get Incidents
        :param start_time: {int} unix time to load starting provided date
        :param end_time: {int} unix time to load till provided date
        :return: {list} List instance of Incident objects
        """
        self.set_json_header()

        data = {
            "username": self.username,
            "secret_key": self.secret,
            "requestData": {"version": "0.1", "ts_from": start_time, "ts_to": end_time},
        }
        response = self.session.get(self._get_full_url("incidents"), json=data)

        self.validate_response(response, error_msg="Failed to get Incidents")
        self.set_original_headers()
        return self.parser.build_incidents_list(response.json())

    def get_aggregated_events(self, query, main_event, time_range):
        """
        Get Aggregated events with a query
        :param query: {str} Incident query
        :param main_event: {IncidentDetails} Incident main event object
        :param time_range: {list} Incident time range
        :return: {list} List instance of IncidentEvent objects
        """
        query = self.construct_query_with_values(query, main_event)

        query_job = self.create_query_job(
            time_range=time_range, query=query, limit=consts.EVENTS_TOTAL_COUNT
        )
        if query_job.success:
            query_result = self.get_query_results(search_id=query_job.search_id)

            while not query_result.finished:
                time.sleep(consts.SLEEP_TIME)
                query_result = self.get_query_results(search_id=query_job.search_id)

            return self.parser.build_incident_events_list(query_result.query_rows)
        else:
            self.logger.info(
                "Wasn't able to successfully execute query and retrieve results for "
                "incident"
            )

    @staticmethod
    def construct_query_with_values(query, data):
        """
        Construct query with the values from provided data
        :param query: {str} Incident query
        :param data: {IncidentDetails} IncidentDetails object
        :return: {str} Constructed query
        """
        keys_string = (
            query.split(consts.CHART_STRING)[1].split("by")[1].split("|")[0].strip()
        )
        keys = [key.strip().split(" ")[0] for key in keys_string.split(",")]
        query = query.split(consts.CHART_STRING)[0]

        for key in keys:
            # Add | filter for every key and it's value
            value = data.to_json().get(key.strip(), "")
            query = (
                query
                + "| filter "
                + f'"{key.strip()}"="{value if value is not None else "*"}"'
            )

        return query

    def get_users(self):
        """
        Get users
        :return: {[User]} list of User objects
        """
        self.set_json_header()
        url = self._get_full_url("get_users")
        data = {"username": self.username, "secret_key": self.secret}

        response = self.session.get(url, json=data)
        self.validate_response(response)
        self.set_original_headers()
        return self.parser.build_user_objects(response.json())
