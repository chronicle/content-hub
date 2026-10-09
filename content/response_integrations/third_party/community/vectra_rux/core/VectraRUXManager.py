from __future__ import annotations

import copy
import time
import urllib.parse
from datetime import datetime

import requests
from TIPCommon.oauth import CredStorage

from .constants import (
    ADD_NOTE_API_NAME,
    ASSIGN_ENTITY_API_NAME,
    ASSIGNMENT_API_NAME,
    CLOSE_DETECTIONS_API_NAME,
    DEFAULT_PAGE_SIZE,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_RESULTS_LIMIT,
    DESCRIBE_DETECTION_API_NAME,
    DESCRIBE_ENTITY_API_NAME,
    DETECTION_EVENTS_CHECKPOINT_PROPERTY_KEY,
    DETECTION_EVENTS_SIZE,
    DOWNLOAD_PCAP_API_NAME,
    ENDPOINTS,
    FIRST_TIMESTAMP_FORMAT,
    GET_INVESTIGATION_RESULTS_API_NAME,
    GROUP_TYPE_FIELD_MAPPING,
    INVESTIGATION_RESULTS_DATA_KEY,
    LIST_ASSIGNMENTS_API_NAME,
    LIST_DETECTIONS_API_NAME,
    LIST_DETECTION_EVENTS_API_NAME,
    LIST_ENTITIES_API_NAME,
    LIST_ENTITY_API_NAME,
    LIST_ENTITY_DETECTIONS_API_NAME,
    LIST_ENTITY_NOTES_API_NAME,
    LIST_GROUPS_API_NAME,
    LIST_TAGS_API_NAME,
    LIST_USERS_API_NAME,
    NEXT_PAGE_URL_KEY,
    OPEN_DETECTIONS_API_NAME,
    QUERY_INVESTIGATION_API_NAME,
    RATE_LIMIT_EXCEEDED_STATUS_CODE,
    REMOVE_NOTE_API_NAME,
    RETRY_COUNT,
    RETRY_COUNT_TOKEN,
    SET_DETECTION_STATUS_API_NAME,
    SET_DETECTION_TICKET_API_NAME,
    SET_ENTITY_TICKET_API_NAME,
    SET_ENTITY_UNRESOLVED_PRIORITY_API_NAME,
    TAGGING_API_NAME,
    UPDATE_ASSIGNMENT_API_NAME,
    UPDATE_ENTITY_NOTE_API_NAME,
    UPDATE_GROUP_MEMBERS_API_NAME,
    WAIT_TIME_FOR_RETRY,
)
from .UtilsManager import HandleExceptions, generate_encryption_key, get_alert_id, get_detection_alert_id
from .vectra_oauth_adapter import JobCredStorage, VectraOAuthAdapter, VectraOAuthManager
from .VectraRUXExceptions import (
    FileNotFoundException,
    ItemNotFoundException,
    RateLimitException,
    UnauthorizeException,
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
        self.content_type = "application/json"
        self.session.headers = {
            "Content-Type": self.content_type,
            "User-agent": "rux-google-csoar-v1.0.0",
        }
        self.api_rate_exception = "API rate limit exceeded."

        self.oauth_adapter = VectraOAuthAdapter(
            api_root=self.api_root,
            client_id=self.client_id,
            client_secret=self.client_secret,
            verify_ssl=False,
        )
        cred_storage_cls = (
            JobCredStorage
            if hasattr(self.siemplify, "get_scoped_job_context_property")
            else CredStorage
        )
        self.cred_storage = cred_storage_cls(
            encryption_password=generate_encryption_key(self.client_id, self.api_root),
            chronicle_soar=self.siemplify,
        )
        self.oauth_manager = VectraOAuthManager(
            oauth_adapter=self.oauth_adapter,
            cred_storage=self.cred_storage,
        )

        if self.oauth_manager._token_is_expired():
            self.generate_token()
        else:
            self.access_token = self.oauth_manager._token.access_token
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

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
                self.generate_token()
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

    def generate_token(self):
        """Generate and save a new access token for the VectraRUX.

        Uses the stored refresh token when available, otherwise falls back
        to the client credentials grant. The resulting token is saved to
        encrypted storage and applied to the session headers.
        """
        self.siemplify.LOGGER.info("Generating new token")

        stored_token = self.oauth_manager._token
        refresh_token = getattr(stored_token, "refresh_token", None)

        token = self.oauth_adapter.refresh_token(refresh_token=refresh_token)
        self.oauth_manager._token = token
        self.oauth_manager.save_token()

        self.access_token = token.access_token
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

        self.siemplify.LOGGER.info("Token generated and saved successfully")

    def test_connectivity(self):
        """Verify the provided VectraRUX credentials by generating a fresh token.

        Returns:
            bool: True if token generation succeeds, raises an exception otherwise.

        """
        self.generate_token()
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
        params = {"id": detection_id}
        request_url = self._get_full_url(DESCRIBE_DETECTION_API_NAME)
        response = self._paginator(
            DESCRIBE_DETECTION_API_NAME, 
            "GET", 
            request_url, 
            params=params
        )
        
        if not response:
            raise ItemNotFoundException(
                f"Detection with ID {detection_id} not found.",
            )
        detection = response[0]     # Get the detection details
        return self.parser.build_detection_object(detection)

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
        params = {
            "type": entity_type,
            "id": entity_id
        }
        request_url = self._get_full_url(DESCRIBE_ENTITY_API_NAME)
        response = self._paginator(
            DESCRIBE_ENTITY_API_NAME, 
            "GET", 
            request_url, 
            params=params,
        )
        
        if not response:
            raise ItemNotFoundException(
                f"Entity with ID {entity_id} not found.",
            )
        
        entity = response[0]
        return self.parser.build_entity_object(entity)

    def list_entity_detections(self, detection_ids, limit, state):
        """Retrieves a list of detection objects based on the provided detection IDs and state.

        Args:
            detection_ids (list): The IDs of the detections to retrieve.
            limit (int): The maximum number of detections to return.
            state (str): The state of the detections to retrieve.

        Returns:
            list: A list of detection objects.

        Note:
            This method uses the LIST_ENTITY_DETECTIONS_API_NAME endpoint to retrieve the
            detections information.

        """
        request_url = self._get_full_url(LIST_ENTITY_DETECTIONS_API_NAME)

        params = {
            "id": ",".join(detection_ids),
        }
        if state != "None":
            params["state"] = state

        response = self._paginator(
            LIST_ENTITY_DETECTIONS_API_NAME,
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
            if action_parameter_value and action_parameter_value != "None"
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

    def list_entity_notes(self, entity_type, entity_id):
        """Retrieves the list of notes for a given entity.

        Args:
            entity_type (str): The type of the entity.
            entity_id (int): The ID of the entity.

        Returns:
            list: A list of Note objects associated with the entity.

        """
        params = {"type": entity_type}
        request_url = self._get_full_url(LIST_ENTITY_NOTES_API_NAME, entity_id=entity_id)
        response = self._make_rest_call(
            LIST_ENTITY_NOTES_API_NAME,
            "GET",
            request_url,
            params=params,
        )

        return [self.parser.build_note_object(note) for note in response]

    def update_entity_note(self, entity_type, entity_id, note_id, note):
        """Updates an existing note on an entity.

        Args:
            entity_type (str): The type of the entity.
            entity_id (int): The ID of the entity.
            note_id (int): The ID of the note to update.
            note (str): The updated note content.

        Returns:
            dict: The response of the update note operation.

        """
        params = {"type": entity_type}
        payload = {"note": note}

        self.session.headers.update(
            {
                "Content-Type": self.content_type,
            },
        )

        request_url = self._get_full_url(
            UPDATE_ENTITY_NOTE_API_NAME,
            entity_id=entity_id,
            note_id=note_id,
        )
        response = self._make_rest_call(
            UPDATE_ENTITY_NOTE_API_NAME,
            "PATCH",
            request_url,
            params=params,
            json=payload,
        )

        return self.parser.build_note_object(response)

    def list_tags(self, entity_id, entity_type):
        """Retrieves the list of tags for a given entity.

        Args:
            entity_id (int): The ID of the entity.
            entity_type (str): The type of the entity (e.g. host, account, detection).

        Returns:
            list: A list of tags associated with the entity.

        """
        request_url = self._get_full_url(LIST_TAGS_API_NAME, entity_id=entity_id)
        params = {"type": entity_type}

        response = self._make_rest_call(
            LIST_TAGS_API_NAME,
            "GET",
            request_url,
            params=params,
        )

        return response

    def set_entity_unresolved_priority(self, entity_type, entity_id, unresolved_priority):
        """Sets the unresolved priority flag on a given entity.

        Args:
            entity_type (str): The type of the entity.
            entity_id (int): The ID of the entity.
            unresolved_priority (str): The unresolved priority value to set.

        Returns:
            dict: The response of the update operation.

        """
        params = {"type": entity_type}
        payload = {"unresolved_priority": str(unresolved_priority).lower()}

        self.session.headers.update(
            {
                "Content-Type": self.content_type,
            },
        )

        request_url = self._get_full_url(
            SET_ENTITY_UNRESOLVED_PRIORITY_API_NAME,
            entity_id=entity_id,
        )
        response = self._make_rest_call(
            SET_ENTITY_UNRESOLVED_PRIORITY_API_NAME,
            "PATCH",
            request_url,
            params=params,
            json=payload,
        )

        return response

    def set_detection_status(self, detection_ids, investigation_status):
        """Sets the investigation status for the given detection IDs.

        Args:
            detection_ids (list): The list of detection IDs to update.
            investigation_status (str): The investigation status to set.

        Returns:
            dict: The response of the update operation.

        """
        payload = {
            "detectionIdList": detection_ids,
            "investigation_status": investigation_status,
        }

        self.session.headers.update(
            {
                "Content-Type": self.content_type,
            },
        )

        request_url = self._get_full_url(SET_DETECTION_STATUS_API_NAME)
        response = self._make_rest_call(
            SET_DETECTION_STATUS_API_NAME,
            "PATCH",
            request_url,
            json=payload,
        )

        return response

    def close_detections(self, detection_ids, reason):
        """Closes the given detection IDs with the provided reason.

        Args:
            detection_ids (list): The list of detection IDs to close.
            reason (str): The reason for closing the detections.

        Returns:
            dict: The response of the close operation.

        """
        payload = {"detectionIdList": detection_ids, "reason": reason}

        self.session.headers.update(
            {
                "Content-Type": self.content_type,
            },
        )

        request_url = self._get_full_url(CLOSE_DETECTIONS_API_NAME)
        response = self._make_rest_call(
            CLOSE_DETECTIONS_API_NAME,
            "PATCH",
            request_url,
            json=payload,
        )

        return response

    def open_detections(self, detection_ids):
        """Re-opens the given detection IDs.

        Args:
            detection_ids (list): The list of detection IDs to re-open.

        Returns:
            dict: The response of the open operation.

        """
        payload = {"detectionIdList": detection_ids}

        self.session.headers.update(
            {
                "Content-Type": self.content_type,
            },
        )

        request_url = self._get_full_url(OPEN_DETECTIONS_API_NAME)
        response = self._make_rest_call(
            OPEN_DETECTIONS_API_NAME,
            "PATCH",
            request_url,
            json=payload,
        )

        return response

    def set_detection_ticket(self, detection_ids, external_reference_id):
        """Sets the external reference ID for the given detection IDs.

        Args:
            detection_ids (list): The list of detection IDs to update.
            external_reference_id (str): The external reference ID to set.

        Returns:
            dict: The response of the update operation.

        """
        payload = {
            "detectionIdList": detection_ids,
            "external_reference_id": external_reference_id,
        }

        self.session.headers.update(
            {
                "Content-Type": self.content_type,
            },
        )

        request_url = self._get_full_url(SET_DETECTION_TICKET_API_NAME)
        response = self._make_rest_call(
            SET_DETECTION_TICKET_API_NAME,
            "PATCH",
            request_url,
            json=payload,
        )

        return response

    def set_entity_ticket(self, entity_type, entity_id, external_reference_id):
        """Sets the external reference ID for the given entity.

        Args:
            entity_type (str): The type of the entity.
            entity_id (int): The ID of the entity.
            external_reference_id (str): The external reference ID to set.

        Returns:
            dict: The response of the update operation.

        """
        params = {"type": entity_type}
        payload = {"external_reference_id": external_reference_id}

        self.session.headers.update(
            {
                "Content-Type": self.content_type,
            },
        )

        request_url = self._get_full_url(SET_ENTITY_TICKET_API_NAME, entity_id=entity_id)
        response = self._make_rest_call(
            SET_ENTITY_TICKET_API_NAME,
            "PATCH",
            request_url,
            params=params,
            json=payload,
        )

        return response

    def query_investigation(self, query, version=None):
        """Starts a query investigation.

        Args:
            query (str): The investigation query.
            version (str, optional): The version of the query. Defaults to None.

        Returns:
            dict: The response of the query investigation operation.

        """
        payload = {"query": query}
        if version:
            payload["version"] = version

        self.session.headers.update(
            {
                "Content-Type": self.content_type,
            },
        )

        request_url = self._get_full_url(QUERY_INVESTIGATION_API_NAME)
        response = self._make_rest_call(
            QUERY_INVESTIGATION_API_NAME,
            "POST",
            request_url,
            json=payload,
        )

        return response

    def get_investigation_results(self, request_id, limit):
        """Retrieves the results of a query investigation.

        Args:
            request_id (str): The ID of the investigation request.
            limit (int): The maximum number of results to return.

        Returns:
            list: A list of InvestigationResult objects for the given request ID.

        """
        request_url = self._get_full_url(
            GET_INVESTIGATION_RESULTS_API_NAME,
            request_id=request_id,
        )
        response = self._paginator(
            GET_INVESTIGATION_RESULTS_API_NAME,
            "GET",
            request_url,
            result_key=INVESTIGATION_RESULTS_DATA_KEY,
            params={},
            limit=limit,
        )

        return [
            self.parser.build_investigation_result_object(result)
            for result in response
        ]

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
            UPDATE_ASSIGNMENT_API_NAME,
            assignment_id=assignment_id,
        )
        response = self._make_rest_call(
            UPDATE_ASSIGNMENT_API_NAME,
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
            if action_parameter_value and action_parameter_value != "None"
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
        
    def get_detection_events_checkpoint(self):
        """Reads the connector_state checkpoint persisted from the previous iteration.

        Returns:
            str|None: The stored `next_checkpoint` value, or None on the first run.

        """
        return self.siemplify.get_connector_context_property(
            self.siemplify.context.connector_info.identifier,
            DETECTION_EVENTS_CHECKPOINT_PROPERTY_KEY,
        )

    def save_detection_events_checkpoint(self, checkpoint):
        """Persists the checkpoint (connector_state) so the next iteration resumes from it.

        Args:
            checkpoint (str): The `next_checkpoint` value to persist.

        """
        if not checkpoint:
            return
        self.siemplify.set_connector_context_property(
            self.siemplify.context.connector_info.identifier,
            DETECTION_EVENTS_CHECKPOINT_PROPERTY_KEY,
            checkpoint,
        )

    def list_detection_events_by_filters(
        self,
        existing_ids,
        entity_type,
        start_time,
        limit,
        unresolved_priority,
        include_triaged,
        checkpoint=None,
    ):
        """Retrieves a list of detection events using the API's checkpoint-based pagination.

        On the first run (no stored `checkpoint`), the request is scoped with
        `event_timestamp_gte` derived from the connector start time. Every following call
        resumes from the `next_checkpoint` returned by the previous response, passed back
        via the `from` query parameter , looping while `remaining_count` is positive and the configured limit
        has not been reached.

        Returns:
            tuple: (list of DetectionEvent, the latest checkpoint to persist as connector_state)

        """
        limit = limit or DEFAULT_RESULTS_LIMIT
        request_url = self._get_full_url(LIST_DETECTION_EVENTS_API_NAME)
        params = {"size": DETECTION_EVENTS_SIZE}
        if entity_type:
            params["type"] = entity_type
        params["unresolved_priority"] = unresolved_priority
        params["include_triaged"] = include_triaged

        if checkpoint:
            params["from"] = checkpoint
        else:
            params["event_timestamp_gte"] = datetime.utcfromtimestamp(
                start_time / 1000,
            ).strftime(FIRST_TIMESTAMP_FORMAT)
            self.siemplify.LOGGER.info(f"event timestamp = {params['event_timestamp_gte']}")

        new_events = []
        existing_events = copy.deepcopy(existing_ids)
        latest_checkpoint = checkpoint
        
        while True:
            response = self._make_rest_call(
                LIST_DETECTION_EVENTS_API_NAME,
                "GET",
                request_url,
                params=params,
            )
            results = response.get("events", [])
            next_checkpoint = response.get("next_checkpoint")
            remaining_count = response.get("remaining_count", 0)

            if not include_triaged:
                results = [event for event in results if not event.get("triaged")]

            duplicates = []
            events = [
                self.parser.build_detection_event_object(event)
                for event in results
                if not self._is_duplicate(
                    get_detection_alert_id(event["detection_id"], event["id"]),
                    existing_events,
                    duplicates,
                )
            ]
            new_events.extend(events)

            if duplicates:
                self.siemplify.LOGGER.info(f"Found duplicates = {duplicates}")

            if next_checkpoint:
                latest_checkpoint = next_checkpoint

            if not next_checkpoint or remaining_count <= 0 or len(new_events) >= limit:
                return new_events, latest_checkpoint

            params = {**params, "from": next_checkpoint}


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
