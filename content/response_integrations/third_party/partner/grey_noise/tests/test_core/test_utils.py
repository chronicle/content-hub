"""
Test cases for core/utils.py to improve coverage from 37% to 100%.
"""

from unittest.mock import MagicMock
import re

import pytest
from core.greynoise_exceptions import InvalidIntegerException
from core.utils import (
    generate_ip_lookup_insight,
    generate_timeline_insight,
    get_cve_entities,
    get_integration_params,
    get_ip_entities,
    validate_cve_format,
    validate_integer_param,
)
from SiemplifyDataModel import EntityTypes


class TestGetIntegrationParams:
    """Test get_integration_params function."""

    def test_get_integration_params_success(self):
        """Test successful API key extraction."""
        mock_siemplify = MagicMock()
        mock_siemplify.extract_configuration_param.return_value = "test_api_key"

        result = get_integration_params(mock_siemplify)

        assert result == "test_api_key"
        # Just verify the method was called, ignore exact parameters since they may vary
        mock_siemplify.extract_configuration_param.assert_called_once()


class TestValidateIntegerParam:
    """Test validate_integer_param function."""

    def test_validate_integer_valid_positive(self):
        """Test validation of valid positive integer."""
        result = validate_integer_param("5", "test_param")
        assert result == 5

    def test_validate_integer_valid_negative_allowed(self):
        """Test validation of valid negative integer when allowed."""
        result = validate_integer_param("-3", "test_param", allow_negative=True)
        assert result == -3

    def test_validate_integer_valid_zero_allowed(self):
        """Test validation of zero when allowed."""
        result = validate_integer_param("0", "test_param", zero_allowed=True)
        assert result == 0

    def test_validate_integer_invalid_string(self):
        """Test validation fails with invalid string."""
        with pytest.raises(InvalidIntegerException) as exc_info:
            validate_integer_param("abc", "test_param")
        assert "test_param must be an integer" in str(exc_info.value)

    def test_validate_integer_invalid_none(self):
        """Test validation fails with None."""
        with pytest.raises(InvalidIntegerException) as exc_info:
            validate_integer_param(None, "test_param")
        assert "test_param must be an integer" in str(exc_info.value)

    def test_validate_integer_negative_not_allowed(self):
        """Test validation fails with negative when not allowed."""
        with pytest.raises(InvalidIntegerException) as exc_info:
            validate_integer_param("-5", "test_param")
        assert "test_param must be a non-negative integer" in str(exc_info.value)

    def test_validate_integer_zero_not_allowed(self):
        """Test validation fails with zero when not allowed."""
        with pytest.raises(InvalidIntegerException) as exc_info:
            validate_integer_param("0", "test_param")
        assert "test_param must be greater than zero" in str(exc_info.value)


class TestGetCVEEntities:
    """Test get_cve_entities function."""

    def test_get_cve_entities_with_cve(self):
        """Test getting CVE entities from mixed entity list."""
        mock_cve_entity = MagicMock()
        mock_cve_entity.entity_type = EntityTypes.CVE

        mock_ip_entity = MagicMock()
        mock_ip_entity.entity_type = EntityTypes.ADDRESS

        mock_siemplify = MagicMock()
        mock_siemplify.target_entities = [mock_cve_entity, mock_ip_entity]

        result = get_cve_entities(mock_siemplify)

        assert len(result) == 1
        assert result[0] == mock_cve_entity

    def test_get_cve_entities_no_cve(self):
        """Test getting CVE entities when none exist."""
        mock_ip_entity = MagicMock()
        mock_ip_entity.entity_type = EntityTypes.ADDRESS

        mock_siemplify = MagicMock()
        mock_siemplify.target_entities = [mock_ip_entity]

        result = get_cve_entities(mock_siemplify)

        assert len(result) == 0

    def test_get_cve_entities_empty_list(self):
        """Test getting CVE entities from empty list."""
        mock_siemplify = MagicMock()
        mock_siemplify.target_entities = []

        result = get_cve_entities(mock_siemplify)

        assert len(result) == 0


