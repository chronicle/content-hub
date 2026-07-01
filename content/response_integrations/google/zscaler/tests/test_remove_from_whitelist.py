# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import pathlib
from unittest.mock import MagicMock
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..actions.RemoveFromWhitelist import (
    RemoveFromWhitelistAction,
)
from ..tests.conftest import LegacyActionOutput
from ..tests.core.zscaler import Zscaler


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
