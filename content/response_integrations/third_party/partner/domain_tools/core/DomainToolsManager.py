"""Manager for the DomainTools integration, handling API communications."""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any, Callable

from domaintools import API
from domaintools.exceptions import (
    NotAuthorizedException,
    NotFoundException,
    ServiceException,
)

from .exceptions import DomainToolsManagerError

ApiMethod = Callable[[str], Any]
RISK_SCORE_KEY: str = "risk_score"
APP_PARTNER_NAME: str = "Google SecOps SOAR"


def _to_bool_case_insensitive(value) -> bool:
    """Converts a string ('True' or 'False', case-insensitive) or a boolean
    value into a canonical Python boolean (True or False).
    """
    if isinstance(value, str):
        s_lower = value.lower()
        if s_lower == "true":
            return True
        if s_lower == "false":
            return False
        raise ValueError(f"Invalid boolean string value: '{value}'. Expected 'True' or 'False'.")

    return bool(value)


class DomainToolsManager:
    """Responsible for all DomainTools system operations functionality."""

    def __init__(
        self,
        username: str,
        api_key: str,
        use_https: bool | str = True,
        verify_ssl: bool | str = True,
        rate_limit: bool | str = True,
    ) -> None:
        """Initializes a DomainToolsManager instance.

        Args:
            username (str): The DomainTools API username.
            api_key (str): The DomainTools API key.
            use_https (bool | str): Whether to use HTTPS for API requests.
            verify_ssl (bool | str): Whether to verify SSL certificates.
            rate_limit (bool | str): Whether to respect API rate limits.
        """
        _use_https = _to_bool_case_insensitive(use_https)
        _verify_ssl = _to_bool_case_insensitive(verify_ssl)
        _rate_limit = _to_bool_case_insensitive(rate_limit)
        self._api = API(
            username,
            api_key,
            _use_https,
            verify_ssl=_verify_ssl,
            rate_limit=_rate_limit,
            app_partner=APP_PARTNER_NAME,
        )
        self.list_product = self._get_account_info()

    def _clear_results(self, response: Any) -> Any:
        """Cleans the raw API response by removing extra symb and parsing JSON.

        Args:
            response (Any): The raw response object from the domaintools
                library.

        Returns:
            Any: The parsed data from the 'response' key of the JSON payload.
        """
        response = str(response.json)
        for x in ["\n", "    "]:
            response = response.replace(x, "")
        data = json.loads(response)["response"]
        return data

    def _valid_ip4(self, ip: str) -> bool:
        """Checks whether the input string is a valid IPv4 address.

        Args:
            ip (str): The string to validate.

        Returns:
            bool: True if the string is a valid IPv4 address, False otherwise.
        """
        m = re.match(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", ip)
        return bool(m) and all([0 <= int(n) <= 255 for n in m.groups()])

    def _get_account_info(self) -> list[Any]:
        """Gets available products based on the account's license.

        Returns:
            list[Any]: A list of product dictionaries available to the account.
        """
        response = self._api.account_information()
        return self._clear_results(response).get("products", [])

    def _check_license(self, product_name: str) -> None:
        """Checks if a specific product is available under the current license.

        Args:
            product_name (str): The ID of the product to check (e.g., 'iris').

        Raises:
            DomainToolsManagerError: If the product is not in the license.
        """
        available_ids = [p.get("id") for p in self.list_product]
        if product_name not in available_ids:
            raise DomainToolsManagerError(f"You don't have {product_name} in your license.")

    def extract_domain_from_string(self, string: str) -> str:
        """Extracts a domain name from a URL or email address.

        Args:
            string (str): The input string which can be a URL, email, or domain.

        Returns:
            str: The extracted domain name.
        """
        string = string.lower()
        if "@" in string:
            return string.split("@")[-1]
        if string.startswith("www"):
            return string.split("www.")[-1]
        return urllib.parse.urlparse(string).netloc or string

    def get_domain_profile(self, domain: str) -> dict[str, Any] | None:
        """Retrieves the domain profile for a given domain.

        Args:
            domain (str): The domain name to query.

        Returns:
            dict[str, Any] | None: A dictionary with the domain profile data,
                or None on API-related failure.
        """
        try:
            self._check_license("domain-profile")
            response = self._api.domain_profile(domain)
            return self._clear_results(response)
        except (ServiceException, NotFoundException, NotAuthorizedException):
            return None
        except DomainToolsManagerError:
            return None

    def get_hosting_history(self, domain: str) -> dict[str, Any] | None:
        """Retrieves the hosting history for a given domain.

        Args:
            domain (str): The domain name to query.

        Returns:
            dict[str, Any] | None: A dictionary with the hosting history, or
                None on API-related failure.
        """
        try:
            self._check_license("hosting-history")
            response = self._api.hosting_history(domain)
            return self._clear_results(response)
        except (ServiceException, NotFoundException, NotAuthorizedException):
            return None
        except DomainToolsManagerError:
            return None

    def get_domains_by_email(self, email_address: str) -> dict[str, Any] | None:
        """Finds domains associated with an email address in their Whois record.

        Args:
            email_address (str): The email address to search for.

        Returns:
            dict[str, Any] | None: A dictionary of domains found, or None on
                API-related failure.
        """
        try:
            self._check_license("iris")
            response = self._api.iris(email=email_address)
            return self._clear_results(response)
        except (ServiceException, NotFoundException, NotAuthorizedException):
            return None
        except DomainToolsManagerError:
            return None

    def get_domains_by_ip(self, ip_address: str) -> dict[str, Any] | None:
        """Finds domain names that share a common IP address.

        Args:
            ip_address (str): The IP address to search for.

        Returns:
            dict[str, Any] | None: A dictionary of domains found, or None on
                API-related failure.
        """
        try:
            self._check_license("iris")
            response = self._api.iris(ip=ip_address)
            return self._clear_results(response)
        except (ServiceException, NotFoundException, NotAuthorizedException):
            return None
        except DomainToolsManagerError:
            return None

    def enrich_domain(self, domain: str) -> dict[str, Any] | None:
        """Enriches a domain or IP with DomainTools reverse DNS data.

        Args:
            domain (str): The domain or IP address to enrich.

        Returns:
            dict[str, Any] | None: A dictionary with enrichment data, or None
                on API-related failure.
        """
        try:
            self._check_license("reverse-ip")
            if self._valid_ip4(domain):
                response = self._api.host_domains(domain)
            else:
                response = self._api.reverse_ip(domain)
            return self._clear_results(response)
        except (ServiceException, NotFoundException, NotAuthorizedException):
            return None
        except DomainToolsManagerError:
            return None

    def get_ip_by_domain(self, domain: str) -> dict[str, Any] | None:
        """Finds IP addresses that a given domain name points to.

        Args:
            domain (str): The domain name to query.

        Returns:
            dict[str, Any] | None: A dictionary of IPs found, or None on
                API-related failure.
        """
        try:
            self._check_license("iris")
            response = self._api.iris(domain=domain)
            return self._clear_results(response)
        except (ServiceException, NotFoundException, NotAuthorizedException):
            return None
        except DomainToolsManagerError:
            return None

    def get_recent_domains_by_string_query(self, string_query: str) -> dict[str, Any] | None:
        """Searches for newly registered domains containing a specific query.

        Args:
            string_query (str): The query string to search for in new domains.

        Returns:
            dict[str, Any] | None: A dictionary of recent domains found, or
                None on API-related failure.
        """
        try:
            self._check_license("phisheye")
            response = self._api.phisheye(string_query)
            return self._clear_results(response)
        except (ServiceException, NotFoundException, NotAuthorizedException):
            return None
        except DomainToolsManagerError:
            return None

    def _get_available_risk_sources(self) -> list[ApiMethod]:
        """Gets a list of available risk-related API methods based on license.

        Raises:
            DomainToolsManagerError: If neither 'risk' nor 'reputation' is in
                the license.

        Returns:
            list[ApiMethod]: A list of callable API methods for fetching risk
                data.
        """
        available_sources: list[tuple[str, ApiMethod]] = [
            ("reputation", self._api.reputation),
            ("risk", self._api.risk),
        ]
        licensed_methods = [
            method
            for name, method in available_sources
            if any(p.get("id") == name for p in self.list_product)
        ]

        if not licensed_methods:
            raise DomainToolsManagerError("You don't have 'risk' or 'reputation' in your license.")

        return licensed_methods

    def _fetch_risk_data(self, api_method: ApiMethod, domain: str) -> dict[str, Any]:
        """Makes a single API call to a risk endpoint and handles exceptions.

        Args:
            api_method (ApiMethod): The specific API method to call
                (e.g., self._api.risk).
            domain (str): The domain to query.

        Raises:
            DomainToolsManagerError: If authentication or service errors occur.

        Returns:
            dict[str, Any]: The resulting risk data dictionary, or an empty
                dict on failure.
        """
        try:
            response = api_method(domain)
            return self._clear_results(response)
        except NotAuthorizedException as e:
            raise DomainToolsManagerError(f"Authentication failed: {e}") from e
        except NotFoundException:
            return {}
        except ServiceException as e:
            raise DomainToolsManagerError(f"API call failed for {domain}: {e}") from e

    def get_domain_risk_data(self, domain: str) -> dict[str, Any] | None:
        """Gets a comprehensive dictionary of risk data from available sources.

        This is the new method for the 'Get Domain Risk' action, which
        combines data from multiple licensed endpoints (like 'risk' and
        'reputation').

        Args:
            domain (str): The domain name to query for risk data.

        Returns:
            dict[str, Any] | None: A combined dictionary of all available risk
                data, or None if no data is found.
        """
        combined_data: dict[str, Any] = {}

        for api_method in self._get_available_risk_sources():
            data = self._fetch_risk_data(api_method, domain)
            if data:
                combined_data.update(data)

        return combined_data if combined_data else None

    def format_risk_entity_result(self, domain: str, risk_data: dict[str, Any]) -> dict[str, Any]:
        """
        Formats the combined risk data into the standardized EntityResult structure.

        The structure depends on whether 'components' data is present (i.e., if
        the 'risk' product was licensed and fetched).

        Args:
            domain (str): The domain name being processed.
            risk_data (dict[str, Any]): The combined risk data from DomainTools.

        Returns:
            dict[str, Any]: The EntityResult dictionary.
        """
        risk_score_value = risk_data.get(RISK_SCORE_KEY)

        result: dict[str, Any] = {
            "domain": domain,
            "risk_score": float(risk_score_value) if risk_score_value is not None else None,
        }

        if "components" in risk_data:
            result["components"] = risk_data["components"]

        if "reasons" in risk_data and "components" not in risk_data:
            result["reasons"] = risk_data["reasons"]

        return result
