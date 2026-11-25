# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import json
import unittest
from unittest.mock import Mock, patch

import pytest

from rsa_net_witness_edr.core.RSAExceptions import RSAError
from rsa_net_witness_edr.core.RSAManager import RSAManager
from rsa_net_witness_edr.tests.common import TESTS_DIR

# Constants
MOCK_DATA = json.loads((TESTS_DIR / "mock_data.json").read_text(encoding="utf-8"))

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
