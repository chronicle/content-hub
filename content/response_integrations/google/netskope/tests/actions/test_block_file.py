from __future__ import annotations
from typing import Any
from unittest.mock import MagicMock, patch

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED

from netskope.actions.BlockFile import main


class TestBlockFile:
    """Unit tests for BlockFile action."""

    def test_block_file_v2_success(self, mock_siemplify: MagicMock) -> None:
        """Test BlockFile with V2 success.

        Args:
            mock_siemplify (MagicMock): mock siemplify object.

        Returns:
            None
        """

        def get_config_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Api Root":
                return "https://test.com"
            if param_name == "V2 Api Key":
                return "v2_key"
            if param_name == "Verify SSL":
                return True
            return default

        def get_action_param_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Use V2 API":
                return True
            if param_name == "File ID":
                return "file_123"
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        with patch("requests.Session.request") as mock_post:
            mock_post.return_value.status_code = 200

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Successfully blocked file" in args[0]

    def test_block_file_v1_success(self, mock_siemplify: MagicMock) -> None:
        """Test BlockFile with V1 success.

        Args:
            mock_siemplify (MagicMock): mock siemplify object.

        Returns:
            None
        """

        def get_config_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Api Root":
                return "https://test.com"
            if param_name == "V1 Api Key":
                return "v1_key"
            if param_name == "Verify SSL":
                return True
            return default

        def get_action_param_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Use V2 API":
                return False
            if param_name == "File ID":
                return "file_123"
            if param_name == "Quarantine Profile ID":
                return "profile_123"
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        with patch("requests.Session.request") as mock_get:
            mock_get.return_value.status_code = 200

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Successfully blocked file" in args[0]

    def test_block_file_v2_already_processed(self, mock_siemplify: MagicMock) -> None:
        """Test BlockFile with V2 already processed (409).

        Args:
            mock_siemplify (MagicMock): mock siemplify object.

        Returns:
            None
        """

        def get_config_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Api Root":
                return "https://test.com"
            if param_name == "V2 Api Key":
                return "v2_key"
            if param_name == "Verify SSL":
                return True
            return default

        def get_action_param_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Use V2 API":
                return True
            if param_name == "File ID":
                return "file_123"
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        with patch("requests.Session.request") as mock_post:
            mock_post.return_value.status_code = 409
            mock_post.return_value.json.return_value = {
                "error": "quarantine incident was already processed"
            }

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "quarantine incident was already processed" in args[0]
            assert args[1] is True
            assert args[2] == EXECUTION_STATE_COMPLETED
