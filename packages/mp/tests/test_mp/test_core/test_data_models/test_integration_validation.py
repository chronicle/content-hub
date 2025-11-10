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

import pydantic
import pytest

import mp.core.constants
from mp.core.data_models.connector.metadata import ConnectorMetadata
from mp.core.data_models.job.metadata import JobMetadata
from mp.core.data_models.action_widget.metadata import ActionWidgetMetadata

if TYPE_CHECKING:
    from mp.core.data_models.job.parameter import JobParameter


class TestPydanticValidations:
    """Tests for Pydantic validations in various data models."""

    def test_integration_metadata_description_too_long(self) -> None:
        """Test that a description that's too long fails validation."""
        with pytest.raises(pydantic.ValidationError):
            ConnectorMetadata(
                file_name="test_connector",
                creator="test creator",
                description="a" * (mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH + 1),
                documentation_link=None,
                integration="test_integration",
                is_connector_rules_supported=True,
                is_custom=False,
                is_enabled=True,
                name="Test Connector",
                parameters=[],
                rules=[],
                version=1.0,
            )

    def test_widget_name_invalid_pattern(self) -> None:
        """Test that an invalid widget title fails validation."""
        with pytest.raises(pydantic.ValidationError):
            ActionWidgetMetadata(
                file_name="test_widget",
                title="Invalid@Title",  # @ is likely not allowed in the pattern
                type_=mock.MagicMock(),
                scope=mock.MagicMock(),
                action_identifier=None,
                description="Test widget description",
                data_definition=mock.MagicMock(),
                condition_group=mock.MagicMock(),
                default_size=mock.MagicMock(),
            )

    def test_job_parameter_list_too_long(self) -> None:
        """Test that a parameter list that's too long fails validation."""
        mock_params: list[JobParameter] = [
            mock.MagicMock() for _ in range(mp.core.constants.MAX_PARAMETERS_LENGTH + 1)
        ]
        with pytest.raises(pydantic.ValidationError):
            JobMetadata(
                file_name="test_job",
                creator="test creator",
                description="Test job description",
                integration="test_integration",
                is_custom=False,
                is_enabled=True,
                name="Test Job",
                parameters=mock_params,  # Too many parameters
                run_interval_in_seconds=900,
                version=1.0,
            )
