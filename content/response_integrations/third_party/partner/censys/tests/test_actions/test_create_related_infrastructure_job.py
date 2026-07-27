from __future__ import annotations

import re
from unittest.mock import Mock, patch

import pytest
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED

from censys.actions.create_related_infrastructure_job import (
    main,
    validate_create_job_params,
)
from censys.core.constants import (
    INVALID_CERTIFICATE_FORMAT_ERROR,
    INVALID_TARGET_TYPE_ERROR,
    INVALID_WEB_PROPERTY_FORMAT_ERROR,
    TARGET_TYPE_CERTIFICATE,
    TARGET_TYPE_HOST,
    TARGET_TYPE_WEB_PROPERTY,
    TARGET_VALUE_REQUIRED_ERROR,
)


class TestValidateCreateJobParams:
    """Test parameter validation for Create Related Infrastructure Job action."""

    def test_validate_host_success(self):
        """Test successful validation for Host target type."""
        validate_create_job_params(TARGET_TYPE_HOST, "14.84.5.68")

    def test_validate_web_property_success(self):
        """Test successful validation for Web Property target type."""
        validate_create_job_params(TARGET_TYPE_WEB_PROPERTY, "example.com:443")

    def test_validate_certificate_success(self):
        """Test successful validation for Certificate target type."""
        valid_cert = "a" * 64
        validate_create_job_params(TARGET_TYPE_CERTIFICATE, valid_cert)

    def test_validate_empty_target_value(self):
        """Test validation fails for empty target value."""
        with pytest.raises(ValueError, match=TARGET_VALUE_REQUIRED_ERROR):
            validate_create_job_params(TARGET_TYPE_HOST, "")

    def test_validate_invalid_ip(self):
        """Test validation fails for invalid IP address."""
        with pytest.raises(ValueError):
            validate_create_job_params(TARGET_TYPE_HOST, "invalid.ip")

    def test_validate_web_property_missing_port(self):
        """Test validation fails for Web Property without port."""
        with pytest.raises(
            ValueError, match=re.escape(INVALID_WEB_PROPERTY_FORMAT_ERROR)
        ):
            validate_create_job_params(TARGET_TYPE_WEB_PROPERTY, "example.com")

    def test_validate_web_property_invalid_port(self):
        """Test validation fails for Web Property with invalid port."""
        with pytest.raises(
            ValueError, match=re.escape(INVALID_WEB_PROPERTY_FORMAT_ERROR)
        ):
            validate_create_job_params(TARGET_TYPE_WEB_PROPERTY, "example.com:99999")

    def test_validate_certificate_invalid_format(self):
        """Test validation fails for invalid certificate format."""
        with pytest.raises(
            ValueError, match=re.escape(INVALID_CERTIFICATE_FORMAT_ERROR)
        ):
            validate_create_job_params(TARGET_TYPE_CERTIFICATE, "invalid_cert")

    def test_validate_invalid_target_type(self):
        """Test validation fails for invalid target type."""
        with pytest.raises(
            ValueError, match=INVALID_TARGET_TYPE_ERROR.format("Invalid")
        ):
            validate_create_job_params("Invalid", "14.84.5.68")


@patch("censys.actions.create_related_infrastructure_job.APIManager")
@patch("censys.actions.create_related_infrastructure_job.SiemplifyAction")
class TestCreateRelatedInfrastructureJob:
    """Test Create Related Infrastructure Job action."""

    def test_create_job_success_host(
        self, mock_siemplify_class, mock_api_manager_class
    ):
        """Test successful job creation for Host target type."""
        mock_siemplify = Mock()
        mock_siemplify_class.return_value = mock_siemplify

        mock_siemplify.extract_action_param.side_effect = [
            TARGET_TYPE_HOST,
            "14.84.5.68",
        ]

        mock_api_manager = Mock()
        mock_api_manager_class.return_value = mock_api_manager

        mock_response = {
            "result": {
                "job_id": "test-job-123",
                "state": "started",
                "create_time": "2026-03-31T07:30:00Z",
            }
        }
        mock_api_manager.create_censeye_job.return_value = mock_response

        main()

        mock_api_manager.create_censeye_job.assert_called_once_with(
            target_type=TARGET_TYPE_HOST,
            target_value="14.84.5.68",
        )
        mock_siemplify.result.add_result_json.assert_called_once_with(mock_response)
        assert "Successfully created" in mock_siemplify.end.call_args[0][0]

    def test_create_job_success_web_property(
        self, mock_siemplify_class, mock_api_manager_class
    ):
        """Test successful job creation for Web Property target type."""
        mock_siemplify = Mock()
        mock_siemplify_class.return_value = mock_siemplify

        mock_siemplify.extract_action_param.side_effect = [
            TARGET_TYPE_WEB_PROPERTY,
            "example.com:443",
        ]

        mock_api_manager = Mock()
        mock_api_manager_class.return_value = mock_api_manager

        mock_response = {
            "result": {
                "job_id": "test-job-456",
                "state": "started",
                "create_time": "2026-03-31T07:30:00Z",
            }
        }
        mock_api_manager.create_censeye_job.return_value = mock_response

        main()

        mock_api_manager.create_censeye_job.assert_called_once_with(
            target_type=TARGET_TYPE_WEB_PROPERTY,
            target_value="example.com:443",
        )

    def test_create_job_validation_error(
        self, mock_siemplify_class, mock_api_manager_class
    ):
        """Test job creation with validation error."""
        mock_siemplify = Mock()
        mock_siemplify_class.return_value = mock_siemplify

        mock_siemplify.extract_action_param.side_effect = [
            TARGET_TYPE_HOST,
            "invalid.ip",
        ]

        main()

        call_args = mock_siemplify.end.call_args[0]
        assert call_args[2] == EXECUTION_STATE_FAILED
