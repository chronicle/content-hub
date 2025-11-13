"""API Manager to handle API calls."""

from __future__ import annotations

import json

import requests

from .constants import (
    ENRICH_ENTITIES_ENDPOINT,
    ERRORS,
    INTEGRATION_NAME,
    PING_ENDPOINT,
    PUSH_BREACH_POINT_ENDPOINT,
)


class ApiManager:
    """Handle API calls made to XMCyber."""

    def __init__(self, auth_type, base_url, api_key, siemplify_logger):
        """
        Initialize ApiManager instance.

        Args:
            auth_type (bool): True if using access token, False if using API key.
            base_url (str): the base URL of the API.
            api_key (str): the API key.
            siemplify_logger (logging.Logger): the logger instance.

        """
        self.auth_type = auth_type
        self.base_url = base_url
        self.api_key = api_key
        self.logger = siemplify_logger

        self.session = requests.Session()
        self.access_token = None
        self.error = ""

        self.authenticate()

    def call_api(self, method, endpoint, **kwargs):
        """
        Make API call using endpoint, HTTP Method and any keyword arguments passed.

        Args:
            method (str): The HTTP method to use.
            endpoint (str): The endpoint to call.
            **kwargs: Additional keyword arguments to pass to the request method.

        Returns:
            tuple: A tuple containing the status of the API call, response and flag
                indicating if retry should be done.
        """
        self.logger.info(
            f"Calling {INTEGRATION_NAME} endpoint: {self.base_url + endpoint} with params: {kwargs}"
        )
        try:
            response = self.session.request(
                method=method.upper(), url=self.base_url + endpoint, **kwargs
            )
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ConnectTimeout,
        ):
            return False, ERRORS["API"]["CONNECTION_ERROR"]
        except Exception as e:
            return False, ERRORS["API"]["UNKNOWN_ERROR"].format(e)

        status_code = response.status_code
        try:
            api_response = response.json()
            if status_code == 200:
                return True, api_response

            if "message" in api_response:
                return False, f"{status_code}: {api_response['message']}"

        except json.JSONDecodeError:
            if status_code == 200:
                return True, ""

            # In case of Bad Request, the API response outputs the error message in HTML format
            if status_code == 400:
                return False, f"{status_code}: {response.text}"

            if status_code == 401:
                return (
                    False,
                    f"{status_code}: {ERRORS['API']['INVALID_AUTHENTICATION']}",
                )

            return (
                False,
                f"{status_code}: {ERRORS['API']['UNKNOWN_ERROR'].format(response.text)}",
            )

    def authenticate(self):
        """Authenticate the connection with XMCyber instance and set the headers for
        subsequent API calls."""
        self.session.headers.update({"x-api-key": self.api_key})

        if self.auth_type is False:
            self.logger.info("Using API key based authentication")
            success, response = self.call_api("POST", PING_ENDPOINT)

            if not success:
                self.error = str(response)
        else:
            self.logger.info("Using Access Token based authentication")
            success, response = self.call_api("POST", PING_ENDPOINT)
            if success:
                del self.session.headers["x-api-key"]
                self.access_token = response.get("accessToken")
                self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
            else:
                self.error = str(response)

    def push_breach_point_data(self, entity_ids, attribute_name):
        """
        Push breach point data to the XM Cyber instance.

        Args:
            entity_ids (list): List of entity IDs to push breach point data to.
            attribute_name (str): Name of the attribute to push.

        Returns:
            bool: True if the API call was successful, False otherwise.
        """
        request_body = {entity_id: [f"{attribute_name}: true"] for entity_id in entity_ids}
        success, response = self.call_api("POST", PUSH_BREACH_POINT_ENDPOINT, json=request_body)
        if not success:
            self.error = str(response)
            self.error += f"\nEntity IDs collected: {entity_ids}"

        return success

    def _process_entity_response(self, entity_response):
        """
        Process the response from the entity API call.

        Args:
            response (list): The response from the entity API call.

        Returns:
            dict: A dictionary containing the processed entity data.
        """
        # It is expected that labels will always be present in the response, but if not,
        # we can handle it gracefully.
        processed_response = {
            "product_object_id": entity_response.get("product_object_id"),
        }
        labels = entity_response.get("attribute", {}).get("labels", [])

        for label in labels:
            key = label.get("key")
            value = label.get("value")
            if key and key.startswith("XM Cyber - "):
                label_key = key.replace("XM Cyber - ", "")
                processed_response[label_key] = value

        return processed_response

    def _process_enrich_entities_response(self, response):
        expected_response = {}
        for entity in response:
            entity = entity.get("entity", {})

            entity_id = entity.get("asset", {}).get("hostname") or entity.get("user", {}).get(
                "userid"
            )
            if not entity_id or not isinstance(entity_id, str):
                self.logger.info(
                    f"hostname/userid field not found or empty in the received entity: {entity} "
                    f"\n Skipping..."
                )
                continue

            entity_id_lower = entity_id.lower()

            # Extracting asset details
            if "asset" in entity:
                asset = entity["asset"]
                expected_response[entity_id_lower] = {"hostname": asset.get("hostname")}
                processed_asset = self._process_entity_response(asset)
                expected_response[entity_id_lower].update(processed_asset)

            # Extracting user details
            elif "user" in entity:
                user = entity["user"]
                expected_response[entity_id_lower] = {"userid": user.get("userid")}
                processed_user = self._process_entity_response(user)
                expected_response[entity_id_lower].update(processed_user)

        return expected_response

    def enrich_entities(self, entity_ids):
        """
        Enrich entities in XM Cyber instance.

        Args:
            entity_ids (list): List of entity IDs to enrich.

        Returns:
            bool: True if the API call was successful, False otherwise.
        """
        params = [("names", name) for name in entity_ids]
        success, response = self.call_api("GET", ENRICH_ENTITIES_ENDPOINT, params=params)

        if not success:
            return False, str(response) + f" Entity IDs collected: {entity_ids}"

        if not response or response == []:
            return (
                False,
                "No XMCyber entity(ies) found from the API Response."
                + f" Entity IDs collected: {entity_ids}",
            )

        processed_response = self._process_enrich_entities_response(response)

        return success, processed_response
