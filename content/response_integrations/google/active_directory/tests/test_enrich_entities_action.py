from __future__ import annotations
import unittest
from unittest.mock import patch, MagicMock, ANY

# Import main from EnrichEntities action script
from ..actions.EnrichEntities import main

class TestEnrichEntitiesAction(unittest.TestCase):
    @patch("content.response_integrations.google.active_directory.actions.EnrichEntities.SiemplifyAction")
    @patch("content.response_integrations.google.active_directory.actions.EnrichEntities.extract_configuration_param")
    @patch("content.response_integrations.google.active_directory.actions.EnrichEntities.extract_action_param")
    @patch("content.response_integrations.google.active_directory.actions.EnrichEntities.ActiveDirectoryManager")
    def test_enrich_entities_action_timeouts_passed(
        self,
        mock_ad_manager,
        mock_extract_action_param,
        mock_extract_config_param,
        mock_siemplify_action,
    ):
        # Configure mocks
        mock_siemplify = mock_siemplify_action.return_value
        mock_siemplify.target_entities = []
        
        # Configure extract_action_param side_effect
        # to return specific values for "Connection Timeout" and "Receive Timeout"
        def extract_action_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Connection Timeout":
                return 15
            elif param_name == "Receive Timeout":
                return 75
            # For other params, return appropriate dummy values
            if kwargs.get("input_type") == bool:
                return False
            return "dummy_value"
            
        mock_extract_action_param.side_effect = extract_action_side_effect
        
        def extract_config_side_effect(siemplify, provider_name, param_name, **kwargs):
            if kwargs.get("input_type") == bool or param_name == "Use SSL":
                return False
            return "dummy_value"
        mock_extract_config_param.side_effect = extract_config_side_effect
        
        # Call main with is_first_run = True
        main(is_first_run=True)
        
        # Verify that extract_action_param was called for "Connection Timeout" and "Receive Timeout"
        mock_extract_action_param.assert_any_call(
            mock_siemplify,
            param_name="Connection Timeout",
            input_type=int,
            is_mandatory=False,
            default_value=10,
        )
        mock_extract_action_param.assert_any_call(
            mock_siemplify,
            param_name="Receive Timeout",
            input_type=int,
            is_mandatory=False,
            default_value=60,
        )
        
        # Verify that ActiveDirectoryManager was instantiated with the extracted timeouts
        mock_ad_manager.assert_called_once_with(
            "dummy_value",  # server
            "dummy_value",  # domain
            "dummy_value",  # username
            "dummy_value",  # password
            False,          # use_ssl
            "dummy_value",  # custom_query_fields
            "dummy_value",  # ca_certificate
            mock_siemplify.LOGGER,
            connection_timeout=15,
            receive_timeout=75,
        )

if __name__ == "__main__":
    unittest.main()
