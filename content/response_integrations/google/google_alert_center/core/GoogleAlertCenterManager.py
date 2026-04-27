from __future__ import annotations
import datetime
import json
from urllib.parse import urljoin
from .constants import (
    ENDPOINTS,
    GOOGLE_APIS_ALERTS_ROOT,
    SCOPES,
    CONNECTOR_DATETIME_FORMAT,
    DEFAULT_MAX_LIMIT,
)
from .UtilsManager import validate_response, parse_string_to_dict, encode_sensitive_data
from .GoogleAlertCenterParser import GoogleAlertCenterParser
from google.oauth2 import service_account
from googleapiclient import _auth
from TIPCommon import filter_old_alerts
from .GoogleAlertCenterExceptions import AlertNotFoundException


class GoogleAlertCenterManager:
    def __init__(
        self,
        service_account_json_secret,
        impersonation_email_address,
        verify_ssl,
        siemplify=None,
    ):
        """
        The method is used to init an object of Manager class
        :param service_account_json_secret: {str} json string that contains the secret of service account keys
        :param impersonation_email_address: {str} email address that has access to the alert center
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.service_account_json_secret = service_account_json_secret
        self.service_account_json = parse_string_to_dict(
            self.service_account_json_secret
        )
        self.impersonation_email_address = impersonation_email_address
        self.verify_ssl = verify_ssl
        self.siemplify = siemplify
        self.parser = GoogleAlertCenterParser()
        self.http_client = None
        self._prepare_http_client()
        self.sensitive_data_arr = [self.impersonation_email_address]

    def _get_full_url(self, api_root, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param api_root: {str} api root
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(api_root, ENDPOINTS[url_id].format(**kwargs))

    def _prepare_http_client(self):
        """
        Prepare http client
        :return: {void}
        """
        credentials = service_account.Credentials.from_service_account_info(
            self.service_account_json, scopes=SCOPES
        )
        credentials = credentials.with_subject(self.impersonation_email_address)
        self.http_client = _auth.authorized_http(credentials)
        self.http_client.http.disable_ssl_certificate_validation = not self.verify_ssl

    def test_connectivity(self):
        """
        Test connectivity
        """
        url = self._get_full_url(GOOGLE_APIS_ALERTS_ROOT, "ping", limit=1)
        try:
            response_info, content = self.http_client.request(url, "GET")
        except Exception as e:
            raise Exception(encode_sensitive_data(str(e), self.sensitive_data_arr))

        validate_response(
            response_info, content, sensitive_data_arr=self.sensitive_data_arr
        )

    def get_alerts(self, existing_ids, limit, start_timestamp):
        """
        Get alerts
        :param existing_ids: {list} The list of existing ids
        :param limit: {int} The limit for results
        :param start_timestamp: {int} The timestamp for oldest alert to fetch
        :return: {list} The list of filtered Alert objects
        """
        url = self._get_full_url(
            GOOGLE_APIS_ALERTS_ROOT,
            "alerts",
            limit=max(limit, DEFAULT_MAX_LIMIT),
            timestamp=self.get_formatted_date_from_timestamp(start_timestamp),
        )
        try:
            response_info, content = self.http_client.request(url, "GET")
        except Exception as e:
            raise Exception(encode_sensitive_data(str(e), self.sensitive_data_arr))
        content = json.loads(content)
        validate_response(
            response_info, content, sensitive_data_arr=self.sensitive_data_arr
        )
        alerts = self.parser.build_alert_objects(content)
        return filter_old_alerts(self.siemplify, alerts, existing_ids, "id")

    @staticmethod
    def get_formatted_date_from_timestamp(timestamp):
        """
        Format timestamp to date string with specific format
        :param timestamp: {int} timestamp to format
        :return: {str} formatted date string
        """
        return f"{datetime.datetime.fromtimestamp(timestamp / 1000).strftime(CONNECTOR_DATETIME_FORMAT)}Z"

    def delete_alert(self, alert_id):
        """
        Delete Alert
        :param alert_id: {str} The id of the alert to delete
        """
        url = self._get_full_url(
            GOOGLE_APIS_ALERTS_ROOT, "delete_alert", alert_id=alert_id
        )
        response_info, content = self.http_client.request(url, "DELETE")
        if response_info.get("status", "") in [404, "404"]:
            raise AlertNotFoundException()
        validate_response(
            response_info, content, sensitive_data_arr=self.sensitive_data_arr
        )
