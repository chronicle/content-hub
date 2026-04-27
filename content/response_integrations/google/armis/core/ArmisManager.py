# ============================================================================#
# title           :ArmisManager.py
# description     :This Module contain all Armis operations functionality
# author          :amit.levizky@siemplify.co
# date            :30-03-2021
# python_version  :3.7
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
from .exceptions import ArmisException
from urllib.parse import urljoin
from .ArmisParser import ArmisParser
from .consts import (
    DEFAULT_ORDER_BY,
    DEFAULT_LENGTH_TO_FETCH,
    DEFAULT_AQL,
    DEVICES,
    ACTIVITY,
    INTEGRATION_NAME,
    DEFAULT_RISK_LEVELS,
    DEFAULT_AQL_GET_ALERT_WITH_TIME,
    DEFAULT_AQL_GET_ALERT_WITHOUT_TIME,
    BAD_REQUEST,
    NOT_FOUND,
    WASNT_FOUND,
)
from .datamodels import Alert, Device, Activity, AlertConnection
from .exceptions import ArmisBadRequestException, ArmisNotFoundException

from .datamodels import Alert, Device, Activity, DeviceAlert, AlertConnection

from typing import List
import requests


HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
}
ENDPOINTS = {
    "access_token": "/api/v1/access_token/",
    "ping": "/api/v1/search/",
    "get-devices": "/api/v1/devices/",
    "search": "/api/v1/search/",
    "alerts": "/api/v1/alerts/{alert_id}/",
}