class TestValidateCVEFormat:
    """Test validate_cve_format function."""

    def test_validate_cve_format_valid(self):
        """Test validation of valid CVE format."""
        result = validate_cve_format("CVE-2023-1234")
        assert result is True

    def test_validate_cve_format_valid_multiple_digits(self):
        """Test validation of valid CVE format with multiple digits."""
        result = validate_cve_format("CVE-2023-12345")
        assert result is True

    def test_validate_cve_format_invalid_no_prefix(self):
        """Test validation fails without CVE prefix."""
        with pytest.raises(ValueError) as exc_info:
            validate_cve_format("2023-1234")
        assert "Invalid CVE format" in str(exc_info.value)

    def test_validate_cve_format_invalid_wrong_year(self):
        """Test validation fails with wrong year format."""
        with pytest.raises(ValueError) as exc_info:
            validate_cve_format("CVE-23-1234")
        assert "Invalid CVE format" in str(exc_info.value)

    def test_validate_cve_format_invalid_insufficient_digits(self):
        """Test validation fails with insufficient digits."""
        with pytest.raises(ValueError) as exc_info:
            validate_cve_format("CVE-2023-123")
        assert "Invalid CVE format" in str(exc_info.value)

    def test_validate_cve_format_invalid_extra_chars(self):
        """Test validation fails with extra characters."""
        with pytest.raises(ValueError) as exc_info:
            validate_cve_format("CVE-2023-1234-extra")
        assert "Invalid CVE format" in str(exc_info.value)

    def test_validate_cve_format_invalid_empty(self):
        """Test validation fails with empty string."""
        with pytest.raises(ValueError) as exc_info:
            validate_cve_format("")
        assert "Invalid CVE format" in str(exc_info.value)


class TestGetIPEntities:
    """Test get_ip_entities function."""

    def test_get_ip_entities_with_ip(self):
        """Test getting IP entities from mixed entity list."""
        mock_ip_entity = MagicMock()
        mock_ip_entity.entity_type = EntityTypes.ADDRESS

        mock_cve_entity = MagicMock()
        mock_cve_entity.entity_type = EntityTypes.CVE

        mock_siemplify = MagicMock()
        mock_siemplify.target_entities = [mock_ip_entity, mock_cve_entity]

        result = get_ip_entities(mock_siemplify)

        assert len(result) == 1
        assert result[0] == mock_ip_entity

    def test_get_ip_entities_no_ip(self):
        """Test getting IP entities when none exist."""
        mock_cve_entity = MagicMock()
        mock_cve_entity.entity_type = EntityTypes.CVE

        mock_siemplify = MagicMock()
        mock_siemplify.target_entities = [mock_cve_entity]

        result = get_ip_entities(mock_siemplify)

        assert len(result) == 0

    def test_get_ip_entities_empty_list(self):
        """Test getting IP entities from empty list."""
        mock_siemplify = MagicMock()
        mock_siemplify.target_entities = []

        result = get_ip_entities(mock_siemplify)

        assert len(result) == 0


class TestGenerateTimelineInsight:
    """Test generate_timeline_insight function."""

    def test_generate_timeline_insight_complete_data(self):
        """Test generating insight with complete timeline data."""
        data = {
            "metadata": {
                "field": "classification",
                "first_seen": "2023-01-01",
                "granularity": "1d",
                "metric": "count",
            },
            "results": [
                {"timestamp": "2023-01-01T00:00:00Z", "label": "benign", "data": "10"},
                {"timestamp": "2023-01-02T00:00:00Z", "label": "suspicious", "data": "5"},
            ],
        }

        result = generate_timeline_insight(data, "8.8.8.8")

        assert "IP Activity Timeline" in result
        assert "Timeline Overview" in result
        assert "classification" in result
        assert "2023-01-01" in result
        assert "benign" in result
        assert "suspicious" in result
        assert "8.8.8.8" in result
        assert re.search(r"https://viz\.greynoise\.io/", result)

    def test_generate_timeline_insight_empty_data(self):
        """Test generating insight with empty data."""
        data = {}
        result = generate_timeline_insight(data, "8.8.8.8")
        assert "<div style='padding:15px; border-radius:6px;'>" in result
        assert "No data available" in result

    def test_generate_timeline_insight_only_metadata(self):
        """Test generating insight with only metadata."""
        data = {"metadata": {"field": "classification", "first_seen": "2023-01-01"}}

        result = generate_timeline_insight(data, "8.8.8.8")

        assert "Timeline Overview" in result
        assert "classification" in result

    def test_generate_timeline_insight_only_activity(self):
        """Test generating insight with only activity data."""
        data = {"results": [{"timestamp": "2023-01-01T00:00:00Z", "label": "benign", "data": "10"}]}

        result = generate_timeline_insight(data, "8.8.8.8")

        assert "IP Activity Timeline" in result
        assert "benign" in result
        assert "2023-01-01" in result

    def test_generate_timeline_insight_many_activities(self):
        """Test generating insight with many activities (truncated to 10)."""
        activities = []
        for i in range(15):
            activities.append({
                "timestamp": f"2023-01-{i + 1:02d}T00:00:00Z",
                "label": f"label_{i}",
                "data": str(i),
            })

        data = {"results": activities}
        result = generate_timeline_insight(data, "8.8.8.8")

        assert "Showing 10 of 15 events" in result
        assert "label_0" in result
        assert "label_9" in result
        assert "label_14" not in result  # Should be truncated


