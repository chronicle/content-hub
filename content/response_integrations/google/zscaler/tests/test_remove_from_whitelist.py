from __future__ import annotations
from unittest.mock import MagicMock
from soar_sdk.SiemplifyDataModel import EntityTypes
from zscaler.actions.RemoveFromWhitelist import (
    RemoveFromWhitelistAction,
)
from zscaler.tests.conftest import LegacyActionOutput
from zscaler.tests.core.zscaler import Zscaler


def create_mock_entity(identifier: str, entity_type: str) -> MagicMock:
    """Local factory for creating mock entities."""
    entity = MagicMock()
    entity.identifier = identifier
    entity.entity_type = entity_type
    entity.is_internal = False
    return entity


class TestRemoveFromWhitelist:
    """
    Tests the RemoveFromWhitelist action.
    """

    def test_remove_entities_from_whitelist_success(
        self,
        mock_siemplify: MagicMock,
        zscaler_product: Zscaler,
        action_output: LegacyActionOutput,
    ) -> None:
        """
        Tests removing via Target Entities.
        """

        zscaler_product.whitelist_urls = ["dhnconstrucciones.com.ar", "5.5.5.5"]

        mock_siemplify.target_entities = [
            create_mock_entity("dhnconstrucciones.com.ar", EntityTypes.DOMAIN)
        ]
        mock_siemplify.parameters = {}

        action = RemoveFromWhitelistAction()

        assert len(zscaler_product.whitelist_urls) == 2

        action.run()

        assert zscaler_product.whitelist_urls == ["5.5.5.5"]

        assert action_output.is_success is True
        assert (
            "Successfully removed the following entities from the Urls whitelist"
            in action_output.output_message
        )
        assert "dhnconstrucciones.com.ar" in action_output.output_message

    def test_remove_wildcard_domain_from_whitelist(
        self,
        mock_siemplify: MagicMock,
        zscaler_product: Zscaler,
        action_output: LegacyActionOutput,
    ) -> None:
        """
        Tests removing a wildcard domain with a leading dot from the whitelist.
        """
        zscaler_product.whitelist_urls = [".darkhorizons.com", "5.5.5.5"]
        mock_siemplify.target_entities = []

        def mock_extract_action_param(param_name: str, _print_value: bool = False, **_kwargs: object) -> str:
            if param_name == "IOCs":
                return ".darkhorizons.com"
            return ""

        mock_siemplify.extract_action_param.side_effect = mock_extract_action_param

        action = RemoveFromWhitelistAction()
        action.run()

        assert zscaler_product.whitelist_urls == ["5.5.5.5"]
        assert action_output.is_success is True
        assert ".darkhorizons.com" in action_output.output_message
