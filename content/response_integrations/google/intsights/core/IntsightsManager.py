from __future__ import annotations
import requests
from urllib.parse import urljoin

from soar_sdk.SiemplifyUtils import convert_string_to_unix_time

from .exceptions import (
    IntsightsManagerError,
    AlertNotFoundError,
    UserNotFoundError,
    ChangeAssigneeError,
    BadCredentialsError,
    NotFoundError,
)

from .consts import (
    SUBMIT_REMEDIATION_EVIDENCE_URL,
    ACTION_TYPE_USER,
    ACTION_TYPE_ALERT,
    TAKEDOWN_REQUEST_URL,
)
from .IntsightsParser import IntsightsParser


API_ENDPOINTS = {
    "ping": "public/v1/api/version",
    "ask_an_analyst": "public/v1/data/alerts/ask-the-analyst/{alert_id}",
    "get_user_details": "public/v1/account/users-details",
    "assign_alert": "public/v1/data/alerts/assign-alert/{alert_id}",
    "close_alert": "public/v1/data/alerts/close-alert/{alert_id}",
    "reopen_alert": "public/v1/data/alerts/reopen-alert/{alert_id}",
    "get_alert_image": "public/v1/data/alerts/alert-image/{alert_image_id}",
    "submit_file_evidence": "public/v1/data/alerts/csv-file/{alert_id}",
    "get_iocs": "public/v3/iocs/ioc-by-value",
    "alerts_list": "public/v1/data/alerts/alerts-list",
    "get_alert_by_id": "public/v1/data/alerts/get-complete-alert/{alert_id}",
    "add_alert_note": "public/v1/data/alerts/add-note/{alert_id}",
}


HEADERS = {"Content-Type": "application/json"}


