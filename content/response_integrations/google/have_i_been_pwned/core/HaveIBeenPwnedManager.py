# ==============================================================================
# title           : HaveIBeenPwnedManager.py
# description     : HaveIBeenPwned to get data.
# author          : zivh@siemplify.co
# date            : 06-25-17
# python_version  : 2.7
# libraries       : -
# requirements    : HaveIBeenPwned
# product_version : v2
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import re
import urllib.parse
from .HIBPTranslationLayer import HIBPTranslationLayer


# =====================================
#              CONSTS                 #
# =====================================
BASE_URL = "https://haveibeenpwned.com/api/v3/{service}"

# Each request to the API must be accompanied by a user agent request header.
# Should be the name of the app consuming the service
HEADERS = {
    "user-agent": "*",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Not found: the account could not be found and has therefore not been pwned
NOT_FOUNT_RESPONSE_STATUS = 404
# Too many requests: the rate limit has been exceeded
RATE_LIMIT_RESPONSE_STATUS = 429
# Unauthorised: either no API key was provided or it wasn't valid
UNAUTHORISED_RESPONSE_STATUS = 401


ACCOUNT_BREACHES_SERVICE = "breachedaccount"
BREACHES_SERVICE = "breaches"
PASTE_SERVICE = "pasteaccount"

DOMAIN_REGEX = r"[a-zA-Z\d-]{,63}(\.[a-zA-Z\d-]{,63})+"
EMAIL_REGEX = r"^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$"

# =====================================
#              CLASSES                #
# =====================================


class HaveIBeenPwnedException(Exception):
    pass


class HaveIBeenPwnedManager:
    """
    Responsible for all Have I Been Pwned system operations functionality
    """

    def __init__(self, api_key, use_ssl=False):
        self.session = requests.Session()
        self.session.verify = use_ssl
        self.session.headers.update({"hibp-api-key": api_key})
        self._translation_layer = HIBPTranslationLayer()

    def test_connectivity(self):
        """
        Check connectivity by getting all breached sites in the system
        """
        self.get_all_breaches_for_an_account("test@gmail.com")

    @staticmethod
    def validate_email(email_address):
        """
        Check if the given email address is valid
        :param email_address: {string} email address
        :return: {bool} True if ok, else false.
        """
        email_regex = re.compile(EMAIL_REGEX)
        if not re.match(email_regex, email_address):
            # Invalid email address
            return False
        return True

    def get_all_pastes_for_an_account(self, account):
        """
        Setup request to retrieve all breaches on a particular account
        :param account: the email address to be searched for. Usernames that are not email addresses cannot be searched for.
        The account is NOT case sensitive and will be trimmed of leading or trailing white spaces. The account should always be URL encoded.
        :return: {list of dicts} all breaches a particular account has been involved in.
        """
        url = f"{BASE_URL.format(service=PASTE_SERVICE)}/{urllib.parse.quote(account)}"
        response = self.session.get(url)

        account_pastes = self.validate_response(response)
        if account_pastes:
            return [
                self._translation_layer.build_paste_obj(paste)
                for paste in account_pastes
            ]
        else:
            return []

    def get_all_breaches_for_an_account(self, account):
        """
        Setup request to retrieve all breaches on a particular account
        :param account: usernames/emails - the account to be searched for.
        The account is not case sensitive and will be trimmed of leading or trailing white spaces. The account should always be URL encoded.
        :return: {list} of dicts {breach data}
        """
        url = f"{BASE_URL.format(service=ACCOUNT_BREACHES_SERVICE)}/{urllib.parse.quote(account)}"

        # By default, only the name of the breach is returned rather than the complete breach data,
        # to get complete breach data returned (a non-truncated response) use the truncateResponse parameter
        response = self.session.get(url, params={"truncateResponse": "false"})

        account_breaches = self.validate_response(response)
        if account_breaches:
            return [
                self._translation_layer.build_breach_obj(breach)
                for breach in account_breaches
            ]
        else:
            return []

    def get_domain_breaches(self, domain):
        """
        Get breaches against the domain specified.
        A "breach" is an instance of a system having been compromised by an attacker and the data disclosed.
        :param domain: {string} domain you want to query. must be valid domain,according to RFC 1035. (e.g. Adobe)
        :return: {list of dicts} the details of the breach
        """
        domain_regex = re.compile(DOMAIN_REGEX)
        if not re.match(domain_regex, domain):
            raise HaveIBeenPwnedException(f"{domain} is an invalid domain.")
        url = BASE_URL.format(service=BREACHES_SERVICE)

        response = self.session.get(url, params={"domain": domain})
        return self.validate_response(response)

    @staticmethod
    def validate_response(response):
        """
        Check if request response is ok
        """
        try:
            if response.status_code == UNAUTHORISED_RESPONSE_STATUS:
                raise HaveIBeenPwnedException(
                    "Unauthorised: either no API key was provided or it wasn't valid"
                )
            elif (
                response.status_code == NOT_FOUNT_RESPONSE_STATUS
                or response.text == "[]"
            ):
                # object has not been pwned.
                return
            elif response.status_code == RATE_LIMIT_RESPONSE_STATUS:
                # Requests to the breaches APIs are limited to one per every 1500 milliseconds each.
                # Any request that exceeds the limit will receive an HTTP 429 "Too many requests" response.
                raise HaveIBeenPwnedException(
                    " Too many requests: The Rate Limit has been exceeded"
                )

            response.raise_for_status()
        except requests.HTTPError as e:
            raise HaveIBeenPwnedException(e)
        return response.json()
