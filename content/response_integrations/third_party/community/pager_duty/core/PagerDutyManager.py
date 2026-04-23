from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

import requests
from TIPCommon.types import SingleJson


class PagerDutyManager:
    BASE_URL: str = "https://api.pagerduty.com"
    INCIDENTS_URI: str = "/incidents"

    def __init__(
        self,
        api_key: str,
        verify_ssl: bool = True,
        from_email: str | None = None,
    ) -> None:
        """Initializes PagerDutyManager with params as set in connector config.

        Args:
            api_key: PagerDuty API key.
            verify_ssl: Whether to verify SSL certificates.
            from_email: The email address of the user performing the action.
        """
        self.api_key: str = api_key
        self.verify_ssl: bool = verify_ssl
        self.from_email: str | None = from_email

        self.requests_session: requests.Session = requests.Session()
        self.requests_session.verify: bool = self.verify_ssl

    def test_connectivity(self) -> None:
        """Tests connectivity and authentication to the PagerDuty API."""
        url: str = self.BASE_URL + "/abilities"
        headers: dict[str, str] = {
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Authorization": f"Token token={self.api_key}",
        }
        response: requests.Response = self.requests_session.get(
            url,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()

    def acknowledge_incident(self, incident_id: str) -> requests.Response:
        """Acknowledges an incident in PagerDuty.

        API Reference: https://developer.pagerduty.com/api-reference/8a0e1aa2ec666-update-an-incident

        Args:
            incident_id (str): The ID of the incident to acknowledge.

        Returns:
            requests.Response: The API response.
        """
        url: str = self.BASE_URL + self.INCIDENTS_URI + f"/{incident_id}"
        data: dict[str, str] = {"statuses[]": "acknowledged"}
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Authorization": f"Token token={self.api_key}",
        }
        response: requests.Response = requests.request(
            "GET",
            url,
            headers=headers,
            params=data,
            timeout=10,
        )
        return response

    def resolve_incident(self, incident_id: str) -> SingleJson:
        """Resolves an incident in PagerDuty.

        Args:
            incident_id: The ID of the incident to resolve.

        Returns:
            SingleJson: The API response.
        """
        url: str = self.BASE_URL + self.INCIDENTS_URI + f"/{incident_id}"
        payload: SingleJson = {
            "incident": {
                "type": "incident",
                "status": "resolved"
            }
        }
        headers: dict[str, str] = self._get_auth_headers()
        headers["Content-Type"] = "application/json"
        response = self.requests_session.put(
            url,
            json=payload,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def add_incident_note(self, incident_id: str, content: str) -> SingleJson:
        """Adds a note to an incident in PagerDuty.

        Args:
            incident_id: The ID of the incident to add the note to.
            content: The content of the note.

        Returns:
            SingleJson: The API response.
        """
        url: str = self.BASE_URL + self.INCIDENTS_URI + f"/{incident_id}/notes"
        payload: SingleJson = {
            "note": {
                "content": content
            }
        }
        headers: dict[str, str] = self._get_auth_headers()
        headers["Content-Type"] = "application/json"
        response = self.requests_session.post(
            url,
            json=payload,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_incident_notes(self, incident_id: str) -> list[SingleJson]:
        """Gets notes for an incident from PagerDuty.

        Args:
            incident_id: The ID of the incident.

        Returns:
            list[SingleJson]: List of notes.
        """
        url: str = self.BASE_URL + self.INCIDENTS_URI + f"/{incident_id}/notes"
        response = self.requests_session.get(
            url,
            headers=self._get_auth_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("notes", [])

    def get_incident(self, incident_id: str) -> SingleJson:
        """Gets an incident from PagerDuty by ID.

        Args:
            incident_id (str): The ID of the incident to retrieve.

        Returns:
            SingleJson: The incident details.
        """
        url: str = self.BASE_URL + self.INCIDENTS_URI + f"/{incident_id}"
        response = self.requests_session.get(
            url,
            headers=self._get_auth_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("incident")

    def list_oncalls(self) -> list[SingleJson]:
        """Lists on-calls.

        Returns:
            list[SingleJson]: List of on-calls.
        """
        url: str = f"{self.BASE_URL}/oncalls"
        response = self.requests_session.get(
            url=url, headers=self._get_auth_headers(), timeout=10
        )
        response.raise_for_status()
        return response.json().get("oncalls", [])

    def get_all_incidents(self) -> list[SingleJson]:
        """Gets all incidents.

        Returns:
            list[SingleJson]: List of incidents.
        """
        self.requests_session.headers.update(
            {"Authorization": f"Token token={self.api_key}"},
        )
        url: str = self.BASE_URL + "/incidents"
        response: requests.Response = self.requests_session.get(url=url, timeout=10)
        response.raise_for_status()
        incident_data: SingleJson = response.json()
        return incident_data.get("incidents")

    def list_incidents(self) -> list[SingleJson] | str:
        """Lists incidents.

        Returns:
            list[SingleJson] | str: List of incidents or "No Incidents Found".
        """
        url: str = f"{self.BASE_URL}/incidents"
        response: requests.Response = self.requests_session.get(
            url=url, headers=self._get_auth_headers(), timeout=10
        )
        response.raise_for_status()
        incidents: list[SingleJson] = response.json().get("incidents")
        if incidents:
            return incidents
        return "No Incidents Found"

    def list_users(self) -> list[SingleJson]:
        """Lists users.

        Returns:
            list[SingleJson]: List of users.
        """
        url: str = f"{self.BASE_URL}/users"
        response: requests.Response = self.requests_session.get(
            url=url, headers=self._get_auth_headers(), timeout=10
        )
        response.raise_for_status()
        return response.json().get("users", [])

    def create_incident(
        self,
        email_from: str,
        title: str,
        service: str,
        urgency: str,
        body: str,
    ) -> SingleJson:
        """Creates an incident.

        Args:
            email_from (str): Email address of the user creating the incident.
            title (str): Title of the incident.
            service (str): Service ID.
            urgency (str): Urgency level.
            body (str): Incident details.

        Returns:
            SingleJson: The created incident or message.
        """
        self.requests_session.headers.update(
            {"Authorization": f"Token token={self.api_key}", "From": f"{email_from}"},
        )
        payload: SingleJson = {
            "incident": {
                "type": "incident",
                "title": f"{title}",
                "service": {"id": f"{service}", "type": "service_reference"},
                "urgency": f"{urgency}",
                "body": {"type": "incident_body", "details": f"{body}"},
            },
        }
        url: str = self.BASE_URL + "/incidents"

        response = self.requests_session.post(url=url, json=payload, timeout=10)
        if response.status_code == 400:
            raise Exception(f"400 Bad Request: {response.text}")
        response.raise_for_status()
        if response.json().get("incident_number") != 0:
            return response.json()
        return {"message": "No Incident Found"}

    def get_incident_ID(self, incidentID: str, email_from: str) -> SingleJson:
        """Gets incident by ID.

        Args:
            incidentID (str): Incident ID or key.
            email_from (str): Email address.

        Returns:
            SingleJson: Incident data.
        """
        self.requests_session.headers.update(
            {"Authorization": f"Token token={self.api_key}", "From": f"{email_from}"},
        )
        parameters: dict[str, str] = {"user_ids[]": incidentID}
        url: str = self.BASE_URL + self.INCIDENTS_URI
        response: requests.Response = self.requests_session.get(
            url=url, json=parameters, timeout=10
        )
        response.raise_for_status()
        incident_data: SingleJson = {}
        info_got: list[SingleJson] = response.json().get("incidents")

        for incident in info_got:
            if incident.get("incident_key") == incidentID:
                incident_data = incident

        return incident_data

    def get_user_by_email(self, email: str) -> SingleJson | str:
        """Gets user by email.

        Args:
            email (str): User email.

        Returns:
            SingleJson | str: User dict or "No User Found".
        """
        url: str = f"{self.BASE_URL}/users"
        params: dict[str, str] = {"query": email}
        response: requests.Response = self.requests_session.get(
            url=url, headers=self._get_auth_headers(), params=params, timeout=10
        )
        response.raise_for_status()
        users: list[SingleJson] = response.json().get("users", [])

        for user in users:
            if user.get("email") == email:
                return user
        return "No User Found"

    def get_user_by_ID(self, userID: str) -> SingleJson | str:
        """Gets user by ID.

        Args:
            userID (str): User ID.

        Returns:
            SingleJson | str: User dict or "No User Found".
        """
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Authorization": f"Token token={self.api_key}",
        }
        url: str = self.BASE_URL + "/users/" + userID
        response = self.requests_session.request(
            "GET", url, headers=headers, timeout=10
        )
        response.raise_for_status()
        if response.json()["user"]:
            return response.json()["user"]
        return "No User Found"

    def list_filtered_incidents(self, params: dict[str, Any]) -> list[SingleJson]:
        """Lists filtered incidents.

        Args:
            params (dict[str, Any]): Filter parameters.

        Returns:
            list[SingleJson]: List of incidents.
        """
        base_url: str = self.BASE_URL + self.INCIDENTS_URI
        headers: dict[str, str] = self._get_auth_headers()
        headers["Content-Type"] = "application/json"

        query_parts: list[str] = []
        for key, value in params.items():
            encoded_key = quote_plus(key)
            if isinstance(value, list):
                for item in value:
                    if item is not None:
                        query_parts.append(f"{encoded_key}={quote_plus(str(item))}")
            else:
                if value is not None:
                    query_parts.append(f"{encoded_key}={quote_plus(str(value))}")

        query_string = "&".join(query_parts)

        full_url: str = base_url
        if query_string:
            full_url += f"?{query_string}"

        response: requests.Response = self.requests_session.get(
            full_url,
            headers=headers,
            timeout=10,
        )

        response.raise_for_status()
        return response.json().get("incidents")

    def snooze_incident(self, email_from: str, incident_id: str) -> SingleJson:
        """Snoozes an incident.

        Args:
            email_from (str): Email address.
            incident_id (str): Incident ID.

        Returns:
            SingleJson: API response.
        """
        self.requests_session.headers.update(
            {"Authorization": f"Token token={self.api_key}", "From": f"{email_from}"},
        )
        payload: dict[str, int] = {"duration": 3600}
        url: str = self.BASE_URL + self.INCIDENTS_URI + f"/{incident_id}" + "/snooze"
        response: requests.Response = self.requests_session.post(
            url=url, json=payload, timeout=10
        )
        response.raise_for_status()
        return response.json()

    def run_response_play(
        self,
        email: str,
        response_plays_id: str,
        user_id: str
    ) -> SingleJson:
        """Runs a response play.

        Args:
            email (str): Email address.
            response_plays_id (str): Response play ID.
            user_id (str): User ID (used as incident ID in payload).

        Returns:
            SingleJson: API response message.
        """
        payload: SingleJson = {
            "incident": {"id": f"{user_id}", "type": "incident_reference"}
        }

        headers: dict[str, str] = self._get_auth_headers()
        headers["Content-Type"] = "application/json"
        headers["From"] = f"{email}"

        full_url: str = self.BASE_URL + "/response_plays/" + response_plays_id + "/run"
        response = self.requests_session.request(
            "POST",
            full_url,
            json=payload,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        return {"message": response}

    def _get_auth_headers(self) -> dict[str, str]:
        """Returns a dictionary with standard authentication headers.

        Returns:
            dict[str, str]: Auth headers.
        """
        headers: dict[str, str] = {
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Authorization": f"Token token={self.api_key}",
        }
        if self.from_email:
            headers["From"] = self.from_email
        return headers
