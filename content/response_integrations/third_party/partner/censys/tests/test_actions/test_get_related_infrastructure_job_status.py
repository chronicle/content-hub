from __future__ import annotations

import pytest
from unittest.mock import Mock, patch

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)

from censys.actions.get_related_infrastructure_job_status import main
from censys.core.constants import (
    JOB_ID_REQUIRED_ERROR,
    JOB_STATE_COMPLETED,
    JOB_STATE_FAILED,
    JOB_STATE_STARTED,
)


@patch("censys.actions.get_related_infrastructure_job_status.APIManager")
@patch("censys.actions.get_related_infrastructure_job_status.SiemplifyAction")
class TestGetRelatedInfrastructureJobStatus:
    """Test Get Related Infrastructure Job Status action."""

    def test_get_status_completed(self, mock_siemplify_class, mock_api_manager_class):
        """Test getting status for completed job."""
        mock_siemplify = Mock()
        mock_siemplify_class.return_value = mock_siemplify

        mock_siemplify.extract_action_param.return_value = "test-job-123"

        mock_api_manager = Mock()
        mock_api_manager_class.return_value = mock_api_manager

        mock_response = {
            "result": {
                "job_id": "test-job-123",
                "state": JOB_STATE_COMPLETED,
                "result_count": 4,
                "create_time": "2026-03-31T07:30:00Z",
                "complete_time": "2026-03-31T07:30:15Z",
            }
        }
        mock_api_manager.get_censeye_job_status.return_value = mock_response

        main()

        mock_api_manager.get_censeye_job_status.assert_called_once_with("test-job-123")
        mock_siemplify.result.add_result_json.assert_called_once_with(mock_response)
        
        call_args = mock_siemplify.end.call_args[0]
        assert "completed successfully" in call_args[0]
        assert call_args[2] == EXECUTION_STATE_COMPLETED

    def test_get_status_in_progress(self, mock_siemplify_class, mock_api_manager_class):
        """Test getting status for job still in progress."""
        mock_siemplify = Mock()
        mock_siemplify_class.return_value = mock_siemplify

        mock_siemplify.extract_action_param.return_value = "test-job-456"

        mock_api_manager = Mock()
        mock_api_manager_class.return_value = mock_api_manager

        mock_response = {
            "result": {
                "job_id": "test-job-456",
                "state": JOB_STATE_STARTED,
                "create_time": "2026-03-31T07:30:00Z",
            }
        }
        mock_api_manager.get_censeye_job_status.return_value = mock_response

        main()

        call_args = mock_siemplify.end.call_args[0]
        assert "in progress" in call_args[0]
        assert call_args[2] == EXECUTION_STATE_INPROGRESS

    def test_get_status_failed(self, mock_siemplify_class, mock_api_manager_class):
        """Test getting status for failed job."""
        mock_siemplify = Mock()
        mock_siemplify_class.return_value = mock_siemplify

        mock_siemplify.extract_action_param.return_value = "test-job-789"

        mock_api_manager = Mock()
        mock_api_manager_class.return_value = mock_api_manager

        mock_response = {
            "result": {
                "job_id": "test-job-789",
                "state": JOB_STATE_FAILED,
                "create_time": "2026-03-31T07:30:00Z",
            }
        }
        mock_api_manager.get_censeye_job_status.return_value = mock_response

        main()

        call_args = mock_siemplify.end.call_args[0]
        assert "failed" in call_args[0]
        assert call_args[2] == EXECUTION_STATE_FAILED

    def test_get_status_empty_job_id(self, mock_siemplify_class, mock_api_manager_class):
        """Test validation error for empty job ID."""
        mock_siemplify = Mock()
        mock_siemplify_class.return_value = mock_siemplify

        mock_siemplify.extract_action_param.return_value = ""

        main()

        call_args = mock_siemplify.end.call_args[0]
        assert JOB_ID_REQUIRED_ERROR in call_args[0]
        assert call_args[2] == EXECUTION_STATE_FAILED
