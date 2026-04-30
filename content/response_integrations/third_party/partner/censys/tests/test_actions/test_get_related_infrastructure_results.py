from __future__ import annotations

from unittest.mock import Mock, patch

from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED

from censys.actions.get_related_infrastructure_results import main
from censys.core.constants import JOB_ID_REQUIRED_ERROR


@patch("censys.actions.get_related_infrastructure_results.APIManager")
@patch("censys.actions.get_related_infrastructure_results.SiemplifyAction")
class TestGetRelatedInfrastructureResults:
    """Test Get Related Infrastructure Results action."""

    def test_get_results_success(self, mock_siemplify_class, mock_api_manager_class):
        """Test successful retrieval of results with table formatting."""
        mock_siemplify = Mock()
        mock_siemplify_class.return_value = mock_siemplify

        mock_siemplify.extract_action_param.return_value = "test-job-123"

        mock_api_manager = Mock()
        mock_api_manager_class.return_value = mock_api_manager
        hash_256 = "2cc63dd4bb612501f18f6b25441bf9adc3dcd35edd0f1beb9f6a30ae3262f942"
        mock_response = {
            "result": {
                "target": {"host_id": "14.84.5.68"},
                "results": [
                    {
                        "count": 5395,
                        "field_value_pairs": [
                            {
                                "field": "services.banner_hash_sha256",
                                "value": hash_256,
                            }
                        ],
                    },
                    {
                        "count": 36216,
                        "field_value_pairs": [
                            {
                                "field": "services.http.response.headers.key",
                                "value": "Content-Type",
                            },
                            {
                                "field": "services.http.response.headers.value",
                                "value": "text/plain",
                            },
                        ],
                    },
                ],
            }
        }
        mock_api_manager.get_censeye_job_results.return_value = mock_response

        main()

        mock_api_manager.get_censeye_job_results.assert_called_once_with("test-job-123")
        mock_siemplify.result.add_result_json.assert_called_once_with(mock_response)
        mock_siemplify.result.add_data_table.assert_called_once()

        call_args = mock_siemplify.end.call_args[0]
        assert "2 related infrastructure pivot(s)" in call_args[0]
        assert "41611" in call_args[0]  # Total assets

    def test_get_results_empty(self, mock_siemplify_class, mock_api_manager_class):
        """Test retrieval with no results."""
        mock_siemplify = Mock()
        mock_siemplify_class.return_value = mock_siemplify

        mock_siemplify.extract_action_param.return_value = "test-job-456"

        mock_api_manager = Mock()
        mock_api_manager_class.return_value = mock_api_manager

        mock_response = {
            "result": {
                "target": {"host_id": "14.84.5.68"},
                "results": [],
            }
        }
        mock_api_manager.get_censeye_job_results.return_value = mock_response

        main()

        call_args = mock_siemplify.end.call_args[0]
        assert "No related infrastructure results found" in call_args[0]

    def test_get_results_empty_job_id(
        self, mock_siemplify_class, mock_api_manager_class
    ):
        """Test validation error for empty job ID."""
        mock_siemplify = Mock()
        mock_siemplify_class.return_value = mock_siemplify

        mock_siemplify.extract_action_param.return_value = ""

        main()

        call_args = mock_siemplify.end.call_args[0]
        assert JOB_ID_REQUIRED_ERROR in call_args[0]
        assert call_args[2] == EXECUTION_STATE_FAILED

    def test_get_results_multi_field_pivot(
        self, mock_siemplify_class, mock_api_manager_class
    ):
        """Test formatting of multi-field pivots."""
        mock_siemplify = Mock()
        mock_siemplify_class.return_value = mock_siemplify

        mock_siemplify.extract_action_param.return_value = "test-job-789"

        mock_api_manager = Mock()
        mock_api_manager_class.return_value = mock_api_manager

        mock_response = {
            "result": {
                "target": {"webproperty_id": "example.com:443"},
                "results": [
                    {
                        "count": 892,
                        "field_value_pairs": [
                            {"field": "autonomous_system.asn", "value": "15169"},
                            {"field": "services.port", "value": "443"},
                        ],
                    }
                ],
            }
        }
        mock_api_manager.get_censeye_job_results.return_value = mock_response

        main()

        # Verify the API was called correctly
        mock_api_manager.get_censeye_job_results.assert_called_once_with("test-job-789")

        # Verify output message contains expected information
        end_call_args = mock_siemplify.end.call_args[0]
        assert "1 related infrastructure pivot(s)" in end_call_args[0]
        assert "892" in end_call_args[0]  # Total assets
