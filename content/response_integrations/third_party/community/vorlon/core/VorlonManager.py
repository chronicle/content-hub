from __future__ import annotations

import json
import time

import requests

from .Utilities import remove_spaces, validate_and_convert_to_epoch


class VorlonManager:
    def __init__(
        self,
        url=None,
        client_id=None,
        client_secret=None,
        refresh_token=None,
    ):
        self.url = url
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = requests.Session()
        self.token = None
        self.token_expiry = None
        self.refresh_token = refresh_token
        self.update_token()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )

    def update_token(self):
        if not self.token or int(time.time()) > self.token_expiry:
            self.token = self.get_access_token()

    def get_access_token(self):
        request_url = f"{self.url}/rest/v1/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        response = self.session.post(request_url, headers=headers, data=payload)
        access_token = response.json().get("access_token")
        if access_token:
            self.token_expiry = int(time.time()) + response.json().get("expires_in", 0)
            return access_token
        error = response.json().get("error_description")
        raise Exception(
            f"Failed fetching token. Reason - {error} and Status - {response.status_code}",
        )

    def test_connectivity(self):
        request_url = f"{self.url}/rest/v1/services"
        response = self.session.get(request_url)

    def get_all_services(self):
        request_url = f"{self.url}/rest/v1/services"
        response = self.session.get(request_url)
        return response.json()

    def get_secrets(self, secrets=None, service=None):
        request_url = f"{self.url}/rest/v1/secrets"
        params = {}
        if secrets and service:
            raise Exception(
                "Both secret id and service id were provided. Please provide either secret ids or service id",
            )
        if not secrets and not service:
            raise Exception("Please provide either secret ids or service id")
        if secrets:
            secrets = remove_spaces(secrets)
            params.update({"ids": secrets})
        elif service:
            params.update({"service_id": service})
        response = self.session.get(request_url, params=params)
        return response.json()

    def get_connection_summary(
        self,
        secrets=None,
        service=None,
        instance_id=None,
        from_time=None,
        to_time=None,
        connection_type=None,
    ):
        if not service:
            raise Exception("Please provide a service id")
        request_url = f"{self.url}/rest/v1/connections/summary/{service}"
        if secrets:
            secrets = remove_spaces(secrets)
        if from_time:
            from_time = validate_and_convert_to_epoch(from_time)
        if to_time:
            to_time = validate_and_convert_to_epoch(to_time)
        params = {
            "secret_ids": secrets,
            "instance_id": instance_id,
            "from": from_time,
            "to": to_time,
            "type": connection_type,
        }
        params = {k: v for k, v in params.items() if v is not None}
        response = self.session.get(request_url, params=params)
        response_json = response.json()
        if not response_json:
            raise Exception(f"Response content is empty for service: {service}")
        return response_json

    def get_connections(
        self,
        secrets=None,
        service=None,
        instance_id=None,
        from_time=None,
        to_time=None,
        limit=None,
    ):
        if not service:
            raise Exception("Please provide a service id")
        request_url = f"{self.url}/rest/v1/connections/{service}"
        if secrets:
            secrets = remove_spaces(secrets)
        if from_time:
            from_time = validate_and_convert_to_epoch(from_time)
        if to_time:
            to_time = validate_and_convert_to_epoch(to_time)
        if limit:
            limit = int(limit)
        params = {
            "secret_ids": secrets,
            "instance_id": instance_id,
            "from": from_time,
            "to": to_time,
            "limit": limit,
        }
        params = {k: v for k, v in params.items() if v is not None}
        response = self.session.get(request_url, params=params)
        response_json = response.json()
        if not response_json:
            raise Exception(f"Response content is empty for service: {service}")
        return response_json

    def get_alerts(
        self,
        requesting_service=None,
        responding_service=None,
        alert_ids=None,
        from_time=None,
        to_time=None,
        status=None,
        page=None,
        limit=None,
    ):
        request_url = f"{self.url}/rest/v1/alerts"
        if requesting_service:
            requesting_service = remove_spaces(requesting_service)
        if responding_service:
            responding_service = remove_spaces(responding_service)
        if alert_ids:
            alert_ids = remove_spaces(alert_ids)
        if from_time:
            if isinstance(from_time, str):
                from_time = validate_and_convert_to_epoch(from_time)
            if isinstance(from_time, int):
                from_time = from_time
            else:
                raise Exception("Incompatible from time provided")
        if to_time:
            to_time = validate_and_convert_to_epoch(to_time)
        if isinstance(page, str):
            page = int(page)
        if isinstance(limit, str):
            limit = int(limit)
        params = {
            "requesting_service": requesting_service,
            "responding_service": responding_service,
            "alert_ids": alert_ids,
            "page": page,
            "from": from_time,
            "to": to_time,
            "status": status,
            "limit": limit,
        }
        params = {k: v for k, v in params.items() if v is not None}
        response = self.session.get(request_url, params=params)
        response_json = response.json()
        if not response_json and response.status_code == 200:
            return {}
        return response_json

    def get_linked_alerts(self, alert_id=None, status=None, page=None, limit=None):
        if not alert_id:
            raise Exception("Please provide an alert_id")
        request_url = f"{self.url}/rest/v1/alerts/linked/{id}"
        if page:
            page = int(page)
        if limit:
            limit = int(limit)
        params = {"id": alert_id, "status": status, "page": page, "limit": limit}
        params = {k: v for k, v in params.items() if v is not None}
        response = self.session.get(request_url, params=params)
        response_json = response.json()
        if not response_json and response.status_code == 200:
            raise Exception(f"No linked alerts were found for the alert id: {alert_id}")
        return response_json

    def update_alert(self, alert_object=None):
        request_url = f"{self.url}/rest/v1/alerts/update"
        try:
            alert_json = json.loads(alert_object)
        except Exception:
            raise Exception(
                f"The input string is not in a JSON Format:\n {alert_object}",
            )
        response = self.session.put(request_url, json=alert_json)
        response_json = response.json()
        return response_json
