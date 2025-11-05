# Copyright 2025 Google LLC
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

from unittest import mock

from mp.core.data_models.action.metadata import ActionMetadata
from mp.core.data_models.integration import Integration


class TestNoPingAction:
    """Test cases specifically for integrations without ping actions."""

    def test_has_ping_action_with_lowercase_name(self) -> None:
        """Test that _has_ping_action works with a lowercase action name."""
        # Create a minimal integration with a lowercase 'ping' action
        actions: dict[str, ActionMetadata] = {}
        ping_action: ActionMetadata = mock.MagicMock(spec=ActionMetadata)
        ping_action.name = "ping"  # Lowercase name
        ping_action.file_name = "ping"
        ping_action.is_enabled = True
        ping_action.is_custom = False
        actions["ping"] = ping_action

        # Mock the rest of the integration
        integration: mock.MagicMock = mock.MagicMock(spec=Integration)
        integration.actions_metadata = actions
        integration.has_ping_action = Integration.has_ping_action.__get__(integration)

        # Verify the method works with lowercase names
        assert integration.has_ping_action() is True

    def test_has_ping_action_with_uppercase_name(self) -> None:
        """Test that _has_ping_action works with the uppercase action name."""
        # Create a minimal integration with uppercase 'PING' action
        actions: dict[str, ActionMetadata] = {}
        ping_action: ActionMetadata = mock.MagicMock(spec=ActionMetadata)
        ping_action.name = "PING"  # Uppercase name
        ping_action.file_name = "ping"
        ping_action.is_enabled = True
        ping_action.is_custom = False
        actions["ping"] = ping_action

        # Mock the rest of the integration
        integration: mock.MagicMock = mock.MagicMock(spec=Integration)
        integration.actions_metadata = actions
        integration.has_ping_action = Integration.has_ping_action.__get__(integration)

        # Verify the method works with uppercase names
        assert integration.has_ping_action() is True
