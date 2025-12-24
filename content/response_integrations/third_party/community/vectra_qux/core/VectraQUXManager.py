from __future__ import annotations

import time
import urllib.parse
from datetime import datetime

import requests
from soar_sdk.SiemplifyUtils import utc_now

from .constants import (
    ADD_NOTE_API_NAME,
    ADD_OUTCOME_API_NAME,
    ASSIGN_ENTITY_API_NAME,
    ASSIGNMENT_API_NAME,
    DEFAULT_PAGE_SIZE,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_RESULTS_LIMIT,
    DESCRIBE_DETECTION_API_NAME,
    DESCRIBE_ENTITY_API_NAME,
    DOWANLOAD_PCAP_API_NAME,
    ENDPOINTS,
    ENTITY_SEARCH_API_NAME,
    GROUP_TYPE_FIELD_MAPPING,
    LIST_ASSIGNMENTS_API_NAME,
    LIST_ENTITY_DETECTIONS_API_NAME,
    LIST_GROUPS_API_NAME,
    LIST_HOSTS_API_NAME,
    LIST_OUTCOMES_API_NAME,
    LIST_USERS_API_NAME,
    MARK_DETECTION_API_NAME,
    NEXT_PAGE_URL_KEY,
    RATE_LIMIT_EXCEEDED_STATUS_CODE,
    REMOVE_NOTE_API_NAME,
    RESOLVE_ASSIGNMENT_API_NAME,
    RETRY_COUNT,
    SEARCH_ACCOUNTS_API_NAME,
    SEARCH_DETECTIONS_API_NAME,
    SEARCH_HOSTS_API_NAME,
    TAGGING_API_NAME,
    UPDATE_GROUP_MEMBERS_API_NAME,
    VECTRA_DATETIME_FORMAT,
    WAIT_TIME_FOR_RETRY,
)
from .UtilsManager import HandleExceptions, get_alert_id
from .VectraQUXExceptions import FileNotFoundException, RateLimitException
from .VectraQUXParser import VectraQUXParser