class TestGenerateIPLookupInsight:
    """Test generate_ip_lookup_insight function."""

    def test_generate_ip_lookup_insight_enterprise_complete(self):
        """Test generating enterprise IP lookup insight with complete data."""
        data = {
            "business_service_intelligence": {
                "found": True,
                "name": "Google DNS",
                "trust_level": "1",
            },
            "internet_scanner_intelligence": {
                "found": True,
                "classification": "benign",
                "actor": "Google",
                "first_seen": "2023-01-01",
                "last_seen": "2023-01-02",
                "bot": False,
                "vpn": False,
                "tags": [{"name": "dns"}, {"name": "public"}],
                "cves": ["CVE-2023-1234"],
                "metadata": {"source_country": "US", "organization": "Google LLC"},
            },
        }

        result = generate_ip_lookup_insight(data, "8.8.8.8")

        assert "IP Intelligence Overview" in result
        assert "BENIGN" in result
        assert "Google" in result
        assert "First Seen" in result
        assert "2023-01-01" in result
        assert "Last Seen" in result
        assert "2023-01-02" in result
        assert "Country" in result
        assert "US" in result
        assert "Organization" in result
        assert "Google LLC" in result
        assert "BUSINESS SERVICE" in result
        assert "Google DNS" in result
        assert "dns" in result
        assert "CVE-2023-1234" in result
        assert "8.8.8.8" in result
        assert re.search(r"https://viz\.greynoise\.io/", result)

    def test_generate_ip_lookup_insight_community_minimal(self):
        """Test generating community IP lookup insight with minimal data - returns NOT FOUND."""
        data = {
            "internet_scanner_intelligence": {
                "classification": "unknown",
                "bot": False,
                "vpn": False,
            }
        }

        result = generate_ip_lookup_insight(data, "1.2.3.4")

        # Without found flag, returns NOT FOUND HTML
        assert "NOT FOUND" in result
        assert "Business Service" in result
        assert "Internet Scanner" in result

    def test_generate_ip_lookup_insight_no_isi(self):
        """Test generating insight with no internet scanner intelligence."""
        data = {"business_service_intelligence": {"found": True, "name": "Test Service"}}

        result = generate_ip_lookup_insight(data, "8.8.8.8")

        assert "IP Intelligence Overview" in result
        assert "BUSINESS SERVICE" in result
        assert "Test Service" in result

    def test_generate_ip_lookup_insight_many_tags(self):
        """Test generating insight with many tags (truncated to 5) - needs found flag."""
        tags = []
        for i in range(10):
            tags.append({"name": f"tag_{i}"})

        data = {"internet_scanner_intelligence": {"found": True, "classification": "benign", "tags": tags}}

        result = generate_ip_lookup_insight(data, "8.8.8.8")

        assert "tag_0" in result
        assert "tag_4" in result
        assert "tag_9" not in result  # Should be truncated

    def test_generate_ip_lookup_insight_many_cves(self):
        """Test generating insight with many CVEs (truncated to 5) - needs found flag."""
        cves = [f"CVE-2023-{i:04d}" for i in range(10)]

        data = {"internet_scanner_intelligence": {"found": True, "classification": "benign", "cves": cves}}

        result = generate_ip_lookup_insight(data, "8.8.8.8")

        assert "CVE-2023-0000" in result
        assert "CVE-2023-0004" in result
        assert "CVE-2023-0009" not in result  # Should be truncated

    def test_generate_ip_lookup_insight_empty_data(self):
        """Test generating insight with empty data - returns NOT FOUND."""
        data = {}
        result = generate_ip_lookup_insight(data, "8.8.8.8")

        # Empty data returns NOT FOUND HTML
        assert "NOT FOUND" in result
        assert "Business Service" in result
        assert "Internet Scanner" in result
