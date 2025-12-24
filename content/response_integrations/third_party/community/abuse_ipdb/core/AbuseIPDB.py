from __future__ import annotations

import requests

from .datamodels import IP

requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning,
)

URL_TYPE = "url"
DUMMY_IP_FOR_TEST = "1.1.1.1"

API_ROOT = "https://api.abuseipdb.com/api/v2/{0}"

# Scan IP messages indicators.
NO_DATA_FOUND_MESSAGE = "No Data Found"
RESOURCE_COULD_NOT_BE_FOUND_MESSAGE = "resource could not be found"
INVALID_MESSAGE = "Invalid"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# =====================================
#              CLASSES                #
# =====================================
class AbuseIPDBManagerError(Exception):
    """General Exception for AbuseIPDB manager"""


class AbuseIPDBLimitManagerError(Exception):
    """Limit Reached for AbuseIPDB manager"""


class AbuseIPDBInvalidAPIKeyManagerError(Exception):
    """Invalid API key exception for AbuseIPDB manager"""


class AbuseIPDBManager:
    def __init__(self, api_key, verify_ssl=True):
        self.api_key = api_key

    def validate_response(self, response, error_msg="An error occurred"):
        """Retrieve a report on a given url/file
        :param response: {dict} response from api call,
        :param error_msg: {string} message if response is not valid
        :return: {bool}
        """
        try:
            response.raise_for_status()

            if response.status_code == 204:
                # API limit reached
                raise AbuseIPDBLimitManagerError("Request rate limit exceeded")

        except requests.HTTPError as error:
            if response.status_code == 403:
                # Forbidden - no permission to resource.
                # You don't have enough privileges to make the request. You may be doing a request without providing
                # an API key or you may be making a request to a Private API without having the appropriate privileges.
                raise AbuseIPDBInvalidAPIKeyManagerError(
                    "Forbidden. You don't have enough privileges to make the request. You may be doing a request "
                    "without providing an API key or you may be making a request to a Private API without having "
                    "the appropriate privileges",
                )

            # Not a JSON - return content
            raise AbuseIPDBManagerError(
                f"{error_msg}: {error} - {error.response.content}",
            )

        return True

    def validate_max_days(self, max_days):
        if str(max_days).isdigit():
            return int(max_days)
        raise AbuseIPDBInvalidAPIKeyManagerError(
            'Failed to parse parameter. Please give a valid integer for the parameter"Max Age in Days"',
        )

    def test_connectivity(self):
        """Ping to server to be sure that connected
        :return: {bool}
        """
        max_days = 90
        return True if self.check_ip(DUMMY_IP_FOR_TEST, max_days) else False

    def check_ip(self, resource, max_days):
        """Retrieve a report on a given IP
        :param resource: {string} The IP,
        :return: {dict}
        """
        params = {"ipAddress": resource, "maxAgeInDays": str(max_days)}
        headers = {"Accept": "application/json", "Key": self.api_key}
        check_url = API_ROOT.format("check")
        response = requests.request(
            method="GET",
            url=check_url,
            headers=headers,
            params=params,
        )
        self.validate_response(response)

        json_object = response.json().get("data")

        return self.build_ip_address_object(json_object)

    def build_ip_address_object(self, json_object):
        return IP(
            raw_data=json_object,
            isPublic=json_object.get("isPublic"),
            ipVersion=json_object.get("ipVersion"),
            isAllowlisted=json_object.get("isWhitelisted"),
            abuseConfidenceScore=json_object.get("abuseConfidenceScore"),
            countryCode=json_object.get("countryCode"),
            countryName=json_object.get("countryName"),
            usageType=json_object.get("usageType"),
            isp=json_object.get("isp"),
            domain=json_object.get("domain"),
            hostnames=json_object.get("hostnames"),
            totalReports=json_object.get("totalReports"),
            numDistinctUsers=json_object.get("numDistinctUsers"),
            lastReportedAt=json_object.get("lastReportedAt"),
            reports=json_object.get("reports"),
        )
