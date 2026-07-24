from __future__ import annotations
import unittest
from unittest.mock import patch, MagicMock, ANY

# Import main from EnrichEntities action script
from actions import EnrichEntities as enrich_action_module
from actions.EnrichEntities import main

class TestEnrichEntitiesAction(unittest.TestCase):
    @patch.object(enrich_action_module, "SiemplifyAction")
    @patch.object(enrich_action_module, "extract_configuration_param")
    @patch.object(enrich_action_module, "extract_action_param")
    @patch.object(enrich_action_module, "ActiveDirectoryManager")
    def test_enrich_entities_action_init(
        self,
        mock_ad_manager,
        mock_extract_action_param,
        mock_extract_config_param,
        mock_siemplify_action,
    ):
        # Configure mocks
        mock_siemplify = mock_siemplify_action.return_value
        mock_siemplify.target_entities = []
        
        def extract_action_side_effect(siemplify, param_name, **kwargs):
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
        
        # Verify that ActiveDirectoryManager was instantiated
        mock_ad_manager.assert_called_once_with(
            "dummy_value",  # server
            "dummy_value",  # domain
            "dummy_value",  # username
            "dummy_value",  # password
            False,          # use_ssl
            "dummy_value",  # custom_query_fields
            "dummy_value",  # ca_certificate
            mock_siemplify.LOGGER,
        )

if __name__ == "__main__":
    unittest.main()
