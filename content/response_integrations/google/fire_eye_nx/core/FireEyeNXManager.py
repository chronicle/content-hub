from __future__ import annotations
import os
from urllib.parse import urljoin

import requests

from TIPCommon import filter_old_alerts

from .FireEyeNXExceptions import ArtifactsNotFoundException
from .FireEyeNXParser import FireEyeNXParser

from .UtilsManager import validate_response
from .FireEyeNXConstants import (
    ENDPOINTS,
    HEADERS,
    API_TIME_FORMAT,
    DURATION,
    ALERT_ID_FIELD,
)


class FireEyeNXManager:

    def __init__(self, api_root, username, password, verify_ssl=False, siemplify=None):
        """
        The method is used to init an object of Manager class
        :param api_root: API Root of the FireEye NX instance.
        :param username: FireEye NX username.
        :param password: FireEye NX password.
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the FireEye NX server is valid.
        :param siemplify: (obj) An instance of the SDK SiemplifyConnectorExecution class.
        """
        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.username = username
        self.password = password
        self.siemplify = siemplify
        self.parser = FireEyeNXParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        self.session.auth = (self.username, self.password)
        self.api_token = self.obtain_token()
        self.session.headers.update({"X-FeApi-Token": self.api_token})
        self.session.auth = None

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def obtain_token(self):
        """
        Obtain FireEye NX authentication security token.
        :return: {str} token
        """
        request_url = self._get_full_url("authorize")
        response = self.session.post(request_url)
        validate_response(response)
        return response.headers.get("X-FeApi-Token")

    def test_connectivity(self):
        """
        Test connectivity to the FireEye NX.
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("test_connectivity")
        response = self.session.get(request_url)
        validate_response(response, "Unable to connect to FireEye NX.")

    def download_alert_artifacts(self, alert_uuid):
        """
        Download alert artifacts.
        :param alert_uuid: UUID of alert from where to download artifacts.
        :return: Artifacts raw data
        """
        request_url = self._get_full_url("download_artifacts", alert_uuid=alert_uuid)
        self.session.headers = None
        response = self.session.get(
            request_url, headers={"X-FeApi-Token": self.api_token}
        )
        try:
            validate_response(response)
        except Exception as e:
            if response.status_code == 404:
                raise ArtifactsNotFoundException()
            raise Exception(e)
        return response

    def save_artifacts_to_file(self, response, download_path):
        """
        Save raw data to a zip in defined path.
        :param response: Download response.
        :param download_path: Path to save the files.
        :return: True if successful, exception otherwise
        """
        if not os.path.exists(download_path):
            with open(download_path, "wb") as f:
                try:
                    for chunk in response.iter_content():
                        f.write(chunk)
                except Exception as e:
                    raise Exception(e)
            return True
        return False

    def get_alerts(self, existing_ids, start_time, duration=DURATION):
        """
        Get alerts.
        :param existing_ids: {list} The list of existing ids.
        :param start_time: {str} The datetime from where to fetch alerts.
        :param duration: {int} Duration from start time that will be used to fetch alerts.
        :return: {list} The list of Alerts.
        """
        request_url = self._get_full_url("get_alerts")
        params = {
            "duration": duration,
            "info_level": "extended",
            "start_time": self._convert_datetime_to_api_format(start_time),
        }
        response = self.session.get(request_url, params=params)
        validate_response(response)
        alerts = self.parser.build_alerts_array(response.json())
        filtered_alerts = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=alerts,
            existing_ids=existing_ids,
            id_key=ALERT_ID_FIELD,
        )
        return sorted(filtered_alerts, key=lambda alert: alert.occurred_time_unix)

    @staticmethod
    def _convert_datetime_to_api_format(time):
        """
        Convert datetime object to the API time format of EX
        :param time: {datetime.Datetime} The datetime object
        :return: {unicode} The formatted time string
        """
        base_time, miliseconds_zone = time.strftime(API_TIME_FORMAT).split(".")
        return f"{base_time}.{miliseconds_zone[:3] + miliseconds_zone[-6:]}"

    def create_ips_policy_exception(
        self,
        policy_name: str,
        policy_mode: str,
        interface: str,
        victim_ip_subnet: str,
        attacker_ip: str,
    ):
        """
        Create an IP policy exception.
        :param policy_name: {str} policy exception name
        :param policy_mode: {str} policy exception mode. Values can be block, unblock, suppress, suppress-unblock
        :param interface: {str} what interface should be used in policy exception. Values can be A, B, C, D, ALL
        :param victim_ip_subnet: {str} IP subnet of the victim that should be used to create the new policy exception. Example: 10.0.0.1/24
        :param attacker_ip: {str} IP subnet of the attacker that should be used to create the new policy exception. Example: 100.10.10.3/32
        :return: raise Exception if failed to validate response
        """
        request_url = self._get_full_url("add_ip_policy_exception")
        payload = [
            {
                "name": policy_name,
                "interface": interface,
                "victim_ip": victim_ip_subnet,
                "action": policy_mode,
                "attacker_ip": attacker_ip,
            }
        ]
        response = self.session.post(request_url, json=payload)
        validate_response(
            response,
            error_msg=f"Failed to create IP policy exception {policy_name} with mode {policy_mode}",
        )
