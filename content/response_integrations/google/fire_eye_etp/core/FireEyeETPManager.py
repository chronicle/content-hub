from __future__ import annotations
from .FireEyeETPParser import FireEyeETPParser
import requests
from urllib.parse import urljoin

from .UtilsManager import validate_response

from .FireEyeETPConstants import ENDPOINTS, HEADERS, API_TIME_FORMAT, DEFAULT_FETCH_SIZE


class FireEyeETPManager:

    def __init__(self, api_root, api_key, verify_ssl=False, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param api_root: API Root of the FireEye ETP instance.
        :param api_key: API key of the FireEye ETP account.
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the FireEye ETP server is valid.
        :param siemplify_logger: Siemplify logger.
        """
        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.api_key = api_key
        self.siemplify_logger = siemplify_logger
        self.parser = FireEyeETPParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        self.session.headers.update({"x-fireeye-api-key": self.api_key})

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity to the FireEye ETP.
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("test_connectivity")
        payload = {"size": 1}
        response = self.session.post(request_url, json=payload)
        validate_response(response, "Unable to connect to FireEye ETP.")

    def get_alerts(self, start_time, timezone_offset):
        """
        Get alerts
        :param start_time: {str} Specifies the start time of the search.
        :param timezone_offset: {str} UTC timezone offset
        :return: {[Alert]} List of found alerts
        """
        request_url = self._get_full_url("get_alerts")
        start_time = self._convert_datetime_to_api_format(start_time)
        payload = {"fromLastModifiedOn": start_time, "size": DEFAULT_FETCH_SIZE}
        response = self.session.post(request_url, json=payload)
        validate_response(response, "Unable to get alerts")
        return self.parser.build_alerts_array(
            raw_json=response.json(), timezone_offset=timezone_offset
        )

    def get_alert_details(self, alert_id, timezone_offset):
        """
        Get alert details by id
        :param alert_id: {str} Id of the alert
        :param timezone_offset: {str} UTC timezone offset
        :return: {Alert} Detailed alert
        """
        request_url = self._get_full_url("get_alert_details", alert_id=alert_id)
        response = self.session.get(request_url)
        validate_response(response, "Unable to get alert details")
        return self.parser.build_first_alert(
            raw_data=response.json(), timezone_offset=timezone_offset
        )

    @staticmethod
    def _convert_datetime_to_api_format(time):
        """
        Convert datetime object to the API time format of ETP
        :param time: {datetime.Datetime} The datetime object
        :return: {unicode} The formatted time string
        """
        base_time, miliseconds_zone = time.strftime(API_TIME_FORMAT).split(".")
        return f"{base_time}.{miliseconds_zone[:3]}"
