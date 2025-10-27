from __future__ import annotations

from urllib.parse import quote_plus

import requests


class PagerDutyManager:
    BASE_URL = "https://api.pagerduty.com"
    INCIDENTS_URI = "/incidents"

    def __init__(self, api_key: str, verify_ssl: bool = False):
        """Initializes PagerDutyManager with params as set in connector config"""
        self.api_key = api_key
        self.verify_ssl = verify_ssl

        self.requests_session = requests.Session()
        self.requests_session.verify = self.verify_ssl

    def test_connectivity(self):
        """Tests connectivity and authentication to the PagerDuty API."""
        url = self.BASE_URL + "/abilities"
        headers = {
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Authorization": f"Token token={self.api_key}",
        }
        response = self.requests_session.get(
            url,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()

    def acknowledge_incident(self, incident_id):
        """Acknowledges an incident in PagerDuty
        API Reference: https://developer.pagerduty.com/api-reference/8a0e1aa2ec666-update-an-incident
        """
        url = self.BASE_URL + self.INCIDENTS_URI + f"/{incident_id}"
        data = {"statuses[]": "acknowledged"}
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Authorization": f"Token token={self.api_key}",
        }
        response = requests.request(
            "GET",
            url,
            headers=headers,
            params=data,
            timeout=10,
        )
        return response

    def list_oncalls(self):
        url = f"{self.BASE_URL}/oncalls"
        response = self.requests_session.get(
            url=url, headers=self._get_auth_headers(), timeout=10
        )
        response.raise_for_status()
        return response.json().get("oncalls", [])

    def get_all_incidents(self):
        self.requests_session.headers.update(
            {"Authorization": f"Token token={self.api_key}"},
        )
        url = self.BASE_URL + "/incidents"
        response = self.requests_session.get(url=url, timeout=10)
        response.raise_for_status()
        incident_data = response.json()
        return incident_data.get("incidents")

    def list_incidents(self):
        url = f"{self.BASE_URL}/incidents"
        response = self.requests_session.get(
            url=url, headers=self._get_auth_headers(), timeout=10
        )
        response.raise_for_status()
        incidents = response.json().get("incidents")
        if incidents:
            return incidents
        return "No Incidents Found"

    def list_users(self):
        url = f"{self.BASE_URL}/users"
        response = self.requests_session.get(
            url=url, headers=self._get_auth_headers(), timeout=10
        )
        response.raise_for_status()
        return response.json().get("users", [])

    def create_incident(self, email_from, title, service, urgency, body):
        self.requests_session.headers.update(
            {"Authorization": f"Token token={self.api_key}", "From": f"{email_from}"},
        )
        payload = {
            "incident": {
                "type": "incident",
                "title": f"{title}",
                "service": {"id": f"{service}", "type": "service_reference"},
                "urgency": f"{urgency}",
                "body": {"type": "incident_body", "details": f"{body}"},
            },
        }
        url = self.BASE_URL + "/incidents"

        response = self.requests_session.post(url=url, json=payload, timeout=10)
        response.raise_for_status()
        if response.json().get("incident_number") != 0:
            return response.json()
        return {"message": "No Incident Found"}

    def get_incident_ID(self, incidentID, email_from):
        self.requests_session.headers.update(
            {"Authorization": f"Token token={self.api_key}", "From": f"{email_from}"},
        )
        parameters = {"user_ids[]": incidentID}
        url = self.BASE_URL + self.INCIDENTS_URI
        response = self.requests_session.get(url=url, json=parameters, timeout=10)
        response.raise_for_status()
        incident_data = {}
        info_got = response.json().get("incidents")

        for incident in info_got:
            if incident.get("incident_key") == incidentID:
                incident_data = incident

        return incident_data

    def get_user_by_email(self, email):
        url = f"{self.BASE_URL}/users"
        params = {"query": email}
        response = self.requests_session.get(
            url=url, headers=self._get_auth_headers(), params=params, timeout=10
        )
        response.raise_for_status()
        users = response.json().get("users", [])
        # The API returns a list, find the exact email match
        for user in users:
            if user.get("email") == email:
                return user
        return "No User Found"

    def get_user_by_ID(self, userID):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Authorization": f"Token token={self.api_key}",
        }
        url = self.BASE_URL + "/users/" + userID
        response = self.requests_session.request(
            "GET", url, headers=headers, timeout=10
        )
        response.raise_for_status()
        if response.json()["user"]:
            return response.json()["user"]
        return "No User Found"

    def list_filtered_incidents(self, params: dict):
        base_url = self.BASE_URL + self.INCIDENTS_URI
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Authorization": f"Token token={self.api_key}",
        }

        query_parts = []
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

        full_url = base_url
        if query_string:
            full_url += f"?{query_string}"

        response = self.requests_session.get(
            full_url,
            headers=headers,
            timeout=10,
        )

        response.raise_for_status()
        if response.json().get("incidents"):
            return response.json()
        return {
            "incidents": [],
            "message": "No incident found with the filters entered",
        }

    def snooze_incident(self, email_from, incident_id):
        self.requests_session.headers.update(
            {"Authorization": f"Token token={self.api_key}", "From": f"{email_from}"},
        )
        payload = {"duration": 3600}
        url = self.BASE_URL + self.INCIDENTS_URI + f"/{incident_id}" + "/snooze"
        response = self.requests_session.post(url=url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()

    def run_response_play(self, email, response_plays_id, user_id):
        payload = {"incident": {"id": f"{user_id}", "type": "incident_reference"}}

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "From": f"{email}",
            "Authorization": f"Token token={self.api_key}",
        }

        full_url = self.BASE_URL + "/response_plays/" + response_plays_id + "/run"
        response = self.requests_session.request(
            "POST",
            full_url,
            json=payload,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        return {"message": response}

    def _get_auth_headers(self):
        """Returns a dictionary with standard authentication headers."""
        return {
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Authorization": f"Token token={self.api_key}",
        }
