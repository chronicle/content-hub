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

from unittest.mock import MagicMock, patch

import pytest
from soar_sdk.SiemplifyAction import SiemplifyAction

from ...core.AttachmentsManager import AttachmentsManager, ExecutionScope


@pytest.fixture
def mock_siemplify():
    siemplify = MagicMock(spec=SiemplifyAction)
    siemplify.LOGGER = MagicMock()
    siemplify.case = MagicMock()
    siemplify.current_alert = MagicMock()
    return siemplify


@pytest.fixture
def attachments_manager(mock_siemplify):
    with patch(
        "content.response_integrations.power_ups.email_utilities.core.AttachmentsManager.get_attachments_metadata",
        return_value=[],
    ), patch.object(AttachmentsManager, "get_alert_entities", return_value=[]):
        return AttachmentsManager(mock_siemplify)


class TestAttachmentsManagerScope:
    def test_get_target_alerts_alert_scope_success(self, attachments_manager):
        """Test target alerts in Alert scope when current_alert is present."""
        attachments_manager.siemplify.soar_action = MagicMock()
        attachments_manager.siemplify.soar_action.execution_scope = (
            ExecutionScope.Alert.value
        )
        attachments_manager.siemplify.current_alert = MagicMock(identifier="alert_1")

        targets = attachments_manager.get_target_alerts()

        assert len(targets) == 1
        assert targets[0].identifier == "alert_1"

    def test_get_target_alerts_alert_scope_no_alert(self, attachments_manager):
        """Test target alerts in Alert scope when current_alert is None (should raise ValueError)."""
        attachments_manager.siemplify.soar_action = MagicMock()
        attachments_manager.siemplify.soar_action.execution_scope = (
            ExecutionScope.Alert.value
        )
        attachments_manager.siemplify.current_alert = None

        with pytest.raises(ValueError, match="Action cannot run on case, only on alerts"):
            attachments_manager.get_target_alerts()

    def test_get_target_alerts_case_scope(self, attachments_manager):
        """Test target alerts in Case scope (should return all case alerts)."""
        attachments_manager.siemplify.soar_action = MagicMock()
        attachments_manager.siemplify.soar_action.execution_scope = (
            ExecutionScope.Case.value
        )
        alert1 = MagicMock(identifier="alert_1")
        alert2 = MagicMock(identifier="alert_2")
        attachments_manager.siemplify.case.alerts = [alert1, alert2]

        targets = attachments_manager.get_target_alerts()

        assert len(targets) == 2
        assert targets[0].identifier == "alert_1"
        assert targets[1].identifier == "alert_2"

    def test_get_attachments_for_target_alerts_alert_scope(self, attachments_manager):
        """Test filtering attachments for Alert scope."""
        attachments_manager.siemplify.soar_action = MagicMock()
        attachments_manager.siemplify.soar_action.execution_scope = (
            ExecutionScope.Alert.value
        )
        attachments_manager.siemplify.current_alert = MagicMock(identifier="alert_1")

        # Set up some dummy attachments
        attachments_manager.attachments = [
            {"type": 4, "alertIdentifier": "alert_1", "name": "att_1"},
            {"type": 4, "alertIdentifier": "alert_2", "name": "att_2"},  # Different alert
            {"type": 3, "alertIdentifier": "alert_1", "name": "att_3"},  # Not type 4
        ]

        filtered = attachments_manager.get_attachments_for_target_alerts()

        assert len(filtered) == 1
        assert filtered[0]["name"] == "att_1"

    def test_get_attachments_for_target_alerts_case_scope(self, attachments_manager):
        """Test filtering attachments for Case scope (should get attachments for all alerts)."""
        attachments_manager.siemplify.soar_action = MagicMock()
        attachments_manager.siemplify.soar_action.execution_scope = (
            ExecutionScope.Case.value
        )

        alert1 = MagicMock(identifier="alert_1")
        alert2 = MagicMock(identifier="alert_2")
        attachments_manager.siemplify.case.alerts = [alert1, alert2]

        attachments_manager.attachments = [
            {"type": 4, "alertIdentifier": "alert_1", "name": "att_1"},
            {"type": 4, "alertIdentifier": "alert_2", "name": "att_2"},
            {"type": 4, "alertIdentifier": "alert_3", "name": "att_3"},  # Not in case
        ]

        filtered = attachments_manager.get_attachments_for_target_alerts()

        assert len(filtered) == 2
        names = [item["name"] for item in filtered]
        assert "att_1" in names
        assert "att_2" in names
