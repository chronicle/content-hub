from __future__ import annotations

import copy
import time
import urllib.parse
from datetime import datetime

import requests
from TIPCommon.DataStream import ConnectorFileStream

from .constants import (
    ADD_NOTE_API_NAME,
    ASSIGN_ENTITY_API_NAME,
    ASSIGNMENT_API_NAME,
    DEFAULT_PAGE_SIZE,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_RESULTS_LIMIT,
    DESCRIBE_DETECTION_API_NAME,
    DESCRIBE_ENTITY_API_NAME,
    DOWNLOAD_PCAP_API_NAME,
    ENDPOINTS,
    FIRST_TIMESTAMP_FORMAT,
    GROUP_TYPE_FIELD_MAPPING,
    LIST_ASSIGNMENTS_API_NAME,
    LIST_DETECTIONS_API_NAME,
    LIST_ENTITIES_API_NAME,
    LIST_ENTITY_API_NAME,
    LIST_GROUPS_API_NAME,
    LIST_OUTCOMES_API_NAME,
    LIST_USERS_API_NAME,
    MARK_DETECTION_API_NAME,
    NEXT_PAGE_URL_KEY,
    PING,
    RATE_LIMIT_EXCEEDED_STATUS_CODE,
    REMOVE_NOTE_API_NAME,
    RESOLVE_ASSIGNMENT_API_NAME,
    RETRY_COUNT,
    RETRY_COUNT_TOKEN,
    TAGGING_API_NAME,
    UPDATE_GROUP_MEMBERS_API_NAME,
    WAIT_TIME_FOR_RETRY,
)
from .UtilsManager import HandleExceptions, get_alert_id
from .VectraRUXExceptions import (
    FileNotFoundException,
    RateLimitException,
    RefreshTokenException,
    UnauthorizeException,
    VectraRUXException,
)
from .VectraRUXParser import VectraRUXParser


