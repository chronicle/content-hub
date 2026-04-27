from __future__ import annotations
from .McAfeeMvisionEDRV2Parser import McAfeeMvisionEDRV2Parser
from .UtilsManager import validate_response
import requests
from urllib.parse import urljoin
from .constants import INTEGRATION_DISPLAY_NAME, DEFAULT_SCOPES
from .exceptions import UnableToGetTokenException


ENDPOINTS = {"login": "/iam/v1.0/token", "investigations": "/edr/v2/investigations"}


class McAfeeMvisionEDRV2Manager:
    def __init__(
        self,
        api_root,
        iam_root,
        client_id,
        client_secret,
        api_key,
        scopes=DEFAULT_SCOPES,
        verify_ssl=False,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: McAfee Mvision ePO API Root
        :param client_id: Client ID of the McAfee Mvision ePO account
        :param client_secret: Client Secret of the McAfee Mvision ePO account
        :param api_key: Api Key of the McAfee Mvision ePO account
        :param scopes: Scopes of the McAfee Mvision ePO account
        :param verify_ssl: Enable (True) or disable (False). If enabled, verify the SSL certificate for the connection to the McAfee Mvision ePO public cloud server is valid.
        :param siemplify_logger: Siemplify logger.
        """
        self.api_root = api_root
        self.iam_root = iam_root
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_key = api_key
        self.scopes = scopes
        self.siemplify_logger = siemplify_logger

        self.parser = McAfeeMvisionEDRV2Parser()

        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers["x-api-key"] = self.api_key

        self.set_auth_token()

        self.session.headers["Content-Type"] = "application/vnd.api+json"

        self.already_loaded_devices = []
        self.all_devices_loaded = False

        # Because we are using one host for getting token, and another one for fetching data, we need to call
        # test_connectivity to be sure that the manager is able to fetch data
        self.test_connectivity()

    def set_auth_token(self):
        """
        Set Authorization header to request session.
        """
        self.session.headers.update({"Authorization": self.get_auth_token()})

    def get_auth_token(self):
        """
        Send request in order to get generated tokens.
        :return: {unicode} The Authorization Token to use for the next requests
        """
        try:
            login_response = self.session.get(
                self._get_full_url("login", self.iam_root),
                auth=(self.client_id, self.client_secret),
                params={"grant_type": "client_credentials", "scope": self.scopes},
            )
            validate_response(login_response)
            return self.parser.get_auth_token(login_response.json())
        except Exception as err:
            raise UnableToGetTokenException(f"{INTEGRATION_DISPLAY_NAME}: {err}")

    def _get_full_url(self, url_id, api_root=None):
        """
        Send full url from url identifier.
        :param api_root: {unicode} The api root
        :param url_id: {unicode} The id of url
        :return: {unicode} The full url
        """
        return urljoin(api_root or self.api_root, ENDPOINTS[url_id])

    def test_connectivity(self):
        """
        Test connectivity to the McAfee Mvision EDR.
        :return: {bool} True if successful, exception otherwise
        """
        # TODO: Currently there is no ping endpoint
        return True

    def create_ip_investigation(
        self,
        case_priority,
        case_type,
        case_name=None,
        case_hint=None,
        address=None,
        event_source=None,
    ):
        """
        Create an IP investigation
        :param case_name: {str} Gives the Guided Investigation a meaningful name. If the name is missing, a default case
            name is assigned. The value of this parameter appears in the MVISION EDR Investigating dashboard under the
            Investigation column.
        :param case_hint: {str} Automatically links related Guided Investigations and avoids creating many cases from
            multiple alerts related to the same incident. Although this parameter is optional, it is highly recommended.
        :param case_priority: {str} Assigns a priority to a Guided Investigation. Example: High, Medium, Low.
        :param case_type: {str} Defines the type of alert. Recognized values are malware and network. Any other value is
            treated as others. Example: Malware, Network
        :param address: {str} IP Address
        :param event_source: {str} Provides the SOC analyst a visual indicator that distinguishes between various
            sources of alerts. The value of this parameter appears in the MVISION EDR Investigating dashboard under the
            By column. Example: McAfeeESM, ArcSightESM, Splunk.
        :return: {str} The ID of the created investigation
        """
        attributes = {
            "caseName": case_name,
            "caseHint": case_hint or None,
            "casePriority": case_priority,
            "caseType": case_type,
            "evidenceType": "IP",
            "address": address,
            "eventSrc": event_source,
        }

        attributes = {k: v for k, v in attributes.items() if v is not None}

        payload = {"data": {"type": "investigations", "attributes": attributes}}
        url = self._get_full_url("investigations")
        response = self.session.post(url, json=payload)
        validate_response(response, "Failed to create investigation")
        return self.parser.build_siemplify_investigation(
            response.json().get("data", {})
        )

    def create_hostname_investigation(
        self,
        case_priority,
        case_type,
        case_name=None,
        case_hint=None,
        hostname=None,
        event_source=None,
    ):
        """
        Create a hostname investigation
        :param case_name: {str} Gives the Guided Investigation a meaningful name. If the name is missing, a default case
            name is assigned. The value of this parameter appears in the MVISION EDR Investigating dashboard under the
            Investigation column.
        :param case_hint: {str} Automatically links related Guided Investigations and avoids creating many cases from
            multiple alerts related to the same incident. Although this parameter is optional, it is highly recommended.
        :param case_priority: {str} Assigns a priority to a Guided Investigation. Example: High, Medium, Low.
        :param case_type: {str} Defines the type of alert. Recognized values are malware and network. Any other value is
            treated as others. Example: Malware, Network
        :param hostname: {str} Hostname
        :param event_source: {str} Provides the SOC analyst a visual indicator that distinguishes between various
            sources of alerts. The value of this parameter appears in the MVISION EDR Investigating dashboard under the
            By column. Example: McAfeeESM, ArcSightESM, Splunk.
        :return: {str} The ID of the created investigation
        """
        attributes = {
            "caseName": case_name,
            "caseHint": case_hint,
            "casePriority": case_priority,
            "caseType": case_type,
            "evidenceType": "Device",
            "hostName": hostname,
            "eventSrc": event_source,
        }

        attributes = {k: v for k, v in attributes.items() if v is not None}

        payload = {"data": {"type": "investigations", "attributes": attributes}}
        url = self._get_full_url("investigations")
        response = self.session.post(url, json=payload)
        validate_response(response, "Failed to create investigation")
        return self.parser.build_siemplify_investigation(
            response.json().get("data", {})
        )
