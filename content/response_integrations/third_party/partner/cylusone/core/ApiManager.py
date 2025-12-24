"""API Manager for Cylus integration."""

from typing import Any, Dict, Optional

import requests

from .constants import DEFAULT_TIMEOUT, ENDPOINTS, ERRORS
from .CylusException import (
    CylusAPIException,
    CylusAuthenticationException,
    CylusConnectionException,
)
from .utils import sanitize_url


class ApiManager:
    """Centralized API manager for Cylus platform interactions."""

    def __init__(
        self,
        api_root: str,
        api_key: str,
        verify_ssl: bool = True,
        logger: Any = None,
    ) -> None:
        """Initialize API client."""
        self.api_root = sanitize_url(api_root)
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key, "Content-Type": "application/json"})
        self.error = None

    def _make_request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        """Make HTTP request to Cylus API."""
        url = f"{self.api_root}{endpoint}"
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        kwargs.setdefault("verify", self.verify_ssl)

        try:
            if self.logger:
                self.logger.info(f"Making {method} request to: {url}")

            response = self.session.request(method, url, **kwargs)

            if self.logger:
                self.logger.info(f"Response status code: {response.status_code}")

            return response

        except requests.exceptions.Timeout:
            error_msg = f"{ERRORS['CONNECTIVITY']['TIMEOUT']} - URL: {url}"
            if self.logger:
                self.logger.error(error_msg)
            raise CylusConnectionException(error_msg)

        except requests.exceptions.ConnectionError:
            error_msg = f"{ERRORS['CONNECTIVITY']['FAILED']} - URL: {url}"
            if self.logger:
                self.logger.error(error_msg)
            raise CylusConnectionException(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error during API request: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise CylusAPIException(error_msg)

    def test_connectivity(self) -> bool:
        """Return True if the API is reachable and credentials are valid."""
        try:
            test_ip = "10.0.0.5"
            endpoint = ENDPOINTS["ASSETS_BY_IP"].format(ip=test_ip)
            response = self._make_request("GET", endpoint)

            if response.status_code == 401:
                self.error = ERRORS["CONNECTIVITY"]["INVALID_CREDENTIALS"]
                if self.logger:
                    self.logger.error(self.error)
                return False
            elif response.status_code == 403:
                self.error = "Access denied - insufficient permissions"
                if self.logger:
                    self.logger.error(self.error)
                return False

            if response.status_code in [200, 404]:
                if self.logger:
                    self.logger.info("Connectivity test successful")
                return True

            self.error = f"Unexpected response: {response.status_code} - {response.text}"
            if self.logger:
                self.logger.warning(self.error)
            return False

        except (CylusConnectionException, CylusAuthenticationException, CylusAPIException) as e:
            self.error = str(e)
            return False
        except Exception as e:
            self.error = f"Connectivity test failed: {str(e)}"
            if self.logger:
                self.logger.error(self.error)
            return False

    def get_asset_by_ip(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Return asset information for the given IP or None if not found."""
        endpoint = ENDPOINTS["ASSETS_BY_IP"].format(ip=ip_address)
        response = self._make_request("GET", endpoint)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None  # Asset not found
        else:
            raise CylusAPIException(
                f"Failed to get asset for IP {ip_address}", status_code=response.status_code
            )
