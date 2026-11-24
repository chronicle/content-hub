from __future__ import annotations
from unittest.mock import MagicMock
from soar_sdk.SiemplifyDataModel import EntityTypes
from zscaler.actions.RemoveFromBlacklist import (
    RemoveFromBlacklistAction,
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


class TestRemoveFromBlacklist:
    """
    Tests the RemoveFromBlacklist action.
    """

    def test_remove_entities_from_blacklist_success(
        self,
        mock_siemplify: MagicMock,
        zscaler_product: Zscaler,
        action_output: LegacyActionOutput,
    ) -> None:
        """
        Tests removing via Target Entities.
        """

        # Pre-populate blacklist
        zscaler_product.blacklist_urls = ["target-entity-domain.com", "8.8.8.8"]

        # Setup Target Entities to remove
        mock_siemplify.target_entities = [
            create_mock_entity("target-entity-domain.com", EntityTypes.DOMAIN),
            create_mock_entity("8.8.8.8", EntityTypes.ADDRESS),
        ]
        mock_siemplify.parameters = {}

        action = RemoveFromBlacklistAction()

        assert len(zscaler_product.blacklist_urls) == 2

        action.run()

        assert zscaler_product.blacklist_urls == []

        assert action_output.is_success is True
        assert (
            "Successfully removed the following entities from the Urls blacklist"
            in action_output.output_message
        )
        assert "target-entity-domain.com" in action_output.output_message
        assert "8.8.8.8" in action_output.output_message

    def test_remove_wildcard_domain_from_blacklist(
        self,
        mock_siemplify: MagicMock,
        zscaler_product: Zscaler,
        action_output: LegacyActionOutput,
    ) -> None:
        """
        Tests removing a wildcard domain with a leading dot from the blacklist.
        """
        zscaler_product.blacklist_urls = [".darkhorizons.com"]
        mock_siemplify.target_entities = []

        def mock_extract_action_param(param_name: str, _print_value: bool = False, **_kwargs: object) -> str:
            if param_name == "IOCs":
                return ".darkhorizons.com"
            return ""

        mock_siemplify.extract_action_param.side_effect = mock_extract_action_param

        action = RemoveFromBlacklistAction()
        action.run()

        assert zscaler_product.blacklist_urls == []
        assert action_output.is_success is True
        assert ".darkhorizons.com" in action_output.output_message
