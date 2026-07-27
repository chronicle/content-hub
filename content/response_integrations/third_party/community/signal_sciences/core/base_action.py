from __future__ import annotations

import ipaddress
from abc import ABC

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_configuration_param

from ..core.SignalSciencesManager import SignalSciencesManager
from .constants import DEFAULT_API_ROOT, INTEGRATION_IDENTIFIER


class SignalSciencesAction(Action, ABC):
    """Base action class for Signal Sciences."""

    @staticmethod
    def is_valid_ip(ip_address: str) -> bool:
        """Check if the provided string is a valid IP address (IPv4 or IPv6).

        Args:
            ip_address: The string to check.

        Returns:
            True if valid, False otherwise.
        """
        try:
            ipaddress.ip_address(ip_address)
            return True
        except ValueError:
            return False

    def _init_api_clients(self) -> SignalSciencesManager:
        """Prepare API client"""
        api_root = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="API Root",
            default_value=DEFAULT_API_ROOT,
        )

        email = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Email",
            is_mandatory=True,
        )
        api_token = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="API Token",
            is_mandatory=True,
        )
        corp_name = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Corporation Name",
            is_mandatory=True,
        )
        verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Verify SSL",
            default_value=True,
            input_type=bool,
        )

        return SignalSciencesManager(
            api_root=api_root,
            email=email,
            api_token=api_token,
            corp_name=corp_name,
            verify_ssl=verify_ssl,
        )