class ArmisManager:
    def __init__(self, api_root: str, api_secret: str, verify_ssl: bool = True):
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.api_secret = api_secret

        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS

        self.session.headers.update({"Authorization": self._login()})

        self.parser = ArmisParser()

    def _get_full_url(self, url_key, **kwargs) -> str:
        """
        Get full url from url key.
        :param url_id: {str} The key of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_key].format(**kwargs))

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate a response
        :param response: {requests.Response} The response
        :param error_msg: {str} The error message to display on failure
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise ArmisException(f"{error_msg}: {error} - {error.response.content}")

            if response.status_code == BAD_REQUEST:
                if WASNT_FOUND in response.json().get("message"):
                    raise ArmisBadRequestException(
                        f"{error_msg}: {error} {response.json().get('message')}"
                    )

            if response.status_code == NOT_FOUND:
                raise ArmisNotFoundException(
                    f"{error_msg}: {error} {response.json().get('message')}"
                )

            raise ArmisException(
                f"{error_msg}: {error} {response.json().get('message')}"
            )

    def _login(self) -> str:
        """
        Get an access token based on the secret_key
        return: {str} Access-Token
        """
        payload = {"secret_key": self.api_secret}
        request_url = self._get_full_url("access_token")
        response = self.session.post(request_url, data=payload)
        self.validate_response(response, "Unable to login to Armis service")

        return response.json().get("data", {}).get("access_token", "")

    def test_connectivity(self):
        """
        Test connectivity to the Armis service with parameters provided at the integration configuration page on
        the Marketplace tab.
        :return: raise Exception if failed to validate response
        """
        payload = {"aql": "in:devices", "length": 1}
        request_url = self._get_full_url("ping")
        response = self.session.get(request_url, params=payload)
        self.validate_response(
            response, f"Unable to connect to {INTEGRATION_NAME} service"
        )

    def get_alerts(
        self,
        existing_ids,
        aql: str = DEFAULT_AQL_GET_ALERT_WITH_TIME,
        after_date: str = None,
        severity: str = DEFAULT_RISK_LEVELS,
        _from: int = None,
        order_by: str = DEFAULT_ORDER_BY,
        length: int = DEFAULT_LENGTH_TO_FETCH,
        max_alerts_to_fetch: int = DEFAULT_LENGTH_TO_FETCH,
    ) -> List[Alert]:
        """
        Fetching alerts from Armis service.
        :param aql: {str} Query to send. for example: aql=in:alerts after:2021-03-07T13:38:50
        before:2021-03-10 riskLevel:Low,Medium status:Unhandled&orderBy
        :param _from: {int} For pagination, get results after that number.
        :param order_by: {str} The field that determined the order of the results. Default: time
        :param length: {int} Number of result to return. Default: 100
        :param max_alerts_to_fetch: {str} Max alerts to fetch.
        :param severity: Severity of the alert in Armis to fetch
        :param after_date: Fetch alert only after this date
        :param existing_ids: {Dict} Ids that already fetched and should not be processed again.
        :return: {datamodels.AlertResponse} Alert Response object, will contain information about the response and
        alerts from Armis service
        """
        query = (
            aql.format(after_date, severity)
            if after_date
            else DEFAULT_AQL_GET_ALERT_WITHOUT_TIME.format(severity)
        )
        payload = {"aql": query, "orderBy": order_by, "length": length}

        alerts = []
        fetched_alerts_count = 0

        request_url = self._get_full_url("search")

        while len(alerts) <= max_alerts_to_fetch:
            payload["from"] = fetched_alerts_count
            response = self.session.get(request_url, params=payload)
            self.validate_response(response, "Unable to get alerts from Armis service")

            alert_response = self.parser.build_alert_response_object(response)

            # if alerts exists in the existing ids dict, we want to count them for pagination
            fetched_alerts_count += len(alert_response.data.alerts)

            # Fetch only alerts that not exists in existing_ids
            new_alerts = [
                alert
                for alert in alert_response.data.alerts
                if str(alert.alert_id) not in existing_ids
            ]

            if not new_alerts and not alert_response.data.next:
                break

            alerts.extend(new_alerts)

        return alerts[:max_alerts_to_fetch]

    def get_alert_devices(
        self,
        alert_id: int,
        _from: int = None,
        aql: str = DEFAULT_AQL,
        length: int = DEFAULT_LENGTH_TO_FETCH,
    ) -> List[DeviceAlert]:
        """
        Fetching alert devices from Armis service.
        :param alert_id: {str} Alert ID to fetch devices from.
        :param aql: {str} Query to send. for example: in:devices alert:(alertId:(4))
        :param _from: {int} For pagination, get results after that number.
        :param length: {int} Number of result to return. Default: 100.
        :return: {List[datamodels.Device]} List of devices related to the alert ID that provided as parameter.
        """
        payload = {
            "aql": aql.format(DEVICES, alert_id),
            "length": length,
            "from": _from,
        }
        request_url = self._get_full_url("search")
        response = self.session.get(request_url, params=payload)
        self.validate_response(
            response, "Unable to get alert devices from Armis service"
        )

        return self.parser.build_device_objects(response)

    def get_alert_activities(
        self,
        alert_id: int,
        _from: int = None,
        order_by: str = DEFAULT_ORDER_BY,
        aql: str = DEFAULT_AQL,
        length: int = DEFAULT_LENGTH_TO_FETCH,
    ) -> List[Activity]:
        """
        Fetching alert activities from Armis service.
        :param alert_id: {str} Alert ID to fetch activities from.
        :param _from: {int} For pagination, get results after that number.
        :param length: {int} Number of result to return. Default: 100.
        :param order_by: {str} The field that determined the order of the results. Default: time
        :param aql: {str} Query to send. for example: in:activity alert:(alertId:(4))
        :return: {List[datamodels.Activity]} List of activities related to the alert ID that provided as parameter.
        """
        payload = {
            "aql": aql.format(ACTIVITY, alert_id),
            "orderBy": order_by,
            "from": _from,
            "length": length,
        }
        request_url = self._get_full_url("search")
        response = self.session.get(request_url, params=payload)
        self.validate_response(
            response, "Unable to get alert activities from Armis service"
        )

        return self.parser.build_activity_objects(response)

    def get_device_by_mac(self, mac_address: str) -> Device:
        """
        Get device info by MAC address
        :param mac_address: {str} MAC Address of the device to fetch
        :return: {Device} Device info data model
        """
        params = {"mac": mac_address}
        request_url = self._get_full_url("get-devices")
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response, f"Unable to get device info with mac address of {mac_address}"
        )
        return self.parser.build_device_obj(response.json(), api_root=self.api_root)

    def get_device_by_ip(self, ip_address: str) -> Device:
        """
        Get device info by IP address
        :param ip_address: {str} IP Address of the device to fetch
        :return: {Device} Device info data model
        """
        params = {"ip": ip_address}
        request_url = self._get_full_url("get-devices")
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response, f"Unable to get device info with ip address of {ip_address}"
        )
        return self.parser.build_device_obj(response.json(), api_root=self.api_root)

    def get_alert_connections(
        self,
        aql: str,
        length: int = DEFAULT_LENGTH_TO_FETCH,
        max_alert_connections_to_fetch: int = DEFAULT_LENGTH_TO_FETCH,
    ) -> List[AlertConnection]:
        """
        Fetching alerts from Armis service.
        :param aql: {str} Query to send. for example: in:connections riskLevel:High,Medium activity:(alert:(alertId:(2)))
        :param length: {int} Number of result to return. Default: 100
        :param max_alert_connections_to_fetch: {str} Max alert connections to fetch.
        :return: {List[datamodels.AlertConnection}} List of alert connections data model
        """
        payload = {"aql": aql, "length": length}

        alert_connections = []
        fetched_alert_connections = 0

        request_url = self._get_full_url("search")

        while len(alert_connections) <= max_alert_connections_to_fetch:
            payload["from"] = fetched_alert_connections
            response = self.session.get(request_url, params=payload)
            self.validate_response(response, "Unable to get alerts from Armis service")

            alert_connections_response = (
                self.parser.build_alert_connection_response_object(response)
            )

            fetched_alert_connections += len(
                alert_connections_response.data.alert_connections
            )

            new_alerts = [
                alert_connection
                for alert_connection in alert_connections_response.data.alert_connections
            ]

            if not new_alerts and not alert_connections_response.data.next:
                break

            alert_connections.extend(new_alerts)

        return alert_connections[:max_alert_connections_to_fetch]

    def update_alert_status(self, alert_id: int, status: str):
        """
        Update status of the alert in Armis.
        :param alert_id: {int} ID of the alert for which you want to update status.
        :param status: {str} What status should be set for the alert.
        """
        request_url = self._get_full_url("alerts", alert_id=alert_id)
        payload = {"status": status}
        response = self.session.patch(request_url, data=payload)
        self.validate_response(response, f"Unable to update alert status")
