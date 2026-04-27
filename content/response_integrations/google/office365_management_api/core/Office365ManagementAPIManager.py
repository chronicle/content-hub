from __future__ import annotations
import base64
import datetime
import time
import uuid
from urllib.parse import urljoin

import jwt
import requests

from .Office365ManagementAPIParser import Office365ManagementAPIParser
from OpenSSL import crypto
from soar_sdk.SiemplifyUtils import unix_now
from TIPCommon import filter_old_alerts
from .UtilsManager import validate_response, get_milliseconds_from_minutes
from .constants import (
    ENDPOINTS,
    HEADERS,
    MANAGE_API_ROOT,
    DEFAULT_LIMIT,
    CONNECTOR_DATETIME_FORMAT,
    GRANT_TYPE,
    CLIENT_ASSERTION_TYPE,
    ALERT_TYPES,
    ALERT_CONTENT_TYPE,
)


class Office365ManagementAPIManager:
    def __init__(
        self,
        api_root,
        azure_active_directory_id,
        client_id,
        client_secret,
        oauth2_login_endpoint_url,
        verify_ssl,
        certificate_path,
        certificate_password=None,
        siemplify=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} Api root url to use with integration.
        :param azure_active_directory_id: {str} Azure Active Directory Tenant ID
        :param client_id: {str} Client ID for the app registration in Azure Active Directory
        :param client_secret: {str} Client Secret for Azure Active Directory app registration
        :param oauth2_login_endpoint_url: {str} Specifies OAUTH2 Login Endpoint Url
        :param verify_ssl: {bool} Specify whether remote API endpoint SSL certificate should be validated.
        :param certificate_path: {str} Certificate Path to .pfx file
        :param certificate_password {str} Password for certificate
        """
        self.api_root = api_root
        self.azure_active_directory_id = azure_active_directory_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.oauth2_login_endpoint_url = oauth2_login_endpoint_url
        self.verify_ssl = verify_ssl
        if siemplify is not None:
            self.siemplify = siemplify
        self.parser = Office365ManagementAPIParser()
        self.session = requests.session()
        self.session.headers = HEADERS
        self.session.verify = verify_ssl

        self.certificate_path = certificate_path
        self.certificate_password = certificate_password

        if not self.certificate_path and not self.client_secret:
            raise Exception(
                "Either Certificate Path or Client Secret has to be specified."
            )

        self.set_auth_token()

    def set_auth_token(self):
        """
        Set Authorization header to request session.
        """
        self.session.headers.update(
            {"Authorization": f"Bearer {self.generate_token()}"}
        )

    def generate_token(self):
        """
        Function that generated tokens based on the auth method provided.
        :return: {str} The authorization token
        """

        if self.client_secret:
            return self.get_auth_token()

        else:
            return self.generate_token_by_certificate()

    def get_auth_token(self):
        """
        Send request to get authorization token.
        :return: {str} The authorization token
        """
        url = self._get_full_url(
            self.oauth2_login_endpoint_url,
            "get_token",
            directory_id=self.azure_active_directory_id,
        )

        payload = {
            "grant_type": "client_credentials",
            "resource": self.api_root,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        response = self.session.post(url, data=payload)
        validate_response(response)
        return self.parser.get_auth_token(response.json())

    def generate_token_by_certificate(self):
        """
        Request access token by certificate (Valid for 60 min)
        :return: {string} Access token. The app can use this token in calls to Office365 API
        """

        thumbprint, private_key = self.get_certificate_thumbprint_and_private_key(
            self.certificate_path, self.certificate_password
        )
        jwt_token = self.get_jwt_token(self.client_id, thumbprint, private_key)

        params = {
            "grant_type": GRANT_TYPE,
            "resource": self.api_root,
            "client_id": self.client_id,
            "client_assertion_type": CLIENT_ASSERTION_TYPE,
            "client_assertion": jwt_token,
        }

        url = self._get_full_url(
            self.oauth2_login_endpoint_url,
            "get_token",
            directory_id=self.azure_active_directory_id,
        )
        response = self.session.post(url, data=params)
        validate_response(response)
        return response.json().get("access_token")

    def get_certificate_thumbprint_and_private_key(
        self, certificate_path, certificate_password
    ):
        """
        Get thumbprint and private key from certificate
        :param certificate_path: {string} If authentication based on certificates is used instead of client secret, specify path to the certificate on Siemplify server
        :param certificate_password: {string} If certificate is password-protected, specify the password to open the certificate file
        :return: {tuple} The certificate thumbprint and private key
        """
        try:
            with open(certificate_path, "rb") as pfx:
                certificate = crypto.load_pkcs12(pfx.read(), certificate_password)
                private_key_object = certificate.get_privatekey()
                x509_certificate = certificate.get_certificate()
                thumbprint_bytes = x509_certificate.digest("sha1")
                # Remove colons from thumbprint
                thumbprint = thumbprint_bytes.decode("utf-8").replace(":", "")
                private_key = crypto.dump_privatekey(
                    crypto.FILETYPE_PEM, private_key_object
                )

                return thumbprint, private_key
        except Exception:
            raise

    def get_jwt_token(self, client_id, thumbprint, private_key):
        """
        Get JWT token
        :param client_id: {string} The Application ID that the registration portal
        :param thumbprint: {string} The certificate thumbprint
        :param private_key: The certificate private key
        :return: {bytes} The JWT token
        """

        # Encode hex to Base64
        encoded_thumbprint = base64.b64encode(bytes.fromhex(thumbprint)).decode("utf-8")
        # Perform base64url-encoding as per RFC7515 Appendix C
        x5t = encoded_thumbprint.replace("=", "").replace("+", "-").replace("/", "_")
        current_timestamp = int(time.time())

        payload = {
            "aud": self._get_full_url(
                self.oauth2_login_endpoint_url,
                "get_token",
                directory_id=self.azure_active_directory_id,
            ),
            "exp": current_timestamp + 3600,
            "iss": client_id,
            "jti": str(uuid.uuid1()),
            "nbf": current_timestamp,
            "sub": client_id,
        }

        jwt_token = jwt.encode(
            payload, private_key, algorithm="RS256", headers={"x5t": x5t}
        )
        return jwt_token.decode("utf-8")

    def _get_full_url(self, api_root, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param api_root: {str} The api root
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(api_root, ENDPOINTS[url_id].format(**kwargs))

    def start_subscription(self, subscription_type):
        """
        Function that starts a subscription in O365 Management API
        :param subscription_type {str} Type of the subscription/Content Type
        """
        url = self._get_full_url(
            MANAGE_API_ROOT,
            "start_subscription",
            directory_id=self.azure_active_directory_id,
            content_type=subscription_type,
        )

        response = self.session.post(url)
        validate_response(response)

    def stop_subscription(self, subscription_type):
        """
        Function that stops a subscription in O365 Management API
        :param subscription_type {str} Type of the subscription/Content Type
        """
        url = self._get_full_url(
            MANAGE_API_ROOT,
            "stop_subscription",
            directory_id=self.azure_active_directory_id,
            content_type=subscription_type,
        )

        response = self.session.post(url)
        validate_response(response)

    def get_alerts(
        self,
        existing_ids,
        limit,
        start_timestamp,
        time_interval,
        events_padding_period,
        mask_findings=False,
        alert_type=ALERT_TYPES["dlp"],
    ):
        """
        Get DLP alerts from Office365 Management API
        :param existing_ids: {list} The list of existing ids.
        :param limit: {int} The limit for alerts.
        :param start_timestamp: {int} Timestamp for oldest alert to fetch.
        :param time_interval: {int} Time interval to split fetching time.
        :param events_padding_period: {int} Period for minimum time interval that will be used
        :param mask_findings: {bool} Specify whether the connector should mask sensitive findings or no
        :param alert_type: {str} Specifies what type of alerts should be fetched
        :return: {list} List of filtered Alert objects.
        """
        limit = max(limit, DEFAULT_LIMIT)
        data_blobs = self.get_data_blobs(
            start_timestamp, events_padding_period, time_interval, alert_type
        )
        alerts = []

        for data_blob in data_blobs:
            if len(alerts) < limit:
                alerts.extend(
                    self.get_alerts_from_data_blob(
                        data_blob, existing_ids, mask_findings, alert_type
                    )
                )

        return alerts[:limit]

    def get_data_blobs(
        self, start_timestamp, events_padding_period, time_interval, alert_type
    ):
        """
        Get data blobs containing alerts
        :param start_timestamp: {int} Timestamp for oldest alert to fetch.
        :param events_padding_period: {int} Period for minimum time interval that will be used
        :param time_interval: {int} Time interval to split fetching time.
        :param alert_type: {str} Specifies what type of alerts should be fetched
        :return: {list} List of DataBlob objects.
        """
        url = self._get_full_url(
            self.api_root, "get_data_blobs", directory_id=self.azure_active_directory_id
        )
        start_timestamp, start_datetime = self.build_start_time_filter(
            start_timestamp, events_padding_period
        )

        params = {
            "contentType": ALERT_CONTENT_TYPE[alert_type],
            "startTime": start_datetime,
            "endTime": self.build_end_time_filter(start_timestamp, time_interval),
        }

        return self.parser.get_data_blobs(self.get_data_blobs_by_url(url, params))

    def get_data_blobs_by_url(self, url, params=None):
        """
        Get data blobs by url
        :param url: {str} Url to get data blobs.
        :param params: {dict} Parameter for request
        :return: {dict} Response raw data.
        """
        response = self.session.get(url=url, params=params)
        validate_response(response)
        return response.json()

    def build_start_time_filter(self, start_timestamp, events_padding_period):
        """
        Build start time filter.
        :param start_timestamp: {int} Timestamp for oldest alert to fetch.
        :param events_padding_period: {int} Period for minimum time interval that will be used
        :return: {tuple} timestamp, datetime string
        """
        events_padding_period_in_milliseconds = get_milliseconds_from_minutes(
            events_padding_period
        )

        if unix_now() - start_timestamp < events_padding_period_in_milliseconds:
            start_timestamp = unix_now() - events_padding_period_in_milliseconds

        return start_timestamp, datetime.datetime.utcfromtimestamp(
            start_timestamp / 1000
        ).strftime(CONNECTOR_DATETIME_FORMAT)

    def build_end_time_filter(self, start_timestamp, time_interval):
        """
        Build end time filter.
        :param start_timestamp: {int} Timestamp for oldest alert to fetch.
        :param time_interval: {int} Time interval to split fetching time.
        :return: {str} datetime string
        """
        time_interval_in_milliseconds = get_milliseconds_from_minutes(time_interval)
        return datetime.datetime.utcfromtimestamp(
            (start_timestamp + time_interval_in_milliseconds) / 1000
        ).strftime(CONNECTOR_DATETIME_FORMAT)

    def get_alerts_from_data_blob(
        self, data_blob, existing_ids, mask_findings, alert_type
    ):
        """
        Get alerts from data blob
        :param siemplify: {SiemplifyConnectorExecutor} Siemplify connector executor instance
        :param data_blob: {list} The DataBlob object.
        :param existing_ids: {list} The list of existing ids.
        :param mask_findings: {bool} Specify whether the connector should mask sensitive findings or no
        :param alert_type: {str} Specifies alerts type
        :return: {list} List of filtered Alert objects.
        """
        response = self.session.get(url=data_blob.url)
        validate_response(response)
        alerts = []

        if alert_type == ALERT_TYPES["dlp"]:
            alerts = self.parser.build_alerts(response.json(), mask_findings)
        if alert_type == ALERT_TYPES["audit_general"]:
            alerts = self.parser.build_audit_general_alerts(response.json())

        filtered_alerts = filter_old_alerts(self.siemplify, alerts, existing_ids, "id")
        return sorted(filtered_alerts, key=lambda alert: alert.creation_time)
