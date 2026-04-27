from __future__ import annotations
import requests
from .APIVoidTranslationLayer import APIVoidTranslationLayer

INVALID_API_KEY_ERROR = "API key is not valid"

# ============================= CLASSES ===================================== #


class APIVoidManagerError(Exception):
    """
    General Exception for APIVoid manager
    """


class APIVoidInvalidAPIKeyError(Exception):
    """
    Invalid API key for APIVoid manager
    """


class APIVoidNotFound(Exception):
    """
    Exception for notifying that reputation was not found by APIVoid
    """


class APIVoidManager:
    """
    APIVoid Manager
    """

    def __init__(self, api_root, api_key, verify_ssl=False):
        self.api_root = api_root
        self.api_key = api_key
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self._translation_layer = APIVoidTranslationLayer()

    def test_connectivity(self):
        """
        Test connectivity to IPVoid
        :return: {bool} True if successful, exception otherwise.
        """
        response = self.session.get(
            url=f"{self.api_root}/iprep/v1/pay-as-you-go/?stats",
            params={"key": self.api_key},
        )
        self.validate_response(response, "Unable to connect to APIVoid")
        return True

    def get_ip_reputation(self, ip):
        """
        Get IP Reputation
        :param ip: {str} The ip address
        :return: {dict} The reputation of the ip
        """
        response = self.session.post(
            url=f"{self.api_root}/iprep/v1/pay-as-you-go/",
            params={"ip": ip, "key": self.api_key},
        )
        self.validate_response(response, f"Unable to get reputation for {ip}")

        data = response.json().get("data", {}).get("report")

        if data:
            return self._translation_layer.build_ip_reputation_obj(data)

        raise APIVoidNotFound(f"No reputation was found for {ip}")

    def get_url_reputation(self, url):
        """
        Get URL Reputation
        :param url: {str} The url
        :return: {Reputation} The reputation of the url
        """
        response = self.session.post(
            url=f"{self.api_root}/urlrep/v1/pay-as-you-go/",
            params={"url": url, "key": self.api_key},
        )
        self.validate_response(response, f"Unable to get reputation for {url}")

        data = response.json().get("data", {}).get("report")

        if data:
            return self._translation_layer.build_url_reputation_obj(data)

        raise APIVoidNotFound(f"No reputation was found for {url}")

    def get_domain_reputation(self, domain):
        """
        Get domain reputation from URLVoid
        :param domain: {string} The domain
        :return: {dict} The reputation of the domain
        """
        response = self.session.get(
            url=f"{self.api_root}/domainbl/v1/pay-as-you-go/",
            params={"host": domain, "key": self.api_key},
        )

        self.validate_response(response, f"Unable to get reputation for {domain}")

        data = response.json().get("data", {}).get("report")

        if data:
            return self._translation_layer.build_domain_reputation_obj(data)

        raise APIVoidNotFound(f"No reputation was found for {domain}")

    def get_url_screenshot(self, url):
        """
        Get screenshot for a given URL
        :param url: {str} The url
        :return: {Screenshot} The screenshot details of the url
        """
        response = self.session.post(
            url=f"{self.api_root}/screenshot/v1/pay-as-you-go/",
            params={"url": url, "key": self.api_key},
        )
        self.validate_response(response, f"Unable to capture screenshot for {url}")

        data = response.json().get("data", {})

        if data:
            return self._translation_layer.build_screenshot_obj(data)

        raise APIVoidNotFound(f"No screenshot was captured for {url}")

    def get_email_info(self, email):
        """
        Get information for a given email
        :param email: {str} The email
        :return: {EmailInformation} The details of the email
        """
        response = self.session.post(
            url=f"{self.api_root}/emailverify/v1/pay-as-you-go/",
            params={"email": email, "key": self.api_key},
        )
        self.validate_response(response, f"Unable to get email information for {email}")

        data = response.json().get("data", {})

        if data:
            return self._translation_layer.build_email_information_obj(data)

        raise APIVoidNotFound(f"No information was found for {email}")

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                raise APIVoidManagerError(f"{error_msg}: {error} - {response.content}")

            raise APIVoidManagerError(
                f"{error_msg}: {error} - {response.json().get('error', 'No error message.')}"
            )

        if "error" in response.json():
            if response.json().get("error") == INVALID_API_KEY_ERROR:
                raise APIVoidInvalidAPIKeyError(
                    f"{error_msg}: {response.json().get('error')}"
                )

            raise APIVoidManagerError(f"{error_msg}: {response.json().get('error')}")
