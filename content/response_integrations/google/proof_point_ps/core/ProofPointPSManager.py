# ============================================================================#
# title           :ProofPointPSManager.py
# description     :This Module contain all ProofPoint Protection Server operations functionality
# author          :avital@siemplify.co
# date            :10-10-2018
# python_version  :2.7
# libreries       :requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations
import requests
import arrow

# ============================== CONSTS ===================================== #

HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) '
                  'Gecko/20100101 Firefox/50.0'
}
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# ============================= CLASSES ===================================== #


class ProofPointPSManagerError(Exception):
    """
    General Exception for ProofPoint PS manager
    """

    pass


class ProofPointPSManager:
    """
    ProofPoint PS Manager
    """

    def __init__(self, server_address, username, password, verify_ssl=False):
        self.server_address = server_address
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        self.session.auth = (username, password)

    def test_connectivity(self):
        """
        Test connectivity to ProofPoint PS
        :return: {bool} True if successful, exception otherwise.
        """
        self.search(sender="*")
        return True

    def search(
        self,
        sender=None,
        recipient=None,
        subject=None,
        start_date=None,
        end_date=None,
        folder=None,
    ):
        """
        Search for quarantine messages with the specified parameters.
        :param sender: {str} The sender of the message. Envelope message sender
        equals, starts with, ends with or is in a domain such as "bar.com"
        :param recipient: {str} The recipient of the message.
        :param subject: {str} The subject of the message.
        :param start_date: {str} The UTC start date of the date/time range
        (%Y-%m-%d %H:%M:%S). Defaults to last 24h.
        :param end_date: {str} The UTC end date of the date/time range
        (%Y-%m-%d %H:%M:%S)
        :param folder: The quarantine folder name. Defaults to "Quarantine".
        :return:
        """
        url = f"{self.server_address}/rest/v1/quarantine"

        data = {
            "from": sender,
            "rcpt": recipient,
            "subject": subject,
            "startdate": start_date,
            "enddate": end_date,
            "folder": folder,
        }

        data = {k: v for k, v in data.items() if v}
        response = self.session.get(url, params=data)

        self.validate_response(response, "Unable to search emails.")
        return response.json().get("records")

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            raise ProofPointPSManagerError(
                f"{error_msg}: {error} - {error.response.content}"
            )
