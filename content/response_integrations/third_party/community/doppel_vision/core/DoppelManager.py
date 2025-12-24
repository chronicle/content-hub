from __future__ import annotations

import requests


class DoppelManager:
    def __init__(self, api_key):
        """Initialize the manager with the API key and base URL."""
        self.api_key = api_key
        self.base_url = "https://api.doppel.com/v1"

    def get_alert(self, entity=None, alert_id=None):
        """Fetches an alert using either the entity or the alert ID, but not both.

        :param entity: (str) The entity for which to fetch the alert (usually a URL).
        :param alert_id: (str) The alert ID to fetch the alert.
        :return: (dict) The JSON response containing the alert if successful, otherwise None.
        """
        if entity and alert_id:
            raise ValueError(
                "Only one of 'entity' or 'alert_id' can be provided, not both.",
            )
        if not entity and not alert_id:
            raise ValueError("Either 'entity' or 'alert_id' must be provided.")

        url = f"{self.base_url}/alert"
        params = {"entity": entity} if entity else {"id": alert_id}

        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to get alert: {e}")
            return None

    def connection_test(self):
        """Tests the connectivity to Doppel and validates credentials.
        Returns True if the request is successful and credentials are valid, otherwise False.
        """
        url = f"{self.base_url}/alerts"
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"Connection Test failed: {e}")
            return False

    def get_alerts(self, filters=None):
        """Fetches multiple alerts from Doppel, optionally filtered by criteria.

        :param filters: (dict) A dictionary of filter parameters (e.g., {"search_key": "example", "tags": ["tag1", "tag2"]}).
        :return: (list) A list of alerts if successful, otherwise None.
        """
        url = f"{self.base_url}/alerts"
        try:
            response = requests.get(url, headers=self._get_headers(), params=filters)
            response.raise_for_status()
            return response.json().get(
                "alerts",
                [],
            )  # Assuming the API response contains an "alerts" key.
        except requests.RequestException as e:
            print(f"Failed to get alerts: {e}")
            return None

    def create_alert(self, entity):
        """Creates a new alert for a given entity in Doppel.

        :param entity: (str) The entity for which to create the alert.
        :return: (dict) The JSON response from Doppel if successful, otherwise None.
        """
        url = f"{self.base_url}/alert"
        payload = {"entity": entity}
        try:
            response = requests.post(
                url,
                headers=self._get_headers(content_type="application/json"),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to create alert: {e}")
            return None

    def update_alert(self, queue_state, entity_state, entity=None, alert_id=None):
        """Updates an existing alert using either the entity or the alert ID.

        :param queue_state: (str) The queue state to update to.
        :param entity_state: (str) The entity state to update to.
        :param entity: (str) The entity for which to update the alert (optional).
        :param alert_id: (str) The alert ID to update the alert (optional).
        :return: (dict) The JSON response containing the updated alert if successful, otherwise None.
        """
        if entity and alert_id:
            raise ValueError(
                "Only one of 'entity' or 'alert_id' can be provided, not both.",
            )
        if not entity and not alert_id:
            raise ValueError("Either 'entity' or 'alert_id' must be provided.")

        url = f"{self.base_url}/alert"
        params = {"entity": entity} if entity else {"id": alert_id}
        payload = {"queue_state": queue_state, "entity_state": entity_state}

        try:
            response = requests.put(
                url,
                headers=self._get_headers(content_type="application/json"),
                params=params,
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to update alert: {e}")
            return None

    def create_abuse_alert(self, entity):
        """Creates an abuse alert for a given entity in Doppel.

        :param entity: (str) The entity for which to create the abuse alert.
        :return: (dict) The JSON response from Doppel if successful, otherwise None.
        """
        url = f"{self.base_url}/alert/abuse"
        payload = {"entity": entity}
        try:
            response = requests.post(
                url,
                headers=self._get_headers(content_type="application/json"),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to create abuse alert: {e}")
            return None

    def _get_headers(self, content_type="application/json"):
        """Generates headers for the API requests.

        :param content_type: (str) The content type for the request. Defaults to 'application/json'.
        :return: (dict) Headers including the API key and content type.
        """
        headers = {"accept": "application/json", "x-api-key": self.api_key}
        if content_type:
            headers["content-type"] = content_type
        return headers
