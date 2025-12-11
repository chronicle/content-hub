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

import pydantic
import pytest

import mp.core.constants
from mp.core.data_models.condition.condition_group import ConditionGroup
from mp.core.data_models.integrations.action_widget.metadata import (
    ActionWidgetMetadata,
    WidgetScope,
    WidgetSize,
)
from mp.core.data_models.integrations.connector.metadata import ConnectorMetadata
from mp.core.data_models.integrations.job.metadata import JobMetadata
from mp.core.data_models.integrations.job.parameter import JobParameter
from mp.core.data_models.widget.data import HtmlWidgetDataDefinition, WidgetType


class TestDescriptionLengthValidations:
    """Test validation of description length in various models."""

    def test_connector_description_too_long(self) -> None:
        """Test that a connector with too long a description fails validation."""
        too_long_description: str = "a" * (mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH + 1)

        with pytest.raises(pydantic.ValidationError) as exc_info:
            ConnectorMetadata(
                file_name="test_connector",
                creator="test creator",
                description=too_long_description,
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

        # Verify the error message contains something about the description field
        error_msg: str = str(exc_info.value).lower()
        assert "description" in error_msg
        assert "should have at most" in error_msg

    def test_connector_description_exact_length(self) -> None:
        """Test that a connector with exactly the max length description passes."""
        exact_length_description: str = "a" * mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH

        # Should not raise an exception
        connector: ConnectorMetadata = ConnectorMetadata(
            file_name="test_connector",
            creator="test creator",
            description=exact_length_description,
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

        assert connector.description == exact_length_description


class TestNameValidations:
    """Test validation of name fields in various models."""

    def test_widget_title_invalid_pattern(self) -> None:
        """Test that a widget with an invalid title fails validation."""
        invalid_titles: list[str] = [
            "Invalid@Title",  # Contains special character '@'
            "Invalid Title!",  # Contains special character '!'
            "Invalid_Title",  # Contains special character '!'
            "A" * (mp.core.constants.DISPLAY_NAME_MAX_LENGTH + 1),  # Too long
        ]

        for invalid_title in invalid_titles:
            with pytest.raises(pydantic.ValidationError) as exc_info:
                ActionWidgetMetadata(
                    file_name="test_widget",
                    title=invalid_title,
                    type_=WidgetType.TEXT,
                    scope=WidgetScope.ALERT,
                    action_identifier="",
                    description="Test description",
                    data_definition=mock.MagicMock(spec=HtmlWidgetDataDefinition),
                    condition_group=mock.MagicMock(spec=ConditionGroup),
                    default_size=WidgetSize.FULL_WIDTH,
                )

            # Verify the error message contains something about the title field
            error_text: str = str(exc_info.value).lower()
            assert (
                "title" in error_text
                or "pattern" in error_text
                or "should have at most" in error_text
            )

    def test_widget_title_valid(self) -> None:
        """Test that a widget with a valid title passes validation."""
        valid_titles: list[str] = [
            "Valid Title",
            "Title123",
            "Title-with-hyphens",
        ]

        for valid_title in valid_titles:
            # Should not raise an exception
            widget: ActionWidgetMetadata = ActionWidgetMetadata(
                file_name="test_widget",
                title=valid_title,
                type_=WidgetType.TEXT,
                scope=WidgetScope.ALERT,
                action_identifier="asd",
                description="Test description",
                data_definition=mock.MagicMock(spec=HtmlWidgetDataDefinition),
                condition_group=mock.MagicMock(spec=ConditionGroup),
                default_size=WidgetSize.FULL_WIDTH,
            )

            assert widget.title == valid_title


class TestParameterListValidations:
    """Test validation of parameter lists in various models."""

    def test_job_parameters_too_many(self) -> None:
        """Test that a job with too many parameters fails validation."""
        too_many_params: list[JobParameter] = [
            mock.MagicMock(spec=JobParameter)
            for _ in range(mp.core.constants.MAX_PARAMETERS_LENGTH + 1)
        ]

        with pytest.raises(pydantic.ValidationError) as exc_info:
            JobMetadata(
                file_name="test_job",
                creator="test creator",
                description="Test job description",
                integration="test_integration",
                is_custom=False,
                is_enabled=True,
                name="Test Job",
                parameters=too_many_params,  # Too many parameters
                run_interval_in_seconds=900,
                version=1.0,
            )

        # Verify the error message contains something about the "parameters" field
        error_msg: str = str(exc_info.value).lower()
        assert "parameters" in error_msg
        assert "should have at most" in error_msg

    def test_job_parameters_exact_max_length(self) -> None:
        """Test that a job with exactly max parameters passes validation."""
        exact_max_params: list[JobParameter] = [
            mock.MagicMock(spec=JobParameter)
            for _ in range(mp.core.constants.MAX_PARAMETERS_LENGTH)
        ]

        # Should not raise an exception
        job: JobMetadata = JobMetadata(
            file_name="test_job",
            creator="test creator",
            description="Test job description",
            integration="test_integration",
            is_custom=False,
            is_enabled=True,
            name="Test Job",
            parameters=exact_max_params,
            run_interval_in_seconds=900,
            version=1.0,
        )

        assert len(job.parameters) == mp.core.constants.MAX_PARAMETERS_LENGTH
