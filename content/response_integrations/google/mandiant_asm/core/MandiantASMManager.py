from __future__ import annotations
from typing import List, Optional
import requests
from datetime import datetime
from urllib.parse import urljoin

from .exceptions import (
    InvalidParametersException,
    InvalidUnicodeKeyError,
    MandiantManagerException,
    ProjectNotFoundError,
)
from .constants import (
    DEFAULT_PAGE_SIZE,
    ENDPOINTS,
    ERROR_CODE,
    WRONG_API_ERROR_MESSAGE,
    INTEGRATION_DISPLAY_NAME,
    ISSUE_STATUS_MAPPING,
    SEVERITY_MAPPING,
)
from .MandiantASMParser import MandiantASMParser
from TIPCommon import is_approaching_timeout
from .UtilsManager import get_project_id, sanitize_identifiers


class MandiantASMManager:
    def __init__(
        self,
        api_root: str,
        project_name: str,
        verify_ssl: bool,
        siemplify_logger: Optional[any] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        gti_api_key: Optional[str] = None,
    ):
        """The method is used to init an object of Manager class.

        Args:
            api_root (str): Mandiant ASM API root
            project_name (str): The name of the project.
            verify_ssl: {bool} Specifies if certificate that is configured on the
                api root should be validated.
            siemplify_logger: {Optional[any]} Optional logger instance used for logging.
            access_key: {str} Mandiant ASM Access Key.
            secret_key: {str} Mandiant ASM  Secret key.
            gti_api_key: {Optional[str]} An optional API key for GTI services.
                If not provided, defaults to None.
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.access_key = access_key
        self.secret_key = secret_key
        self.gti_api_key = gti_api_key
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self._validate_keys()

        headers = {"Accept": "application/json"}
        if self.gti_api_key:
            headers["x-apikey"] = gti_api_key
        else:
            headers["INTRIGUE_ACCESS_KEY"] = access_key
            headers["INTRIGUE_SECRET_KEY"] = secret_key

        self.session.headers.update(headers)

        self.project_id = self.set_project_id(project_name)
        self.parser = MandiantASMParser()

    def _validate_keys(self) -> None:
        """Validate that the provided keys do not contain Unicode characters
        and ensure that at least one of the required keys is provided.
        """

        if not self.access_key and not self.secret_key and not self.gti_api_key:
            raise InvalidParametersException(
                'either "Client ID" + "Client Secret" or '
                '"GTI API Key" should be provided. Make sure that the correct API'
                " root is provided as well."
            )

        for key in [self.access_key, self.secret_key, self.gti_api_key]:
            if key and any(ord(char) > 127 for char in key):
                raise InvalidUnicodeKeyError(
                    "Please verify the 'Client ID,' 'Client Secret,' or 'GTI API Key'"
                    " credentials."
                )

    def _get_full_url(
        self,
        api_root: str,
        endpoint_id: str,
        gti_api_key: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Constructs the full URL based on the API root, endpoint identifier, and
            whether the GTI API key is provided.

        Args:
            api_root (str): The base URL for the API.
            endpoint_id (str): The identifier for the specific API endpoint.
            gti_api_key (Optional[str]): The GTI API key, if available. Determines
                whether to use a GTI-specific endpoint or a non-GTI endpoint.
            kwargs (dict): Additional variables passed for string formatting of
                the endpoint URL.

        Returns:
            str: The fully constructed URL.
        """
        endpoint_type = "gti" if gti_api_key is not None else "non_gti"

        return urljoin(api_root, ENDPOINTS[endpoint_id][endpoint_type].format(**kwargs))

    def set_project_id(self, project_name):
        """
        Set Project ID from project name.
        :param project_name: {str} The name of the Project
        :return: {str} id of project matching project_name
        """
        url = self._get_full_url(
            api_root=self.api_root,
            endpoint_id="index_projects",
            gti_api_key=self.gti_api_key,
        )

        response = self.session.get(url)
        self.validate_response(response)
        projects = response.json()["result"]
        if project_name:
            project_id = get_project_id(projects, project_name)

            if not project_id:
                raise ProjectNotFoundError(
                    f"Failed to find Project {project_name} "
                    f"with the provided credentials."
                )

            return project_id

    @staticmethod
    def validate_response(response, error_msg="An error occurred") -> None:
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} Default message to display on error
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                if (
                    response.json().get("error", {})
                    and response.json().get("error", {}) == ERROR_CODE
                ):
                    raise InvalidParametersException(
                        f"{error_msg}: {WRONG_API_ERROR_MESSAGE}"
                    ) from error

                raise MandiantManagerException(response.json()["message"])
            except (ValueError, KeyError):
                pass

            raise MandiantManagerException(
                f"{error_msg}: {error} {error.response.content}"
            )

        return True

    @staticmethod
    def build_query_for_single_params(**kwargs):
        query_string = ""
        for param_name, param_value in kwargs.items():
            if param_value:
                query_string += f"{param_name}:{param_value} "

        return query_string

    @staticmethod
    def build_query_for_collection_params(**kwargs):
        query_string = ""
        for param_name, param_values in kwargs.items():
            if param_values:
                for param_value in param_values:
                    query_string += f"{param_name}:{param_value} "

        return query_string

    def build_query_string(
        self,
        entity_name: List[str],
        issue_ids: List[str],
        entity_ids: List[str],
        tags: List[str],
        time_parameter: str,
        start_time: datetime,
        end_time: datetime,
        status: str,
    ):
        """
        Build query string for Mandiant ASM.

        Params:
            :param entity_name: {List[str]} Entity names list
            :param issue_ids: {List[str]} List of issue ids
            :param entity_ids: {List[str]} List of entity ids
            :param tags: {List[str]} List of entity tags
            :param time_parameter: {str} Time parameter to Last seen / First seen
            :param start_time: {datetime} Start time for period
            :param end_time: {datetime} End time for period
            :param status: {str} Status to filter out by

        Returns:
            {str} query string to use in filter
        """
        query_string = ""
        time_kwargs = {}

        if time_parameter == "First Seen":
            time_kwargs = {
                "first_seen_before": end_time.isoformat(),
                "first_seen_after": start_time.isoformat(),
            }
        elif time_parameter == "Last Seen":
            time_kwargs = {
                "last_seen_before": end_time.isoformat(),
                "last_seen_after": start_time.isoformat(),
            }

        query_string += self.build_query_for_single_params(
            status_new=status, **time_kwargs
        )

        query_string += self.build_query_for_collection_params(
            entity_name=sanitize_identifiers(entity_name) if entity_name else [],
            id=issue_ids,
            entity_uid=entity_ids,
            tag=tags,
        )

        return query_string

    def search_issues(
        self,
        lowest_severity: str,
        limit: int,
        script_starting_time: int,
        execution_deadline: int,
        **kwargs,
    ):
        """
        Searches issues that match specified criteria up to limit.

        Params:
            :param lowest_severity: {int} the lowest severity to fetch issues.
            :param limit: {int} Limitation of how much issues to fetch
            :param script_starting_time: {int} Script starting time
            :param execution_deadline: {int} Execution deadline
            :param kwargs: {Dict[str, Any]} the dictionary that contains all kwargs params specified for filtering,
                check build_query_string for details.

        Returns:
            Tuple(Hits {List[obj]}, More {bool})
        """
        page_number = 0
        filtered_issues = []

        query_string = self.build_query_string(
            entity_name=kwargs.get("entity_name"),
            issue_ids=kwargs.get("issue_ids"),
            entity_ids=kwargs.get("entity_ids"),
            tags=kwargs.get("tags"),
            time_parameter=kwargs.get("time_parameter"),
            start_time=kwargs.get("start_time"),
            end_time=kwargs.get("end_time"),
            status=kwargs.get("status"),
        )

        lowest_severity = (
            SEVERITY_MAPPING[lowest_severity.lower()] if lowest_severity else ""
        )

        self.siemplify_logger.info(f"Searching Issues in {INTEGRATION_DISPLAY_NAME}")

        while True:
            if is_approaching_timeout(script_starting_time, execution_deadline):
                self.siemplify_logger.info(
                    "Timeout is approaching. Action will gracefully exit"
                )
                break

            issues, more_pages = self.search_issues_by_page(
                lowest_severity=lowest_severity,
                query_string=query_string,
                page_number=page_number,
            )
            filtered_issues.extend(issues)

            if len(filtered_issues) >= limit or not more_pages:
                self.siemplify_logger.info(
                    f"Reached Maximum count of entities to process of {limit} !"
                )
                break

            page_number += 1

        return filtered_issues[:limit]

    def search_issues_by_page(self, lowest_severity, query_string, page_number):
        """
        Searches issues that match query string criteria and returns specified page results.

        Params:
            :param lowest_severity: {int} the lowest severity to fetch issues.
            :param query_string: {str} criteria to search for entities.
            :param page_number: {str} result page_number to fetch.

        Returns:
            Tuple(Hits {List[obj]}, More {bool})
        """
        if self.project_id:
            self.session.headers.update({"PROJECT-ID": self.project_id})
        self.session.params = {"page_size": DEFAULT_PAGE_SIZE, "page": page_number}
        url = self._get_full_url(
            api_root=self.api_root,
            endpoint_id="search_issues",
            gti_api_key=self.gti_api_key,
            severity=lowest_severity,
            query_string=query_string,
        )

        response = self.session.get(url)
        self.validate_response(response)

        response_json = response.json()
        if response_json["success"]:
            return (
                self.parser.build_issue_objects(response_json["result"]["hits"]),
                response_json["result"]["more"],
            )

        self.siemplify_logger.error(
            f"Failed to fetch issues - {response_json['message']}"
        )
        return ([], False)

    def search_asm_issues_by_page(self, query_string, page_number, entity_names):
        """
        Searches issues that match query string criteria and returns specified page results.

        Params:
            :param query_string: {str} criteria to search for entities.
            :param page_number: {str} result page_number to fetch.
            :param entity_names: List[str] provided entity names

        Returns:
            Tuple(Hits {List[obj]}, More {bool})
        """
        if self.project_id:
            self.session.headers.update({"PROJECT-ID": self.project_id})
        self.session.params = {"page_size": DEFAULT_PAGE_SIZE, "page": page_number}
        url = self._get_full_url(
            api_root=self.api_root,
            endpoint_id="search_entities",
            gti_api_key=self.gti_api_key,
            query_string=query_string,
        )

        response = self.session.get(url)
        self.validate_response(
            response, error_msg="Failed to fetch issues from Mandiant - ASM. Reason:"
        )
        response_json = response.json()
        if response_json["success"]:
            entity_names = [name.lower() for name in entity_names]
            if entity_names:
                results = [
                    hit
                    for hit in response_json["result"]["hits"]
                    if sanitize_identifiers([hit["name"].lower()])[0] in entity_names
                ]
            else:
                results = response_json["result"]["hits"]
            return (
                self.parser.build_asm_entity_objects(results),
                response_json["result"]["more"],
            )

        self.siemplify_logger.error(
            f"Failed to fetch issues - {response_json['message']}"
        )
        return ([], False)

    def update_issue(self, issue_id: str, issue_status: str):
        """
        Updates issue in ASM with new status.
        :param issue_id: {str} issue id to update in ASM
        :param issue_status: {str} new issue status
        """
        if self.project_id:
            self.session.headers.update({"PROJECT-ID": self.project_id})

        data = {"status": ISSUE_STATUS_MAPPING[issue_status]}
        url = self._get_full_url(
            api_root=self.api_root,
            endpoint_id="update_issue",
            gti_api_key=self.gti_api_key,
            issue_id=issue_id,
        )

        response = self.session.post(url, json=data)
        self.validate_response(response)
        response_json = response.json()

        if not response_json["success"]:
            raise Exception(response_json["message"])

        return response_json

    def get_issue_by_id(self, issue_id):
        """
        Fetches details of a. given issue id.
        :param issue_id: {str} issue if to fetch details of
        """
        if self.project_id:
            self.session.headers.update({"PROJECT-ID": self.project_id})
        url = self._get_full_url(
            api_root=self.api_root,
            endpoint_id="get_issue_details",
            gti_api_key=self.gti_api_key,
            issue_id=issue_id,
        )

        response = self.session.get(url)
        self.validate_response(response)
        response_json = response.json()

        if not response_json["success"]:
            raise MandiantManagerException(response_json["message"])

        return self.parser.build_issue_object(response_json["result"])

    @staticmethod
    def build_asm_query_string(
        names, tags, minimum_vulns, minimum_issues, critical_or_high
    ):
        query_string = ""
        if names:
            sanitized_names = sanitize_identifiers(names)
            for name in sanitized_names:
                query_string += f'name:"{name}" '
        if tags:
            for tag in tags:
                query_string += f'tag:"{tag}" '
        if critical_or_high:
            query_string += f"critical_or_high:true "
        if minimum_vulns:
            query_string += f"vuln_count_gte:{minimum_vulns} "
        if minimum_issues:
            query_string += f"issue_count_gte:{minimum_issues} "
        if query_string:
            return query_string
        else:
            return "last_seen_after:last_refresh"

    def search_asm_entities(
        self, limit: int, script_starting_time: int, execution_deadline: int, **kwargs
    ):
        """
        Searches ASM entities that match specified criteria up to limit.

        Params:
            :param limit: {int} Limitation of how much issues to fetch
            :param script_starting_time: {int} Script starting time
            :param execution_deadline: {int} Execution deadline
            :param kwargs: {Dict[str, Any]} the dictionary that contains all kwargs params specified for filtering,
                check build_query_string for details.

        Returns:
            Tuple(Hits {List[obj]}, More {bool})
        """
        page_number = 0
        filtered_issues = []

        names = kwargs.get("entity_name", [])
        query_string = self.build_asm_query_string(
            names=names,
            critical_or_high=kwargs.get("critical_or_high"),
            tags=kwargs.get("tags"),
            minimum_vulns=kwargs.get("vuln_count_gte"),
            minimum_issues=kwargs.get("issue_count_gte"),
        )

        self.siemplify_logger.info(
            f"Searching ASM entities in {INTEGRATION_DISPLAY_NAME}"
        )

        while True:
            if is_approaching_timeout(script_starting_time, execution_deadline):
                self.siemplify_logger.info(
                    "Timeout is approaching. Action will gracefully exit"
                )
                break

            issues, more_pages = self.search_asm_issues_by_page(
                query_string=query_string,
                page_number=page_number,
                entity_names=sanitize_identifiers(names) if names else [],
            )
            filtered_issues.extend(issues)

            if len(filtered_issues) >= limit or not more_pages:
                self.siemplify_logger.info(
                    f"Reached Maximum count of entities to process of {limit} !"
                )
                break

            page_number += 1

        return filtered_issues[:limit]

    def get_asm_entity_by_id(self, entity_id):
        """
        Fetches details of a given entity id.

        Args:
            entity_id: {str} entity id to fetch details of

        Returns:
            datamodels.ASMEntity
        """
        if self.project_id:
            self.session.headers.update({"PROJECT-ID": self.project_id})
        url = self._get_full_url(
            api_root=self.api_root,
            endpoint_id="entity_full_details",
            gti_api_key=self.gti_api_key,
            entity_id=entity_id,
        )

        response = self.session.get(url)
        self.validate_response(response)
        response_json = response.json()

        if not response_json["success"]:
            raise MandiantManagerException(response_json["message"])

        return self.parser.build_asm_entity_object(response_json.get("result", {}))

    def get_issues(self, severity: int, limit: int, first_seen_after: str):
        """
        Fetches a list of issues from ASM.

        Args:
            severity: lowest severity to fetch
            limit: max issues to fetch
            first_seen_after: reference time to fetch events

        Returns:
            List of Issue objects
        """
        if self.project_id:
            self.session.headers.update({"PROJECT-ID": self.project_id})
        if not severity:
            severity = ""
        page_number = 0
        page_size = max(100, limit)
        params = {"page_size": page_size, "page": page_number}
        url = self._get_full_url(
            api_root=self.api_root,
            endpoint_id="get_issues",
            gti_api_key=self.gti_api_key,
            first_seen_after=first_seen_after,
            severity=severity,
        )
        response = self.session.get(url, params=params)
        self.validate_response(
            response, error_msg="Failed to fetch issues from Mandiant - ASM. Reason:"
        )
        response_json = response.json()
        results = (
            response_json.get("result", {}).get("hits", [])
            if response_json.get("success")
            else []
        )
        has_more = response_json.get("more", False)

        while has_more:
            if len(results) >= limit:
                break

            page_number += 1
            params.update({"page": page_number})
            response = self.session.get(url, params=params)
            self.validate_response(
                response,
                error_msg="Failed to fetch issues from Mandiant - ASM. Reason:",
            )
            response_json = response.json()
            results.extend(
                response_json.get("result", {}).get("hits", [])
                if response_json.get("success")
                else []
            )
            has_more = response_json.get("more", False)

        issues = [
            self.parser.build_connector_issue_object(issue_json)
            for issue_json in results
        ]
        return sorted(issues, key=lambda alert: alert.first_seen)

    def get_issue_details(self, issue_id: str):
        """
        Fetches details of a given issue id

        Args:
            issue_id: issue id to fetch details of

        Returns:
            datamodels.Issue object
        """
        if self.project_id:
            self.session.headers.update({"PROJECT-ID": self.project_id})
        url = self._get_full_url(
            api_root=self.api_root,
            endpoint_id="get_issue_details",
            gti_api_key=self.gti_api_key,
            issue_id=issue_id,
        )
        response = self.session.get(url)
        self.validate_response(
            response,
            error_msg="Failed to fetch issue details from Mandiant - ASM. Reason:",
        )

        response_json = response.json()
        if not response_json["success"]:
            raise Exception(
                f"Failed to fetch details of issue {issue_id} - {response_json['message']}"
            )

        return self.parser.build_connector_issue_object(response_json.get("result", {}))
