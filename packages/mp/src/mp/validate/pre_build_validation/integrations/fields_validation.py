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

import dataclasses
import re
from typing import TYPE_CHECKING

from mp.core.data_models.integrations.integration import Integration
from mp.core.exceptions import NonFatalValidationError
from mp.core.exclusions import get_param_display_name_regex

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.data_models.integrations.action.metadata import ActionMetadata
    from mp.core.data_models.integrations.action.parameter import ActionParameter
    from mp.core.data_models.integrations.connector.metadata import ConnectorMetadata
    from mp.core.data_models.integrations.connector.parameter import ConnectorParameter
    from mp.core.data_models.integrations.integration_meta.metadata import IntegrationMetadata
    from mp.core.data_models.integrations.job.metadata import JobMetadata
    from mp.core.data_models.integrations.job.parameter import JobParameter


METADATA_NAME_REGEX: str = r"^[a-zA-Z0-9-\s]+$"
PARAM_NAME_REGEX: str = get_param_display_name_regex()


@dataclasses.dataclass(slots=True, frozen=True)
class FieldsValidation:
    name: str = "Fields Validation"

    @staticmethod
    def run(integration_path: Path) -> None:
        """Strict integration fields names.

        Args:
            integration_path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If the integration doesn't have a documentation link.

        """
        integration: Integration = Integration.from_non_built_path(integration_path)

        result: list[str] = []
        result.extend(_validate_action_metadata(list(integration.actions_metadata.values())))
        result.extend(_validate_connector_metadata(list(integration.connectors_metadata.values())))
        result.extend(_validate_job_metadata(list(integration.jobs_metadata.values())))
        result.extend(_integration_metadata(integration.metadata))

        if result:
            raise NonFatalValidationError("\n".join(result))


def _validate_action_metadata(all_actions_metadata: list[ActionMetadata]) -> list[str]:
    result: list[str] = []
    for metadata in all_actions_metadata:
        if not re.match(METADATA_NAME_REGEX, metadata.name):
            result.append(
                f"Action name: {metadata.name} does not match the regex: {METADATA_NAME_REGEX}"
            )
        result.extend(_validate_action_parameters(metadata.parameters))

    return result


def _validate_action_parameters(action_parameters: list[ActionParameter]) -> list[str]:
    result: list[str] = [
        f"Action Parameter name: {parameter.name} does not match the regex: {PARAM_NAME_REGEX}"
        for parameter in action_parameters
        if not re.match(PARAM_NAME_REGEX, parameter.name)
    ]
    return result


def _validate_connector_metadata(all_connectors_metadata: list[ConnectorMetadata]) -> list[str]:
    result: list[str] = []
    for metadata in all_connectors_metadata:
        if not re.match(METADATA_NAME_REGEX, metadata.name):
            result.append(
                f"Connector name: {metadata.name} does not match the regex: {METADATA_NAME_REGEX}"
            )
        result.extend(_validate_connector_parameters(metadata.parameters))
    return result


def _validate_connector_parameters(connector_parameters: list[ConnectorParameter]) -> list[str]:
    result: list[str] = [
        f"Connector Parameter name: {parameter.name} does not match the regex: {PARAM_NAME_REGEX}"
        for parameter in connector_parameters
        if not re.match(PARAM_NAME_REGEX, parameter.name)
    ]
    return result


def _validate_job_metadata(all_jobs_metadata: list[JobMetadata]) -> list[str]:
    result: list[str] = []
    for metadata in all_jobs_metadata:
        if not re.match(METADATA_NAME_REGEX, metadata.name):
            result.append(
                f"Job name: {metadata.name} does not match the regex: {METADATA_NAME_REGEX}"
            )
        result.extend(_validate_job_parameters(metadata.parameters))
    return result


def _validate_job_parameters(job_parameters: list[JobParameter]) -> list[str]:
    result: list[str] = [
        f"Job Parameter name: {parameter.name} does not match the regex: {PARAM_NAME_REGEX}"
        for parameter in job_parameters
        if not re.match(PARAM_NAME_REGEX, parameter.name)
    ]
    return result


def _integration_metadata(integration_metadata: IntegrationMetadata) -> list[str]:
    result: list[str] = []
    if not re.match(PARAM_NAME_REGEX, integration_metadata.name):
        result.append(
            f"Integration name: {integration_metadata.name} "
            f"does not match the regex: {METADATA_NAME_REGEX}\n"
        )

    return result
