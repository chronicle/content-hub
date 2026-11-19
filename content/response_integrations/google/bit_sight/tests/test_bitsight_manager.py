from __future__ import annotations

import os
import json
import unittest
from typing import List
from unittest.mock import patch, Mock

import pytest

from bit_sight.core.datamodels import Company, VulnerabilityStats
from bit_sight.core.BitSightManager import BitSightManager
from bit_sight.core.BitSightExceptions import BitSightException

# from Tests.integrations.BitSight.conftest import (
#     mock_get_companies_response,
#     mock_get_vulnerabilities_response
#
from integration_testing.logger import Logger


################################################
#       Class based approach - Unittests       #
################################################


COMPANIES_DATA = json.load(
    open(
        os.path.join(os.path.dirname(__file__), "companies.json")
    )
)

class TestBitsightManager(unittest.TestCase):
    def setUp(self) -> None:
        with open("config.json", "r") as f:
            data = f.read()

        config = json.loads(data)
        api_root = config.get("API Root")
        api_key = config.get("API Key")
        verify_ssl = config.get("Verify SSL")
        if isinstance(verify_ssl, str):
            verify_ssl = (
                True if verify_ssl.lower() == "true" else False
            )
        self.manager = BitSightManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=Logger()
        )
        self.test_company_id = ''

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