class VectraQUXManager:
    def __init__(self, api_root, api_token, verify_ssl=False, siemplify=None):
        """Initializes an object of the VectraQUXManager class.

        Args:
            api_root (str): API root of the VectraQUX server.
            api_token (str): API token of the VectraQUX account.
            verify_ssl (bool, optional): If True, verify the SSL certificate for the connection.
                Defaults to False.
            siemplify (object, optional): An instance of the SDK SiemplifyConnectorExecution class.
                Defaults to None.

        """
        self.api_root = api_root
        self.api_token = api_token
        self.siemplify = siemplify
        self.parser = VectraQUXParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.content_type = "application/json"
        self.session.headers.update(
            {
                "Authorization": f"Token {self.api_token}",
                "Content-Type": self.content_type,
                "User-agent": "qux-google-csoar-v1.0.0",
            },
        )

    def _get_full_url(self, url_id, **kwargs):
        """Get full URL from URL identifier.

        Args:
            url_id (str): The ID of the URL.
            kwargs (dict): Variables passed for string formatting.

        Returns:
            str: The full URL.

        """
        return urllib.parse.urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def _paginator(
        self,
        api_name,
        method,
        url,
        result_key="results",
        params=None,
        body=None,
        limit=DEFAULT_RESULTS_LIMIT,
        is_connector_request=False,
    ):
        """Paginate the results.

        Args:
            api_name (str): API name.
            method (str): The method of the request (GET, POST, PUT, DELETE, PATCH).
            url (str): The URL to send the request to.
            result_key (str, optional): The key to extract data. Defaults to "results".
            params (dict, optional): The parameters of the request.
            body (dict, optional): The JSON payload of the request.
            limit (int, optional): The limit of the results. Defaults to DEFAULT_RESULTS_LIMIT.

        Returns:
            list: List of results.

        """
        limit = limit or DEFAULT_RESULTS_LIMIT
        params["page"] = params.get("page", 1)
        params["page_size"] = min(DEFAULT_PAGE_SIZE, limit)
        response = self._make_rest_call(api_name, method, url, params=params, body=body)
        results = response.get(result_key, [])

        while True:
            if not response.get(NEXT_PAGE_URL_KEY) or len(results) >= limit:
                break
            remaining = limit - len(results)
            params["page"] = params["page"] + 1
            params["page_size"] = min(DEFAULT_PAGE_SIZE, remaining)
            if is_connector_request:
                try:
                    response = self._make_rest_call(
                        api_name,
                        method,
                        url,
                        params=params,
                        body=body,
                    )
                except Exception as e:
                    self.siemplify.LOGGER.exception(e)
                    return results
            else:
                response = self._make_rest_call(
                    api_name,
                    method,
                    url,
                    params=params,
                    body=body,
                )
            results.extend(response.get(result_key, []))

        return results

    def _make_rest_call(
        self,
        api_name,
        method,
        url,
        params=None,
        body=None,
        retry_count=RETRY_COUNT,
    ):
        """Make a rest call to the VectraQUX.

        Args:
            api_name (str): API name.
            method (str): The method of the request (GET, POST, etc.).
            url (str): The URL to send the request to.
            params (dict, optional): The parameters of the request. Defaults to None.
            body (dict, optional): The JSON payload of the request. Defaults to None.
            retry_count (int, optional): The number of retries in case of rate limit.
                Defaults to RETRY_COUNT.

        Returns:
            dict: The JSON response from the API.

        Raises:
            RateLimitException: If the API rate limit is exceeded.

        """
        response = self.session.request(
            method,
            url,
            params=params,
            json=body,
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
        try:
            self.validate_response(api_name, response)
        except RateLimitException:
            if retry_count > 0:
                time.sleep(WAIT_TIME_FOR_RETRY)
                retry_count -= 1
                return self._make_rest_call(
                    api_name,
                    method,
                    url,
                    params,
                    body,
                    retry_count,
                )
            raise RateLimitException("API rate limit exceeded.")
        try:
            if api_name == DOWANLOAD_PCAP_API_NAME:
                return response
            return response.json()
        except Exception:
            self.siemplify.LOGGER.error(
                "Ecxeption occure while returning response json",
            )
            return {}

    @staticmethod
    def validate_response(api_name, response, error_msg="An error occurred"):
        """Validate the response from the API.

        Args:
            api_name (str): API name.
            response (requests.Response): The response object.
            error_msg (str, optional): The error message to display. Defaults to "An error occurred"

        Returns:
            bool: True if the response is valid, raises an exception otherwise.

        Raises:
            RateLimitException: If the API rate limit is exceeded.

        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            if response.status_code == RATE_LIMIT_EXCEEDED_STATUS_CODE:
                raise RateLimitException("API rate limit exceeded.")

            HandleExceptions(api_name, error, response, error_msg).do_process()

        return True

    def test_connectivity(self):
        """Test connectivity to the VectraQUX.

        Returns:
            bool: True if successful, exception otherwise.

        """
        request_url = self._get_full_url(LIST_HOSTS_API_NAME)
        _ = self._make_rest_call(LIST_HOSTS_API_NAME, "GET", request_url)
        return True

    def describe_detection(self, detection_id):
        """Describes a detection.

        Args:
            detection_id (str): The id of the detection.

        Returns:
            Detection: A Detection object with the details of the detection.

        """
        request_url = self._get_full_url(
            DESCRIBE_DETECTION_API_NAME,
            detection_id=detection_id,
        )
        response = self._make_rest_call(DESCRIBE_DETECTION_API_NAME, "GET", request_url)

        return self.parser.build_detection_object(response)

    def describe_entity(self, entity_id, entity_type):
        """Retrieves an entity from VectraQUX.

        Args:
            entity_id (str): The ID of the entity to retrieve.
            entity_type (str): The type of the entity to retrieve.

        Returns:
            dict: The entity object.

        Raises:
            VectraQUXException: If the API returns an error.

        """
        request_url = self._get_full_url(
            DESCRIBE_ENTITY_API_NAME,
            entity_type=entity_type + "s",
            entity_id=entity_id,
        )
        response = self._make_rest_call(DESCRIBE_ENTITY_API_NAME, "GET", request_url)

        return self.parser.build_entity_object(response, entity_type)

    def list_entity_detections(self, entity_id, entity_type, limit, state="active"):
        """Retrieves a list of detections for a given entity.

        Args:
            entity_id (str): The ID of the entity to retrieve detections for.
            entity_type (str): The type of the entity to retrieve detections for.
            limit (int): The maximum number of detections to return.
            state (str): The state of the detections to retrieve, default is "active",
                if not provided, all detections will be retrieved.

        Returns:
            list: A list of Detection objects representing the detections for the given entity.

        Raises:
            VectraQUXException: If the API returns an error.

        """
        request_url = self._get_full_url(LIST_ENTITY_DETECTIONS_API_NAME)
        src_field = "src_linked_account" if entity_type == "account" else "src_host"
        params = {
            "query_string": f'detection.{src_field}.id:{entity_id} AND detection.state:"{state}"',
        }

        response = self._paginator(
            LIST_ENTITY_DETECTIONS_API_NAME,
            "GET",
            request_url,
            limit=limit,
            params=params,
        )

        response_list = [self.parser.build_detection_object(res) for res in response]
        return response_list

    def get_assignment_list(self, query_params, max_assignment_to_return):
        """Get a list of assignments based on specified query parameters and up to a specified limit.

        Args:
            query_params (dict): The query parameters to filter the assignments.
            max_assignment_to_return (int): The maximum number of assignments to return.

        Returns:
            tuple: A tuple containing the list of Assignment objects and the raw response data.

        """
        request_url = self._get_full_url(LIST_ASSIGNMENTS_API_NAME)
        response = self._paginator(
            LIST_ASSIGNMENTS_API_NAME,
            "GET",
            request_url,
            limit=max_assignment_to_return,
            params=query_params,
        )

        proceeded_data = []
        for data in response:
            proceeded_data.append(self.parser.build_assignment_object(data))

        return proceeded_data, response

    def get_entity_tags(self, entity_id, entity_type):
        """Retrieves a list of tags for a given entity.

        Args:
            entity_id (int): The ID of the entity.
            entity_type (str): The type of the entity (e.g. host, account).

        Returns:
            list: A list of tags associated with the entity.

        """
        request_url = self._get_full_url(
            TAGGING_API_NAME,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        response = self._make_rest_call(TAGGING_API_NAME, "GET", request_url)

        return response.get("tags", None)

    def update_tags(self, entity_type, entity_id, entity_tags):
        """Updates the tags for a given entity.

        Args:
            entity_type (str): The type of the entity (e.g. host, account).
            entity_id (int): The ID of the entity.
            entity_tags (list): A list of tags to associate with the entity.

        Returns:
            json: Response of the update tags operation.

        """
        request_url = self._get_full_url(
            TAGGING_API_NAME,
            entity_type=entity_type,
            entity_id=entity_id,
        )

        payload = {"tags": entity_tags}
        response = self._make_rest_call(
            TAGGING_API_NAME,
            "PATCH",
            request_url,
            body=payload,
        )

        return response

    def search_hosts(self, limit, **kwargs):
        """Searches for hosts in VectraQUX.

        Args:
            limit (int): The limit of the number of results.

        Keyword Args:
            **kwargs: The action parameters to filter by.

        Returns:
            list: A list of Host objects representing the search results.

        """
        request_url = self._get_full_url(SEARCH_HOSTS_API_NAME)
        params = {
            action_parameter: action_parameter_value
            for action_parameter, action_parameter_value in kwargs.items()
            if action_parameter_value
        }
        response = self._paginator(
            SEARCH_HOSTS_API_NAME,
            "GET",
            request_url,
            params=params,
            limit=limit,
        )
        return response

    def search_accounts(self, limit, **kwargs):
        """Searches for accounts in VectraQUX.

        Args:
            limit (int): The limit of the number of results.

        Keyword Args:
            **kwargs: The action parameters to filter by.

        Returns:
            list: A list of Account objects representing the search results.

        """
        request_url = self._get_full_url(SEARCH_ACCOUNTS_API_NAME)
        params = {
            action_parameter: action_parameter_value
            for action_parameter, action_parameter_value in kwargs.items()
            if action_parameter_value
        }
        response = self._paginator(
            SEARCH_ACCOUNTS_API_NAME,
            "GET",
            request_url,
            params=params,
            limit=limit,
        )
        return response

    def get_user_list(self, limit, **kwargs):
        """Retrieves a list of users from the VectraQUX.

        Args:
            limit (int): The maximum number of results to return.

        Keyword Args:
            **kwargs: Additional keyword arguments to be passed as query parameters to the API.

        Returns:
            List[User]: A list of User objects representing the users in the VectraQUX.

        """
        request_url = self._get_full_url(LIST_USERS_API_NAME)

        params = {
            action_parameter: action_parameter_value
            for action_parameter, action_parameter_value in kwargs.items()
            if action_parameter_value
        }

        response = self._paginator(
            LIST_USERS_API_NAME,
            "GET",
            request_url,
            params=params,
            limit=limit,
        )

        user_objects = []
        for user in response:
            user_objects.append(self.parser.build_user_object(user))

        return user_objects, response

    def get_group_list(self, limit, group_type, **kwargs):
        """Get a list of groups from VectraQUX.

        Args:
            limit (int): The number of results to return.
            **kwargs: Additional parameters to pass to the API.

        Returns:
            list: List of Group objects.

        Raises:
            RateLimitException: If the API rate limit is exceeded.

        """
        request_url = self._get_full_url(LIST_GROUPS_API_NAME)
        params = {
            action_parameter: action_parameter_value
            for action_parameter, action_parameter_value in kwargs.items()
            if action_parameter_value and action_parameter_value != "None"
        }

        if group_type != "None":
            params["type"] = group_type
        response = self._paginator(
            LIST_GROUPS_API_NAME,
            "GET",
            request_url,
            params=params,
            limit=limit,
        )
        group_objects = []
        for group in response:
            group_objects.append(self.parser.build_group_object(group))
        return group_objects, response

    def describe_assignment(self, assignment_id):
        """Describes a assignment.

        Args:
            assignment_id (str): The id of the assignment.

        Returns:
            Assignment: A Assignment object with the details of the assignment.

        """
        request_url = self._get_full_url(
            ASSIGNMENT_API_NAME,
            assignment_id=assignment_id,
        )
        response = self._make_rest_call(ASSIGNMENT_API_NAME, "GET", request_url)

        data = response.get("assignment")
        proceeded_data = self.parser.build_assignment_object(data)
        return response, proceeded_data

    def get_outcome_list(self, max_outcome_to_return):
        """Get a list of outcomes up to a specified limit.

        Args:
            max_outcome_to_return (int): The maximum number of outcomes to return.

        Returns:
            tuple: A tuple containing the list of Outcome objects and the raw response data.

        """
        request_url = self._get_full_url(LIST_OUTCOMES_API_NAME)
        response = self._paginator(
            LIST_OUTCOMES_API_NAME,
            "GET",
            request_url,
            limit=max_outcome_to_return,
            params={},
        )

        # Convert the raw data to Outcome objects
        proceeded_data = []
        for data in response:
            proceeded_data.append(self.parser.build_outcome_object(data))

        return proceeded_data, response

    def add_outcome(self, title, category):
        """Adds a new outcome to VectraQUX.

        Args:
            title (str): The title of the outcome.
            category (str): The category of the outcome.

        Returns:
            Outcome: A Outcome object with the details of the outcome.

        """
        request_url = self._get_full_url(ADD_OUTCOME_API_NAME)
        payload = {"title": title, "category": category}
        response = self._make_rest_call(
            ADD_OUTCOME_API_NAME,
            "POST",
            request_url,
            body=payload,
        )

        return self.parser.build_outcome_object(response)

    def resolve_assignment(
        self,
        assignment_id,
        outcome_id,
        note_title="",
        triage_as="",
        detection_ids="",
    ):
        """Resolve assignment

        Args:
            assignment_id (str): The ID of the assignment to resolve.
            outcome_id (str): The outcome ID for the assignment resolution.
            note_title (str, optional): Title of the note associated with the resolution.
                Defaults to None.
            triage_as (str, optional): The triage status. Defaults to None.
            detection_ids (list, optional): List of detection IDs associated with the resolution.
                Defaults to None.

        Returns:
            dict: Contains assignment object

        """
        # Replace "" with None, only when the value is not being used.
        request_data = {
            key: value
            for key, value in {
                "outcome": outcome_id,
                "note": note_title if note_title != "" else None,
                "triage_as": triage_as if triage_as != "" else None,
                "detection_ids": detection_ids if detection_ids != "" else None,
            }.items()
            if value not in [None, ""]
        }

        request_url = self._get_full_url(
            RESOLVE_ASSIGNMENT_API_NAME,
            assignment_id=assignment_id,
        )
        response = self._make_rest_call(
            RESOLVE_ASSIGNMENT_API_NAME,
            "PUT",
            request_url,
            body=request_data,
        )
        data = response.get("assignment")
        proceeded_data = self.parser.build_assignment_object(data, note_title)
        return response, proceeded_data

    def mark_detection_as_fixed(self, detection_list_id):
        """Mark Detection As Fixed.

        Args:
            detection_list_id (list) : list of Detection IDs.

        Returns:
            json: Response of the Marked Detection Fixed.

        """
        request_data = {"detectionIdList": detection_list_id, "mark_as_fixed": "True"}

        request_url = self._get_full_url(MARK_DETECTION_API_NAME)
        response = self._make_rest_call(
            MARK_DETECTION_API_NAME,
            "PATCH",
            request_url,
            body=request_data,
        )

        return response

    def remove_assignment(self, assignment_id):
        """Remove assignment from entity

        Args:
            assignment_id (str): The ID of the assignment to remove.

        Returns:
            bool: True if the assignment gets deleted, else false

        """
        request_url = self._get_full_url(
            ASSIGNMENT_API_NAME,
            assignment_id=assignment_id,
        )
        response = self._make_rest_call(ASSIGNMENT_API_NAME, "DELETE", request_url)
        if response == {}:
            return True
        return False

    def update_assignment(self, user_id, assignment_id):
        """Update assignment with user id.

        Args:
            user_id (int): User id.
            assignment_id (int): Assignment id.

        Returns:
            dict: Contains assignment object

        """
        request_data = {"assign_to_user_id": user_id}

        request_url = self._get_full_url(
            ASSIGNMENT_API_NAME,
            assignment_id=assignment_id,
        )
        response = self._make_rest_call(
            ASSIGNMENT_API_NAME,
            "PUT",
            request_url,
            body=request_data,
        )

        data = response.get("assignment")
        proceeded_data = self.parser.build_assignment_object(data)
        return response, proceeded_data

    def unmark_detection_as_fixed(self, detection_list_id):
        """Unmark Detection As Fixed.

        Args:
            detection_list_id (list) : list of detection IDs.

        Returns:
            json: Response of the unmarked detection fixed.

        """
        request_data = {"detectionIdList": detection_list_id, "mark_as_fixed": "False"}

        request_url = self._get_full_url(MARK_DETECTION_API_NAME)
        response = self._make_rest_call(
            MARK_DETECTION_API_NAME,
            "PATCH",
            request_url,
            body=request_data,
        )

        return response

    def add_note(self, entity_type, entity_id, note):
        """Adds a note to an entity.

        Args:
            entity_type (str): The type of the entity.
            entity_id (str): The ID of the entity.
            note (str): The note to add.

        Returns:
            dict: The entity object.

        """
        request_url = self._get_full_url(
            ADD_NOTE_API_NAME,
            entity_type=entity_type + "s",
            entity_id=entity_id,
        )
        response = self._make_rest_call(
            ADD_NOTE_API_NAME,
            "POST",
            request_url,
            body={"note": note},
        )

        return self.parser.build_note_object(response)

    def remove_note(self, entity_type, entity_id, note_id):
        """Removes a note from an entity.

        Args:
            entity_type (str): The type of the entity.
            entity_id (str): The ID of the entity.
            note_id (str): The ID of the note to remove.

        Returns:
            Returns empty response

        """
        request_url = self._get_full_url(
            REMOVE_NOTE_API_NAME,
            entity_type=entity_type + "s",
            entity_id=entity_id,
            note_id=note_id,
        )
        response = self._make_rest_call(REMOVE_NOTE_API_NAME, "DELETE", request_url)
        return response

    def search_detections(self, limit, **kwargs):
        """Retrieves a list of Detections of a given type.

        Args:
            limit (int): The maximum number of entities to return.

        Keyword Args:
            **kwargs (dict): Action parameters to filter the detections by.

        Returns:
            list: A list of detections (hosts/accounts) matching the given criteria.

        """
        request_url = self._get_full_url(SEARCH_DETECTIONS_API_NAME)
        params = {
            action_parameter: action_parameter_value
            for action_parameter, action_parameter_value in kwargs.items()
            if action_parameter_value
        }
        response = self._paginator(
            SEARCH_DETECTIONS_API_NAME,
            "GET",
            request_url,
            limit=limit,
            params=params,
        )

        return response

    def assign_entity(self, entity_id, entity_type, user_id):
        """Creates an assignment between a user and an entity.

        Args:
            entity_id (int): The ID of the entity to assign.
            entity_type (str): The type of the entity to assign (e.g. host, account).
            user_id (int): The ID of the user to assign the entity to.

        Returns:
            Assignment: The assignment object representing the assignment of the entity to the user.

        """
        request_body = {
            "assign_to_user_id": user_id,
            f"assign_{entity_type}_id": entity_id,
        }

        request_url = self._get_full_url(ASSIGN_ENTITY_API_NAME)
        response = self._make_rest_call(
            ASSIGN_ENTITY_API_NAME,
            "POST",
            request_url,
            body=request_body,
        )

        return self.parser.build_assignment_object(response.get("assignment"))

    def download_pcap(self, detection_id):
        """Download PCAP file associated with a detection

        Args:
            detection_id (int):  ID of the detection to download PCAP for
        Return:
            content (str): content of PCAP file
            file_name: File Name

        """
        filename = None
        # Construct the request URL by appending the detection ID to the base URL
        request_url = self._get_full_url(
            DOWANLOAD_PCAP_API_NAME,
            detection_id=detection_id,
        )

        # Send a GET request to the request URL and retrieve the response
        # response = self.session.get(url)
        response = self._make_rest_call(DOWANLOAD_PCAP_API_NAME, "GET", request_url)

        # Check if the request was successful
        if response.status_code == 200:
            # Print a success message
            filename = response.headers["Content-Disposition"].split("filename=")[-1]
            self.siemplify.LOGGER.info("File downloaded successfully")
        else:
            # Print an error message with the status code
            self.siemplify.LOGGER.info(
                f"Failed to download file. Status code: {response.status_code}",
            )
            raise FileNotFoundException
        # Return the content of the response and file name
        return response.content, filename

    def update_group_members(self, group_id, members, membership_action="append"):
        """Assigns members to a group.

        Args:
            group_id (int): The id of the group.
            members (list): A list of user ids to be assigned to the group.

        Returns:
            json: The response of the assign group operation.

        Raises:
            RateLimitException: If the API rate limit is exceeded.

        """
        request_url = self._get_full_url(
            UPDATE_GROUP_MEMBERS_API_NAME,
            group_id=group_id,
        )
        params = {"membership_action": membership_action}
        response = self._make_rest_call(
            UPDATE_GROUP_MEMBERS_API_NAME,
            "PATCH",
            request_url,
            params=params,
            body={"members": members},
        )
        return response

    def get_group_members(self, group_id):
        """Retrieves the details of a group.

        Args:
            group_id (int): The id of the group.

        Returns:
            json: The response of the get group details operation.

        Raises:
            RateLimitException: If the API rate limit is exceeded.

        """
        request_url = self._get_full_url(
            UPDATE_GROUP_MEMBERS_API_NAME,
            group_id=group_id,
        )
        response = self._make_rest_call(
            UPDATE_GROUP_MEMBERS_API_NAME,
            "GET",
            request_url,
        )
        members = response.get("members", [])
        group_type = response.get("type")
        group_members = [
            (
                member
                if GROUP_TYPE_FIELD_MAPPING[group_type] == group_type
                else member.get(GROUP_TYPE_FIELD_MAPPING[group_type])
            )
            for member in members
        ]
        return group_members

    def list_entities_by_filters(
        self,
        existing_ids,
        entity_type,
        start_time,
        limit,
        **kwargs,
    ):
        request_url = self._get_full_url(
            ENTITY_SEARCH_API_NAME,
            entity_type=entity_type,
        )
        query_string = self._build_query_string(
            [
                self._build_time_filter(entity_type, start_time),
                self._build_state_filter(entity_type, kwargs.get("user_query")),
                self._build_threat_filter(
                    entity_type,
                    kwargs.get("min_threat_score"),
                    kwargs.get("user_query"),
                ),
                self._build_certainty_filter(
                    entity_type,
                    kwargs.get("min_certainty_score"),
                    kwargs.get("user_query"),
                ),
                self._build_detection_category_filter(
                    entity_type,
                    kwargs.get("detection_category"),
                    kwargs.get("user_query"),
                ),
                self._build_detection_type_filter(
                    entity_type,
                    kwargs.get("detection_type"),
                    kwargs.get("user_query"),
                ),
                self._build_specific_tag_filter(
                    entity_type,
                    kwargs.get("specific_tag"),
                    kwargs.get("user_query"),
                ),
                self._build_partial_tag_filter(
                    entity_type,
                    kwargs.get("partial_tag"),
                    kwargs.get("user_query"),
                ),
                kwargs.get("user_query"),
            ],
        )
        params = {"query_string": query_string, "page": 1}
        while True:
            results = self._paginator(
                ENTITY_SEARCH_API_NAME,
                "GET",
                request_url,
                limit=limit,
                params=params,
            )
            duplicates = []
            entities = [
                self.parser.build_entity_object(entity, entity_type)
                for entity in results
                if not self._is_duplicate(
                    get_alert_id(
                        entity["id"],
                        (
                            entity["last_detection_timestamp"]
                            if entity_type == "account"
                            else entity["last_modified"]
                        ),
                        entity_type,
                    ),
                    existing_ids,
                    duplicates,
                )
            ]
            self.siemplify.LOGGER.info(f"Duplicate entities = {duplicates}")
            if self._are_all_the_records_duplicates(duplicates, results):
                if limit < DEFAULT_PAGE_SIZE:
                    params["page"] = params["page"] + 1
                else:
                    params["page"] = params["page"] + limit // DEFAULT_PAGE_SIZE
                self.siemplify.LOGGER.info(
                    f"All the records are duplicates. Setting page to {params['page']}",
                )
                continue

            return entities

    @staticmethod
    def _is_duplicate(_id, existing_ids, duplicates):
        if _id in existing_ids:
            duplicates.append(_id)
            return True
        return False

    @staticmethod
    def _are_all_the_records_duplicates(duplicates, results):
        if results and len(duplicates) == len(results):
            return True
        return False

    @staticmethod
    def _build_time_filter(entity_type, start_time):
        """Build time filter.
        :param start_time: {int} Timestamp for oldest detection  to fetch.
        :return: {unicode} The query for time filter
        """
        timestamp_field = (
            "last_detection_timestamp" if entity_type == "account" else "last_modified"
        )
        return (
            f"{entity_type}.{timestamp_field}:["
            f"{datetime.utcfromtimestamp(start_time / 1000).strftime(VECTRA_DATETIME_FORMAT)} "
            f"TO {utc_now().strftime(VECTRA_DATETIME_FORMAT)}]"
        )

    @staticmethod
    def _build_state_filter(entity_type, user_query, state="active"):
        """Build state filter.
        :param state: {str} State of the entity.
        :param user_query: {str} user query
        :return: {unicode} The query for state filter
        """
        query_field = f"{entity_type}.state"
        if (user_query and query_field not in user_query) or not user_query:
            return f'{query_field}:"{state}"'
        return ""

    @staticmethod
    def _build_threat_filter(entity_type, threat, user_query):
        """Build threat filter.
        :param threat: {str} min threat score of the entity.
        :param user_query: {str} user query
        :return: {unicode} The query for threat filter
        """
        query_field = f"{entity_type}.threat"
        query = ""
        if threat:
            query = f"{query_field}:>={threat}"
            if user_query and query_field in user_query:
                query = ""

        return query

    @staticmethod
    def _build_certainty_filter(entity_type, certainty, user_query):
        """Build certainty filter.
        :param certainty: {str} min certainty score of the entity.
        :param user_query: {str} user query
        :return: {unicode} The query for threat filter
        """
        query_field = f"{entity_type}.certainty"
        query = ""
        if certainty:
            query = f"{query_field}:>={certainty}"
            if user_query and query_field in user_query:
                query = ""

        return query

    @staticmethod
    def _build_detection_category_filter(entity_type, detection_category, user_query):
        """Build detection category filter.
        :param detection_category: {str} detection category of the entity.
        :param user_query: {str} user query
        :return: {unicode} The query for threat filter
        """
        query_field = f"{entity_type}.detection_summaries.detection_category"
        query = ""
        if detection_category:
            query = f'{query_field}:"{detection_category}"'
            if user_query and query_field in user_query:
                query = ""

        return query

    @staticmethod
    def _build_detection_type_filter(entity_type, detection_type, user_query):
        """Build detection type filter.
        :param detection_type: {str} detection type of the entity.
        :param user_query: {str} user query
        :return: {unicode} The query for threat filter
        """
        query_field = f"{entity_type}.detection_summaries.detection_type"
        query = ""
        if detection_type:
            query = f'{query_field}:"{detection_type}"'
            if user_query and query_field in user_query:
                query = ""
        return query

    @staticmethod
    def _build_specific_tag_filter(entity_type, tag, user_query):
        """Build specific tag filter.
        :param tag: {str} tag of the entity.
        :param user_query: {str} user query
        :return: {unicode} The query for threat filter
        """
        query_field = f"{entity_type}.tags"
        query = ""
        if tag:
            query = f'{query_field}:"{tag}"'
            if user_query and query_field in user_query:
                query = ""

        return query

    @staticmethod
    def _build_partial_tag_filter(entity_type, tag, user_query):
        """Build specific tag filter.
        :param partial tag: {str} tag of the entity.
        :param user_query: {str} user query
        :return: {unicode} The query for threat filter
        """
        query_field = f"{entity_type}.tags"
        query = ""
        if tag:
            query = f"{query_field}:{tag}"
            if user_query and query_field in user_query:
                query = ""
        return query

    @staticmethod
    def _build_query_string(queries):
        """Join filters.
        :param queries: {list} List of queries.
        :return: {unicode} joined query
        """
        return " AND ".join([query for query in queries if query])