class VectraRUXManager:
    def __init__(self, api_root, client_id, client_secret, siemplify=None):
        """Initializes an object of the VectraRUXManager class.

        Args:
            api_root (str): API root of the VectraRUX server.
            client_id (str): API token of the VectraRUX account.
            siemplify (object, optional): An instance of the SDK SiemplifyConnectorExecution class.
                Defaults to None.

        """
        self.api_root = api_root
        self.client_id = client_id
        self.client_secret = client_secret
        self.siemplify = siemplify
        self.parser = VectraRUXParser()
        self.session = requests.session()
        self.access_token = None
        self.refresh_token = None
        self.content_type = "application/json"
        self.session.headers = {
            "Content-Type": self.content_type,
            "User-agent": "rux-google-csoar-v1.0.0",
        }
        self.file_name = self.client_id[:5]
        self.file_manager = ConnectorFileStream(
            file_name=f"{self.file_name}.json",
            siemplify=siemplify,
        )
        self.stored_client_id = None
        self.api_rate_exception = "API rate limit exceeded."
        self.generate_token()

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
        retry_count_token=RETRY_COUNT_TOKEN,
        **kwargs,
    ):
        """Make a reset call to the VectraRUX.

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
            data=body,
            timeout=DEFAULT_REQUEST_TIMEOUT,
            **kwargs,
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
                    **kwargs,
                )
            raise RateLimitException(self.api_rate_exception)
        except UnauthorizeException as e:
            if retry_count_token > 0:
                self.siemplify.LOGGER.exception(
                    f"Exception occure - {e}. Hence, Generating new tokens.",
                )
                self.generate_token(using_refresh_token=True)
                retry_count_token -= 1
                return self._make_rest_call(
                    api_name,
                    method,
                    url,
                    params,
                    body,
                    retry_count,
                    retry_count_token,
                    **kwargs,
                )
            raise UnauthorizeException(e)
        try:
            if api_name == DOWNLOAD_PCAP_API_NAME:
                return response
            return response.json()
        except Exception:
            self.siemplify.LOGGER.exception(
                "Exception occure while returning response json",
            )
            return {}

    def _make_rest_call_token(
        self,
        api_name,
        method,
        url,
        params=None,
        body=None,
        retry_count=RETRY_COUNT,
        **kwargs,
    ):
        """Make a reset call to the VectraRUX.

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
        response = self.session.request(method, url, params=params, data=body, **kwargs)
        try:
            self.validate_response(api_name, response)
        except RateLimitException:
            if retry_count > 0:
                time.sleep(WAIT_TIME_FOR_RETRY)
                retry_count -= 1
                return self._make_rest_call_token(
                    api_name,
                    method,
                    url,
                    params,
                    body,
                    retry_count,
                    **kwargs,
                )
            raise RateLimitException(self.api_rate_exception)
        except RefreshTokenException as e:
            raise RefreshTokenException(
                f"Failed to generate token using refresh token. Error - {e}",
            )
        except UnauthorizeException:
            raise UnauthorizeException(
                "Provided Credentials are not valid!. Please verify provided credentials.",
            )

        return response.json()

    def generate_token(
        self,
        test_connectivity=False,
        using_refresh_token=False,
        using_client_credentials=False,
    ):
        """Generate token for the VectraRUX.

        Returns:
            exception if failed else set access_token into header.

        """
        try:
            self.siemplify.LOGGER.info("Reading stored tokens")
            self.tokens = self.file_manager.read_content(
                default_value_to_return=None,
            )
            if self.tokens and not test_connectivity:
                self.siemplify.LOGGER.info("Generating tokens using stored token")
                self.access_token = self.tokens.get("access_token", None)
                self.refresh_token = self.tokens.get("refresh_token", None)
                self.stored_client_id = self.tokens.get("client_id", None)

                # Below conditions are check if token is present or not and
                # set variables accordingly
                if not self.access_token:
                    if self.refresh_token:
                        using_refresh_token = True
                    else:
                        using_client_credentials = True
                if self.stored_client_id and self.stored_client_id != self.client_id:
                    self.siemplify.LOGGER.info(
                        "It seems provided client ID and stored client ID not matching. Hence, Removing stored token and try with provided credentials",
                    )
                    # Removing stored token
                    self.file_manager.write_content(
                        content_to_write={},
                        default_value_to_set=None,
                    )
                    using_refresh_token = False
                    using_client_credentials = True
                if using_client_credentials or using_refresh_token:
                    self.session.headers.pop("Authorization", "Key not found")
                    self.session.headers.update(
                        {
                            "Content-Type": "application/x-www-form-urlencoded",
                        },
                    )
                    request_url = self._get_full_url(PING)
                    if using_refresh_token:
                        if self.refresh_token:
                            self.siemplify.LOGGER.info(
                                "Generating token using refresh token",
                            )
                            body = {
                                "grant_type": "refresh_token",
                                "refresh_token": f"{self.refresh_token}",
                            }
                            response = self._make_rest_call_token(
                                PING,
                                "POST",
                                request_url,
                                body=body,
                            )
                        else:
                            self.siemplify.LOGGER.info(
                                "Refresh token is not present. Hence, going with creds",
                            )
                            using_client_credentials = True
                    if using_client_credentials:
                        auth = (self.client_id, self.client_secret)
                        body = "grant_type=client_credentials"
                        self.siemplify.LOGGER.info(
                            "Generating token using client credentials",
                        )
                        response = self._make_rest_call_token(
                            PING,
                            "POST",
                            request_url,
                            body=body,
                            auth=auth,
                        )

                    self.access_token = response.get("access_token")
                    self.refresh_token = response.get("refresh_token")
                    if self.access_token:
                        self.session.headers.update(
                            {"Authorization": f"Bearer {self.access_token}"},
                        )

                        response["client_id"] = self.client_id
                        # We tring to add tokens into file
                        self.file_manager.write_content(
                            content_to_write=response,
                            default_value_to_set=None,
                        )

                        self.tokens = self.file_manager.read_content(
                            default_value_to_return=None,
                        )

                        self.siemplify.LOGGER.info(
                            f"Successfully written token into file using client credentials. Filename - {self.file_name}.json",
                        )
                else:
                    self.siemplify.LOGGER.info("Using stroed access token")
                    self.session.headers.update(
                        {"Authorization": f"Bearer {self.access_token}"},
                    )
            else:
                self.siemplify.LOGGER.info("Generating token using client credentials")
                request_url = self._get_full_url(PING)
                self.session.headers.update(
                    {
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                auth = (self.client_id, self.client_secret)
                body = "grant_type=client_credentials"
                response = self._make_rest_call_token(
                    PING,
                    "POST",
                    request_url,
                    body=body,
                    auth=auth,
                )
                self.access_token = response.get("access_token")
                self.refresh_token = response.get("refresh_token")
                if self.access_token:
                    self.session.headers.update(
                        {"Authorization": f"Bearer {self.access_token}"},
                    )
                    response["client_id"] = self.client_id
                    # We tring to add tokens into file
                    self.file_manager.write_content(
                        content_to_write=response,
                        default_value_to_set=None,
                    )

                    self.siemplify.LOGGER.info(
                        f"Successfully written token into file using client credentials. Filename - {self.file_name}.json",
                    )
        except RefreshTokenException as e:
            self.siemplify.LOGGER.exception(f"{e!s}")
            self.generate_token(using_client_credentials=True)
        except UnauthorizeException as e:
            raise UnauthorizeException(e)

    def test_connectivity(self):
        try:
            if self.stored_client_id and self.stored_client_id != self.client_id:
                self.generate_token(test_connectivity=True)
        except Exception as e:
            raise VectraRUXException(e)
        return True

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

    def get_assignment_list(self, query_params, max_assignment_to_return):
        """Retrieves a list of assignments based on the provided query parameters.

        Args:
            query_params (dict): A dictionary of query parameters to filter the assignments.
            max_assignment_to_return (int): The maximum number of assignments to return.

        Returns:
            list: A list of assignment objects.

        Note:
            This method uses the LIST_ASSIGNMENTS_API_NAME endpoint and paginates the results if
            necessary.

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

    def describe_detection(self, detection_id):
        """Retrieves a detection object based on the provided detection ID.

        Args:
            detection_id (int): The ID of the detection to retrieve.

        Returns:
            Detection: The detection object.

        Note:
            This method uses the DESCRIBE_DETECTION_API_NAME endpoint to retrieve the detection
            information.

        """
        request_url = self._get_full_url(
            DESCRIBE_DETECTION_API_NAME,
            detection_id=detection_id,
        )
        response = self._make_rest_call(DESCRIBE_DETECTION_API_NAME, "GET", request_url)

        return self.parser.build_detection_object(response)

    def describe_entity(self, entity_id, entity_type):
        """Retrieves an entity object based on the provided entity ID and type.

        Args:
            entity_id (int): The ID of the entity to retrieve.
            entity_type (str): The type of the entity to retrieve.

        Returns:
            Entity: The entity object.

        Note:
            This method uses the DESCRIBE_ENTITY_API_NAME endpoint to retrieve the entity
            information.

        """
        request_url = self._get_full_url(
            DESCRIBE_ENTITY_API_NAME,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        response = self._make_rest_call(DESCRIBE_ENTITY_API_NAME, "GET", request_url)

        return self.parser.build_entity_object(response)

    def list_entity_detections(self, detection_ids, limit, state):
        """Retrieves a list of detection objects based on the provided detection IDs and state.

        Args:
            detection_ids (list): The IDs of the detections to retrieve.
            limit (int): The maximum number of detections to return.
            state (str): The state of the detections to retrieve.

        Returns:
            list: A list of detection objects.

        Note:
            This method uses the LIST_DETECTIONS_API_NAME endpoint to retrieve the detections
            information.

        """
        request_url = self._get_full_url(LIST_DETECTIONS_API_NAME)

        params = {
            "id": ",".join(detection_ids),
        }
        if state != "None":
            params["state"] = state

        response = self._paginator(
            LIST_DETECTIONS_API_NAME,
            "GET",
            request_url,
            limit=limit,
            params=params,
        )
        response_list = [self.parser.build_detection_object(res) for res in response]

        return response_list

    def get_entity_tags(self, entity_id, entity_type):
        """Retrieves a list of tags for a given entity.

        Args:
            entity_id (int): The ID of the entity.
            entity_type (str): The type of the entity (e.g. host, account, detection).

        Returns:
            list: A list of tags associated with the entity.

        """
        request_url = self._get_full_url(TAGGING_API_NAME, entity_id=entity_id)
        params = {"type": entity_type}

        response = self._make_rest_call(
            TAGGING_API_NAME,
            "GET",
            request_url,
            params=params,
        )
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

        params = {"type": entity_type}
        payload = {"tags": entity_tags}

        self.session.headers.update(
            {
                "Content-Type": self.content_type,
            },
        )

        response = self._make_rest_call(
            TAGGING_API_NAME,
            "PATCH",
            request_url,
            params=params,
            json=payload,
        )

        return response

    def list_entities(self, entity_type, limit, **kwargs):
        """Retrieves a list of entities of a given type.

        Args:
            entity_type (str): The type of the entity (e.g. host, account).
            limit (int): The maximum number of entities to return.

        Keyword Args:
            **kwargs (dict): Action parameters to filter the entities by.

        Returns:
            list: A list of entities (hosts/accounts) matching the given criteria.

        """
        request_url = self._get_full_url(LIST_ENTITIES_API_NAME)
        params = {
            action_parameter: action_parameter_value
            for action_parameter, action_parameter_value in kwargs.items()
            if action_parameter_value
        }
        params["type"] = entity_type
        response = self._paginator(
            LIST_ENTITIES_API_NAME,
            "GET",
            request_url,
            limit=limit,
            params=params,
        )

        return response

    def get_user_list(self, limit, **kwargs):
        """Retrieves a list of users from the VectraRUX.

        Args:
            limit (int): The maximum number of results to return.

        Keyword Args:
            **kwargs: Additional keyword arguments to be passed as query parameters to the API.

        Returns:
            List[User]: A list of User objects representing the users in the VectraRUX.

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

        proceeded_data = []
        for data in response:
            proceeded_data.append(self.parser.build_outcome_object(data))

        return proceeded_data, response

    def mark_detection_as_fixed(self, detection_list_id):
        """Marked Detection Fixed.

        Args:
            detection_list_id (list) : list of Detection IDs.

        Returns:
            json: Response of the Marked Detection Fixed.

        """
        request_data = {"detectionIdList": detection_list_id, "mark_as_fixed": "True"}
        request_url = self._get_full_url(MARK_DETECTION_API_NAME)
        self.session.headers.update(
            {
                "Content-Type": self.content_type,
            },
        )
        response = self._make_rest_call(
            MARK_DETECTION_API_NAME,
            "PATCH",
            request_url,
            json=request_data,
        )
        return response

    def get_group_list(self, limit, group_type, **kwargs):
        """Get a list of groups from VectraRUX.

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

    def unmark_detection_as_fixed(self, detection_list_id):
        """Unmark Detection Fixed.

        Args:
            detection_list_id (list) : list of Detection IDs.

        Returns:
            json: Response of the Unmarked Detection Fixed.

        """
        request_data = {"detectionIdList": detection_list_id, "mark_as_fixed": "False"}
        request_url = self._get_full_url(MARK_DETECTION_API_NAME)
        self.session.headers.update(
            {
                "Content-Type": self.content_type,
            },
        )
        response = self._make_rest_call(
            MARK_DETECTION_API_NAME,
            "PATCH",
            request_url,
            json=request_data,
        )

        return response

    def get_specific_entity_info(self, entity_type, entity_id):
        """Get assignment information.

        Args:
            entity_type (str): Entity type.
            entity_id (int): Entity id.

        Returns:
            dict: Response of the assignment information.

        """
        request_url = self._get_full_url(
            LIST_ENTITY_API_NAME,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        response = self._make_rest_call(LIST_ENTITY_API_NAME, "GET", request_url)
        return response

    def remove_assignment(self, assignment_id):
        """Remove assignment from entity

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

    def add_note(self, entity_type, entity_id, note):
        """Adds a note to an entity.

        Args:
            entity_type (str): The type of the entity.
            entity_id (str): The ID of the entity.
            note (str): The note to add.

        Returns:
            dict: The entity object.

        """
        params = {"type": entity_type}
        payload = {"note": note}

        self.session.headers.update(
            {
                "Content-Type": self.content_type,
            },
        )

        request_url = self._get_full_url(ADD_NOTE_API_NAME, entity_id=entity_id)
        response = self._make_rest_call(
            ADD_NOTE_API_NAME,
            "POST",
            request_url,
            params=params,
            json=payload,
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
        params = {"type": entity_type}
        self.session.headers.update(
            {
                "Content-Type": self.content_type,
            },
        )
        request_url = self._get_full_url(
            REMOVE_NOTE_API_NAME,
            entity_id=entity_id,
            note_id=note_id,
        )
        response = self._make_rest_call(
            REMOVE_NOTE_API_NAME,
            "DELETE",
            request_url,
            params=params,
        )

        return response

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
        # Replace " " with None, only when the value is not being used.
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
            json=request_data,
        )
        self.session.headers.update(
            {
                "Content-Type": self.content_type,
            },
        )
        data = response.get("assignment")
        proceeded_data = self.parser.build_assignment_object(data, note_title)

        return response, proceeded_data

    def update_assignment(self, user_id, assignment_id):
        """Update assignment with user ID.

        Args:
            user_id (int): User ID.
            assignment_id (int): Assignment ID.

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
            json=request_data,
        )

        data = response.get("assignment")
        proceeded_data = self.parser.build_assignment_object(data)
        return response, proceeded_data

    def list_detections(self, limit, **kwargs):
        """Retrieves a list of Detections of a given type.

        Args:
            limit (int): The maximum number of entities to return.

        Keyword Args:
            **kwargs (dict): Action parameters to filter the detections by.

        Returns:
            list: A list of detections (hosts/accounts) matching the given criteria.

        """
        request_url = self._get_full_url(LIST_DETECTIONS_API_NAME)
        params = {
            action_parameter: action_parameter_value
            for action_parameter, action_parameter_value in kwargs.items()
            if action_parameter_value
        }
        response = self._paginator(
            LIST_DETECTIONS_API_NAME,
            "GET",
            request_url,
            limit=limit,
            params=params,
        )

        return response

    def assign_entity(self, entity_id, entity_type, user_id):
        """Assigns an entity and user to an assignment.

        Args:
            entity_id (int): The ID of the entity to assign.
            entity_type (str): The type of the entity to assign (e.g. host, account).
            user_id (int): The ID of the user to assign the entity to.

        Returns:
            Assignment: The assignment object.

        Note:
            This method uses the ASSIGN_ENTITY_API_NAME endpoint to assign the entity to the user.

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
            json=request_body,
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
            DOWNLOAD_PCAP_API_NAME,
            detection_id=detection_id,
        )

        # Send a GET request to the request URL and retrieve the response
        # response = self.session.get(url)
        response = self._make_rest_call(DOWNLOAD_PCAP_API_NAME, "GET", request_url)

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
            raise FileNotFoundException("File not found")
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
        payload = {"members": members}
        self.session.headers.update(
            {
                "Content-Type": self.content_type,
            },
        )
        response = self._make_rest_call(
            UPDATE_GROUP_MEMBERS_API_NAME,
            "PATCH",
            request_url,
            params=params,
            json=payload,
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
        is_prioritized,
        specific_tag,
    ):
        """Retrieves a list of entities of a given type."""
        request_url = self._get_full_url(LIST_ENTITIES_API_NAME)
        params = {
            "type": entity_type,
            "last_modified_timestamp_gte": datetime.utcfromtimestamp(
                start_time / 1000,
            ).strftime(FIRST_TIMESTAMP_FORMAT),
            "ordering": "last_modified_timestamp",
            "state": "active",
            "page": 1,
        }
        if is_prioritized:
            params["is_prioritized"] = is_prioritized

        if specific_tag:
            params["tags"] = specific_tag

        new_entities = []
        existing_entities = copy.deepcopy(existing_ids)
        original_limit = limit
        while True:
            try:
                results = self._paginator(
                    LIST_ENTITIES_API_NAME,
                    "GET",
                    request_url,
                    limit=limit,
                    params=params,
                    is_connector_request=True,
                )
            except Exception as e:
                if "Invalid page" in str(e):
                    results = []
                else:
                    raise

            duplicates = []
            entities = [
                self.parser.build_entity_object(entity)
                for entity in results
                if not self._is_duplicate(
                    get_alert_id(
                        entity["id"],
                        entity["last_modified_timestamp"],
                        entity_type,
                    ),
                    existing_entities,
                    duplicates,
                )
            ]
            new_entities.extend(entities)

            if results and duplicates:
                if self._are_all_the_records_duplicates(duplicates, results):
                    if limit < DEFAULT_PAGE_SIZE:
                        params["page"] = params["page"] + 1
                    else:
                        params["page"] = params["page"] + limit // DEFAULT_PAGE_SIZE
                    self.siemplify.LOGGER.info(
                        f"All the records are duplicates. Setting page to {params['page']}",
                    )
                    continue
                self.siemplify.LOGGER.info(f"Found duplicates = {duplicates}")
                params["last_modified_timestamp_gte"] = results[-1][
                    "last_modified_timestamp"
                ]
                limit = original_limit - len(new_entities)
                params["page"] = 1
                continue

            return new_entities

    @staticmethod
    def _is_duplicate(_id, existing_ids, duplicates):
        if _id in existing_ids:
            duplicates.append(_id)
            return True
        existing_ids.add(_id)
        return False

    @staticmethod
    def _are_all_the_records_duplicates(duplicates, results):
        if len(duplicates) == len(results):
            return True
        return False
