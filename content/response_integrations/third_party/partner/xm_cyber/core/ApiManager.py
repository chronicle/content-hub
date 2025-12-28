"""API Manager to handle API calls."""

from __future__ import annotations

import json

import requests
from TIPCommon.oauth import AuthorizedOauthClient, CredStorage

from .constants import (
    ENRICH_ENTITIES_ENDPOINT,
    ERRORS,
    INTEGRATION_NAME,
    PING_ENDPOINT,
    PUSH_BREACH_POINT_ENDPOINT,
)
from .utils import generate_encryption_key
from .xmcyber_oauth_adapter import XMCyberOAuthAdapter, XMCyberOAuthManager


class ApiManager:
    """Handle API calls made to XMCyber."""

    def __init__(self, auth_type, base_url, api_key, siemplify):
        """
        Initialize ApiManager instance.

        Args:
            auth_type (bool): True if using access token, False if using API key.
            base_url (str): the base URL of the API.
            api_key (str): the API key.
            siemplify (Siemplify): the siemplify instance.

        """
        self.auth_type = auth_type
        self.base_url = base_url
        self.api_key = api_key
        self.logger = siemplify.LOGGER

        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.error = ""

        # Initialize OAuth components if using token-based auth
        if self.auth_type:
            self.logger.info("Using the access token based authentication")
            self._init_oauth(siemplify)
        else:
            self.logger.info("Using the API key based authentication")
            self._init_api_key_auth()
            success, response = self.call_api("POST", PING_ENDPOINT)

            if not success:
                self.error = str(response)

    def _init_oauth(self, siemplify: str) -> None:
        """Initialize OAuth components."""

        self.logger.info("Initializing OAuth components")
        # Create OAuth adapter
        oauth_adapter = XMCyberOAuthAdapter(
            base_url=self.base_url, api_key=self.api_key, tenant=siemplify.integration_instance
        )

        # Create credential storage
        cred_storage = CredStorage(
            chronicle_soar=siemplify,
            encryption_password=generate_encryption_key(self.api_key, self.base_url),
        )

        # Initialize OAuth manager
        self.oauth_manager = XMCyberOAuthManager(
            oauth_adapter=oauth_adapter, cred_storage=cred_storage
        )

        # Create authorized client
        self.session = AuthorizedOauthClient(self.oauth_manager)
        oauth_adapter._refresh_token = self.oauth_manager._token.refresh_token

    def __del__(self):
        # ensure cleanup when APIManager object is destroyed
        if self.auth_type:
            self.session.close()

    def _init_api_key_auth(self) -> None:
        """Initialize API key based authentication."""
        self.logger.info("Initializing API key authentication")
        self.session.headers.update({"x-api-key": self.api_key})

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
        url = self.base_url + endpoint
        self.logger.info(f"Calling {INTEGRATION_NAME} endpoint: {url} with params: {kwargs}")
        try:
            response = self.session.request(method=method.upper(), url=url, **kwargs)
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
