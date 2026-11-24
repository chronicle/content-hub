from __future__ import annotations

import json
import os
import unittest
from unittest.mock import Mock, patch

import pytest

from rsa_net_witness_edr.core.RSAManager import RSAManager
from rsa_net_witness_edr.core.RSAExceptions import (
    RSAError,
)

# Constants
MOCK_DATA = json.load(
    open(
        os.path.join(os.path.dirname(__file__), "mock_data.json")
    )
)

TEST_IP_ADDRESS = "172.30.203.155"
TEST_HOSTNAME = "RSA-HOST02"

class TestRSAManager(unittest.TestCase):
    """
    RSAManager test cases
    """

    def setUp(self) -> None:
        self.manager = RSAManager(api_root="API Root", username="Username",
                                  password="Password", verify_ssl="Verify SSL")

    def test_get_endpoint_details(self):
        """
        Test the get endpoint details

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        mock_response = Mock()
        mock_response.json.return_value = MOCK_DATA.get(
            'get_endpoints'
        )
        patch_object = patch.object(
            self.manager.session, "get", return_value=mock_response
        )

        with patch_object:
            response = self.manager.get_endpoint_details(
                endpoint_gui = TEST_IP_ADDRESS
            )
            assert response.local_ip == TEST_IP_ADDRESS
            assert response.machine_name == TEST_HOSTNAME

    @pytest.mark.usefixtures("mock_get_endpoint_details_to_raise_manager_error")
    def test_get_endpoint_details_failure(self) -> None:
        """
        Test get endpoint details

        Returns:
            None

        Raises:
        - RSAException
        """

        with pytest.raises(RSAError):
            self.manager.get_endpoint_details(
                endpoint_gui = TEST_IP_ADDRESS
            )
