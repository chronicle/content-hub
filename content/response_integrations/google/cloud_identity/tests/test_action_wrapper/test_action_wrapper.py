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

from unittest.mock import Mock

from core.action_wrapper import ActionContext, ActionRunner
from TIPCommon.base.action import EntityTypesEnum


def test_action_runner_sets_supported_entities():
    """Test that ActionRunner sets supported entities on context."""
    # GIVEN
    mock_function = Mock()
    supported_entities = [EntityTypesEnum.URL, EntityTypesEnum.DOMAIN]
    runner = ActionRunner(
        mock_function,
        integration_name="test_integration",
        action_name="test_action",
        supported_entities=supported_entities,
    )

    mock_context = Mock(spec=ActionContext)
    mock_logger = Mock()
    mock_context.get_logger.return_value = mock_logger

    # WHEN
    runner.run(context=mock_context)

    # THEN
    mock_context.set_supported_entities.assert_called_once_with(
        supported_entities
    )
    mock_function.assert_called_once()


def test_get_entities_logs_unsupported_entities():
    """Test that get_entities logs unsupported entities."""
    # GIVEN
    context = ActionContext.__new__(ActionContext)
    context._supported_entities = [EntityTypesEnum.URL]

    mock_entity_supported = Mock()
    mock_entity_supported.entity_type = EntityTypesEnum.URL
    mock_entity_supported.identifier = "http://example.com"

    mock_entity_unsupported = Mock()
    mock_entity_unsupported.entity_type = EntityTypesEnum.DOMAIN
    mock_entity_unsupported.identifier = "example.com"

    mock_siemplify = Mock()
    mock_siemplify.target_entities = [
        mock_entity_supported,
        mock_entity_unsupported,
    ]
    context._siemplify_action = mock_siemplify

    mock_logger = Mock()
    context.get_logger = Mock(return_value=mock_logger)

    # WHEN
    entities = context.get_entities()

    # THEN
    assert entities == [mock_entity_supported]
    mock_logger.debug.assert_called_once_with(
        f"Entity: example.com -> {EntityTypesEnum.DOMAIN} not in {context._supported_entities}"
    )


def test_get_entities_logs_unknown_entity_type():
    """Test that get_entities logs unknown entity types."""
    # GIVEN
    context = ActionContext.__new__(ActionContext)
    context._supported_entities = [EntityTypesEnum.URL]

    mock_entity = Mock()
    mock_entity.entity_type = "USERUNIQNAME"
    mock_entity.identifier = "user1"

    mock_siemplify = Mock()
    mock_siemplify.target_entities = [mock_entity]
    context._siemplify_action = mock_siemplify

    mock_logger = Mock()
    context.get_logger = Mock(return_value=mock_logger)

    # WHEN
    entities = context.get_entities()

    # THEN
    assert entities == []
    mock_logger.debug.assert_called_once_with(
        f"Entity: user1 -> USERUNIQNAME not in {context._supported_entities}"
    )
        
