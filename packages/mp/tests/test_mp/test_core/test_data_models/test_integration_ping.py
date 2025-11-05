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

from typing import TYPE_CHECKING
from unittest import mock

import pytest

import mp.core.constants
from mp.core.data_models.action.metadata import ActionMetadata
from mp.core.data_models.integration import Integration
from mp.core.data_models.integration_meta.metadata import PythonVersion

if TYPE_CHECKING:
    from mp.core.data_models.integration_meta.metadata import IntegrationMetadata


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

    def test_build_integration_with_disabled_ping(self) -> None:
        """Test building integration with a disabled ping action."""
        # Create a minimal integration with the disabled ping action
        actions: dict[str, ActionMetadata] = {}
        ping_action: ActionMetadata = mock.MagicMock(spec=ActionMetadata)
        ping_action.name = "Ping"
        ping_action.file_name = "ping"
        ping_action.is_enabled = False  # Disabled ping action
        ping_action.is_custom = False
        actions["ping"] = ping_action

        # Mock the integration metadata
        metadata: IntegrationMetadata = mock.MagicMock()
        metadata.identifier = "test_integration"
        metadata.is_custom = False
        metadata.python_version = PythonVersion.PY_3_11

        # Test that creating the integration still works (ping exists but is disabled)
        with pytest.raises(RuntimeError, match="contains disabled scripts"):
            Integration(
                python_version=PythonVersion.PY_3_11.to_string(),
                identifier="test_integration",
                metadata=metadata,
                release_notes=[],
                custom_families=[],
                mapping_rules=[],
                common_modules=[],
                actions_metadata=actions,
                connectors_metadata={},
                jobs_metadata={},
                widgets_metadata={},
            )

    @mock.patch("mp.core.constants.EXCLUDED_INTEGRATIONS_IDS_WITHOUT_PING", set())
    def test_excluded_integrations_feature(self) -> None:
        """Test the excluded integrations feature works correctly."""
        # Create integration without 'ping'
        metadata: IntegrationMetadata = mock.MagicMock()
        metadata.identifier = "special_integration"
        metadata.is_custom = False
        metadata.python_version = PythonVersion.PY_3_11

        # First try with empty exclusion list - should fail
        with pytest.raises(RuntimeError, match="doesn't implement a 'ping' action"):
            Integration(
                python_version=PythonVersion.PY_3_11.to_string(),
                identifier="special_integration",
                metadata=metadata,
                release_notes=[],
                custom_families=[],
                mapping_rules=[],
                common_modules=[],
                actions_metadata={},  # No ping action
                connectors_metadata={},
                jobs_metadata={},
                widgets_metadata={},
            )

        # Now add to an exclusion list and try again
        with mock.patch.object(
            mp.core.constants,
            "EXCLUDED_INTEGRATIONS_IDS_WITHOUT_PING",
            {"special_integration"},
        ):
            # Should not raise exception
            integration: Integration = Integration(
                python_version=PythonVersion.PY_3_11.to_string(),
                identifier="special_integration",
                metadata=metadata,
                release_notes=[],
                custom_families=[],
                mapping_rules=[],
                common_modules=[],
                actions_metadata={},  # Still no ping action
                connectors_metadata={},
                jobs_metadata={},
                widgets_metadata={},
            )

            assert not integration.has_ping_action()  # Confirm no ping action