class IntsightsManager:
    """
    IntSights Manager
    """

    def __init__(
        self,
        server_address,
        account_id,
        api_key,
        api_login=False,
        verify_ssl=False,
        force_check_connectivity=False,
        siemplify=None,
    ):
        self.server_address = self._get_adjusted_root_url(server_address)
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        self.session.auth = (account_id, api_key)
        self.parser = IntsightsParser()
        self.siemplify = siemplify
        if force_check_connectivity:
            self.test_connectivity()

    @staticmethod
    def _get_adjusted_root_url(api_root):
        return api_root if api_root[-1] == r"/" else f"{api_root}/"

    @staticmethod
    def _get_url(url_id, **kwargs):
        """
        Get url from url identifier.
        :param url_id: {str} The id of url
        :param general_api: {bool} whether to use general api or not
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The url
        """
        return API_ENDPOINTS[url_id].format(**kwargs)

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param general_api: {bool} whether to use general api or not
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.server_address, self._get_url(url_id, **kwargs))

    def test_connectivity(self):
        """
        Test connectivity to Intsights
        :return: {bool} True if successfully connected, Exception otherwise.
        """
        res = self.session.get(self._get_full_url("ping"))
        self.validate_response(res, f"Unable to connect to {self.server_address}")

        return True

    def search_iocs(self, free_text=None):
        """
        Search for IOCs
        :param free_text: {str} Free text to search for
        :return: {JSON} THe found IOC data
        """
        res = self.session.get(
            self._get_full_url("get_iocs"), params={"iocValue": free_text}
        )
        self.validate_response(res, f"Unable to search IOCs for {free_text}")

        if res.content:
            return self.parser.build_iocs_object(res.json())

        return []

    def get_alerts(
        self,
        limit,
        date_from=0,
        date_to=None,
        severities=None,
        alert_types=None,
        network_types=None,
        sources=None,
        assigned=None,
        is_closed=False,
    ):
        """
        Get alerts
        :param existing_ids: {list} List of already seen alert ids
        :param limit: {int} Max alerts to return
        :param date_from: {int} Start date to fetch from in Unix Millisecond Timestamp
        :param date_to: {int} End date to fetch to in Unix Millisecond Timestamp
        :param severities: {list} Alert's severities. Allowed values:
            "High", "Medium", "Low"
        :param alert_types: {list} Alert's types. Allowed values:
            "AttackIndication", "DataLeakage", "Phishing", "BrandSecurity",
            "ExploitableData", "vip"
        :param network_types: {list} Alert's network types. Allowed values:
            "ClearWeb", "DarkWeb"
        :param sources: {list} Alert's source types. Allowed values:
            "ApplicationStores", "BlackMarkets", "HackingForums",
            "SocialMedia", "PasteSites", "Others"
        :param assigned: {bool} Show only assigned alerts
        :param is_closed: {bool} Show closed/open alerts. Default: False
        :return: {list} Alerts.
        """
        params = {
            "foundDateFrom": date_from,
            "foundDateTo": date_to,
            "severity": ",".join(severities) if severities else None,
            "alertType": ",".join(alert_types) if alert_types else None,
            "networkType": ",".join(network_types) if network_types else None,
            "sourceType": ",".join(sources) if sources else None,
            "assigned": assigned,
            "isClosed": is_closed,
        }

        params = {k: v for k, v in params.items() if v is not None}

        res = self.session.get(self._get_full_url("alerts_list"), params=params)
        self.validate_response(res, "Unable to get alerts")
        alerts = []

        if not res.content:
            return alerts

        alert_ids = res.json()

        for alert_id in alert_ids:
            alerts.append(self.get_alert_by_id(alert_id))

        return sorted(
            alerts,
            key=lambda alert: (
                convert_string_to_unix_time(alert.found_date) if alert.found_date else 1
            ),
        )[:limit]

    def get_alert_by_id(self, alert_id):
        """
        Get alert full details by ID
        :param alert_id: {str} The ID of the alert
        :return: {dict} Details of the alert
        """
        res = self.session.get(self._get_full_url("get_alert_by_id", alert_id=alert_id))
        self.validate_response(res, f"Unable to get alert {alert_id}")

        return self.parser.build_alert_obj(res.json())

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            if response.status_code == 401:
                raise BadCredentialsError(response.content)

            response.raise_for_status()

        except requests.HTTPError as error:
            raise IntsightsManagerError(
                f"{error_msg}: {error} {error.response.content}"
            )

    @staticmethod
    def validate_response_customized(
        response, error_msg="An error occurred", action_type=None
    ):
        try:
            if response.status_code == 404 and action_type == ACTION_TYPE_ALERT:
                raise NotFoundError(response.content)

            if response.status_code == 400 and action_type == ACTION_TYPE_ALERT:
                raise AlertNotFoundError(response.content)

            if response.status_code == 400 and action_type == ACTION_TYPE_USER:
                raise UserNotFoundError(response.content)

            if response.status_code == 500 and action_type == ACTION_TYPE_ALERT:
                raise ChangeAssigneeError(response.content)

            if response.status_code == 204:
                raise IntsightsManagerError(f"{'Content Not Found in Intsight'}")

            if response.status_code == 401:
                raise BadCredentialsError(response.content)

            response.raise_for_status()

        except requests.HTTPError as error:
            raise IntsightsManagerError(
                f"{error_msg}: {error} {error.response.content}"
            )

    def close_alert(self, alert_id, reason, additional_information=None, rate=None):
        """
        Function that closes an alert in Intsight
        :param alert_id: {str} ID of an alert that should be closed
        :param additional_information {str} Additional information about the reason for closure
        :param rate {int} Rate of an alert
        :param reason {str} Reason for alert closure
        """
        payload = {"Reason": reason, "FreeText": additional_information, "Rate": rate}
        payload = {key: value for key, value in payload.items() if value is not None}

        res = self.session.patch(
            self._get_full_url("close_alert", alert_id=alert_id), json=payload
        )
        self.validate_response_customized(
            res, f"Unable to get alert {alert_id}", action_type=ACTION_TYPE_ALERT
        )

    def get_user_details(self, assignee_email):
        """
        Function that gets the details of an assignee email
        :param assignee_email {str} Assignee Email for which we need details
        :return {JSON} Returns a json response of the details of the user
        """
        params = {"userEmail": assignee_email}

        res = self.session.get(self._get_full_url("get_user_details"), params=params)
        self.validate_response_customized(
            res,
            f"Unable to get ID of the assignee {assignee_email}",
            action_type=ACTION_TYPE_USER,
        )

        return res.json()

    def assign_alert(self, alert_id, assignee_id):
        """
        Function that assignees an alert in Intsight to an assignee
        :param alert_id: {str} ID of an alert that should be reassigned
        :param assignee_id {str} Assignee ID of the new assignee
        """
        payload = {"AssigneeID": assignee_id}

        res = self.session.patch(
            self._get_full_url("assign_alert", alert_id=alert_id), json=payload
        )
        self.validate_response_customized(
            res,
            f"Unable to assign alert {alert_id} to {assignee_id}",
            action_type=ACTION_TYPE_ALERT,
        )

    def ask_an_analyst(self, alert_id, comment):
        """
        Function that activates the Ask An Analyst feature
        :param alert_id: {str} ID of an alert that should be using in ask an analyst request
        :param comment: {str} Comment is a question to ask
        """
        payload = {"Question": comment}

        res = self.session.post(
            self._get_full_url("ask_an_analyst", alert_id=alert_id), json=payload
        )
        self.validate_response_customized(
            res, f"General Error Occured. {alert_id}.", action_type=ACTION_TYPE_ALERT
        )

    def takedown_request(self, alert_id):
        """
        Funtion that takes down an alert by alert ID.
        :param alert_id: {str} ID of an alert that should be takendown
        """

        url = TAKEDOWN_REQUEST_URL.format(self.server_address, alert_id)

        res = self.session.patch(url)
        self.validate_response_customized(
            res, f"General Error Occured. {alert_id}.", action_type=ACTION_TYPE_ALERT
        )

    def reopen_alert(self, alert_id):
        """
        Function that reopens an alert in Intsight
        :param alert_id: {str} ID of an alert that should be reopened
        """
        res = self.session.patch(self._get_full_url("reopen_alert", alert_id=alert_id))
        self.validate_response_customized(
            res, f"Unable to get alert {alert_id}", action_type=ACTION_TYPE_ALERT
        )

    def get_alert_image(self, alert_image_id):
        """
        Function that gets the alert image based on ID in Intsight
        :param alert_image_id: {str} ID of an alert image that should be fetched from the Intsight
        :return {Response.content} Raw response content
        """
        res = self.session.get(
            self._get_full_url("get_alert_image", alert_image_id=alert_image_id)
        )
        self.validate_response_customized(
            res, f"Unable to get alert image with ID {alert_image_id}."
        )

        return res.content  # raw content from the request is the image content

    def submit_evidence_file(
        self, alert_id, file_name, evidence_file_path, file_format
    ):
        """
        Function that submits evidence file to Intsight
        :param alert_id: {str} ID of an alert image for which the evidence is submitted to Intsight
        :param file_name: {str} Name of the file
        :param evidence_file_path: {str} Path to the evidence file
        :param file_format: {str} File Format
        """

        url = SUBMIT_REMEDIATION_EVIDENCE_URL.format(
            self.server_address, alert_id, file_name
        )
        self.session.headers = {"Content-Type": f"application/{file_format}"}

        file = open(evidence_file_path, "rb")
        files = {"file": file}

        res = self.session.post(url, files=files)
        self.validate_response_customized(
            res, f"Unable to find alert with ID {alert_id}."
        )

    def download_alert_csv(self, alert_id):
        """
        Function that downloads alert csv
        :param alert_id: {str} ID of an alert
        """
        res = self.session.get(
            self._get_full_url("submit_file_evidence", alert_id=alert_id)
        )
        self.validate_response_customized(
            res,
            f"Unable to find alert with ID {alert_id}.",
            action_type=ACTION_TYPE_ALERT,
        )
        return res

    def add_alert_note(self, alert_id: str, note: str) -> None:
        """
        Adds note to the alert with given alert_id
        Args:
            alert_id: ID of alert
            note: Note to add to the alert
        Returns:
            None
        """
        url = self._get_full_url("add_alert_note", alert_id=alert_id)
        payload = {"Note": note}

        response = self.session.post(url, json=payload)
        self.validate_response_customized(
            response,
            f"Unable to add note to alert {alert_id}",
            action_type=ACTION_TYPE_ALERT,
        )
