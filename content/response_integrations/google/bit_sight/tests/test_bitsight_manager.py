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
import os
import unittest
from typing import List
from unittest.mock import MagicMock, Mock, patch

import pytest

from bit_sight.core.BitSightExceptions import BitSightException
from bit_sight.core.BitSightManager import BitSightManager
from bit_sight.core.datamodels import Company, VulnerabilityStats
from bit_sight.tests.common import CONFIG

with open(os.path.join(os.path.dirname(__file__), "companies.json"), encoding="utf-8") as companies_file:
    COMPANIES_DATA = json.load(companies_file)


class TestBitsightManager(unittest.TestCase):
    def setUp(self) -> None:
        api_root = CONFIG.get("API Root")
        api_key = CONFIG.get("API Key")
        verify_ssl = CONFIG.get("Verify SSL")
        if isinstance(verify_ssl, str):
            verify_ssl = verify_ssl.lower() == "true"
        self.manager = BitSightManager(
            api_root=str(api_root),
            api_key=str(api_key),
            verify_ssl=bool(verify_ssl),
            siemplify_logger=MagicMock(),
        )
        self.test_company_id = ""

    def test_connectivity_success(self) -> None:
        """
        Test for connectivity success
        Args:
            bitsight_manager: BitSightManager
        Returns:
            None
        """
        mock_get_request = Mock()
        mock_get_request.raise_for_status.return_value = True
        with patch.object(self.manager.session, 'get', mock_get_request):
            assert self.manager.test_connectivity() is None  # no exception were raised

    @pytest.mark.usefixtures("mock_test_connectivity_to_raise_manager_error")
    def test_connectivity_fail(self) -> None:
        """
            Test for connectivity failure
            Args:
                bitsight_manager: BitSightManager
            Returns:
                None
            """
        mock_get_request = Mock()
        mock_get_request.raise_for_status.side_effect = BitSightException('Mock error')
        with patch.object(self.manager.session, 'get', mock_get_request):
            with pytest.raises(BitSightException):
                self.manager.test_connectivity()

    def test_get_companies(self, *args) -> None:
        mock_companies = Mock()
        mock_companies.json.return_value = COMPANIES_DATA
        mock_companies.raise_for_status.return_value = COMPANIES_DATA
        with patch.object(
            self.manager.session,
            'get',
            return_value=mock_companies
        ):
            companies = self.manager.get_companies()
            assert isinstance(companies, list)
            if len(companies):  # companies list can be empty
                assert isinstance(companies[0], Company)

    def test_get_company_details_success(self, *args) -> None:
        if self.test_company_id:  # companies list can be empty
            company = self.manager.get_company_details(self.test_company_id)
            assert isinstance(company, Company)

    @pytest.mark.usefixtures("mock_get_company_details_raise_manager_error")
    def test_get_company_details_incorrect_company_id(self, *args) -> None:
        company_id = "dummy_id"
        with pytest.raises(BitSightException):
            self.manager.get_company_details(company_id)

    def test_get_company_vulnerabilities_success(self, *args) -> None:
        if self.test_company_id:  # companies list can be empty
            vulnerabilities = self.manager.get_company_vulnerabilities(self.test_company_id, high_confidence=False)
            assert isinstance(vulnerabilities[0], VulnerabilityStats)

    @pytest.mark.usefixtures("mock_get_company_vulnerabilities_raise_manager_error")
    def test_get_company_vulnerabilities_incorrect_company_id(self, *args) -> None:
        company_id = "dummy_id"
        with pytest.raises(BitSightException):
            self.manager.get_company_vulnerabilities(company_id, high_confidence=False)

    def test_get_company_vulnerabilities_high_confidence(self, *args) -> None:
        if self.test_company_id:
            stats: List[VulnerabilityStats] = self.manager.get_company_vulnerabilities(
                self.test_company_id, high_confidence=True
            )
            for vulnerability in stats[0].vulnerabilities:
                self.assertEquals(vulnerability.confidence, "HIGH")
            assert isinstance(stats[0], VulnerabilityStats)
