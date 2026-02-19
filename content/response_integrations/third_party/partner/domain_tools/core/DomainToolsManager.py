"""Manager for the DomainTools integration, handling API communications."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from domaintools import API
from domaintools.exceptions import (
    NotAuthorizedException,
    NotFoundException,
    ServiceException,
)

from .exceptions import DomainToolsManagerError
from .DomainToolsParser import DomainToolsParser
from .datamodels import IrisInvestigateModel, ParsedDomainRDAPModel, WhoisHistoryModel


APP_PARTNER_NAME: str = "Google SecOps SOAR"
APP_VERSION: str = "10.0"


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
        siemplify_logger=None,
    ) -> None:
        """
        Initializes a DomainToolsManager instance.

        Args:
            username (str): The DomainTools API username.
            api_key (str): The DomainTools API key.
            use_https (bool | str): Whether to use HTTPS for API requests.
            verify_ssl (bool | str): Whether to verify SSL certificates.
            rate_limit (bool | str): Whether to respect API rate limits.
            siemplify_logger (Siemplify Logger): The siemplify logger
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
            app_version=APP_VERSION
        )
        self.logger = siemplify_logger
        self.available_api_calls = []
        self.list_product = self._get_account_info()
        self.parser = DomainToolsParser()

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
        try:
            response = self._api.account_information().response()
            dt_available_products = response.get("products", [])
            self.available_api_calls = [p.get("id") for p in dt_available_products]

            return dt_available_products
        except Exception as e:
            raise DomainToolsManager(f"Unable to get account info. Reason: {str(e)}")

    def _check_license(self, product_name: str) -> None:
        """Checks if a specific product is available under the current license.

        Args:
            product_name (str): The ID of the product to check (e.g., 'iris').

        Raises:
            DomainToolsManagerError: If the product is not in the license.
        """

        if product_name not in self.available_api_calls:
            raise DomainToolsManagerError(f"You don't have {product_name} - {self.available_api_calls} in your license.")

    def investigate_domains(self, domains: list[str]) -> list[IrisInvestigateModel]:
        try:
            self._check_license("iris-investigate")
            response = self._api.iris_investigate(domains=domains).response()
            results = response.get("results", [])

            return [self.parser.parse_iris_data(raw_data=result) for result in results]
        except Exception as e:
            raise DomainToolsManagerError(f"Unable to investigate domains. Reason {str(e)}")

    def get_parsed_domain_rdap(self, domain: str) -> ParsedDomainRDAPModel:
        try:
            self._check_license("parsed-domain-rdap")
            response = self._api.parsed_domain_rdap(query=domain).response()
            parsed_domain_rdap_data = response.get("parsed_domain_rdap", {})

            return self.parser.parse_domain_rdap_data(raw_data=parsed_domain_rdap_data)
        except NotFoundException:
            return ParsedDomainRDAPModel(domain=domain, has_found=False)
        except Exception as e:
            raise DomainToolsManagerError(f"Unable to get parsed domain rdap for {domain}. Reason {str(e)}")

    def get_whois_history(self, domain: str):
        try:
            self._check_license("parsed-domain-rdap")
            response = self._api.whois_history(query=domain).response()
            return self.parser.parse_whois_history(raw_data=response)
        except NotFoundException:
            return WhoisHistoryModel(record_count=0)
        except Exception as e:
            raise DomainToolsManagerError(f"Unable to get parsed domain rdap for {domain}. Reason {str(e)}")

