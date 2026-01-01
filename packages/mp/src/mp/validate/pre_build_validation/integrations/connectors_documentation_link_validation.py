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
from typing import TYPE_CHECKING

import mp.core.constants
from mp.core.exceptions import NonFatalValidationError
from mp.core.utils import filter_and_map_yaml_files
from mp.validate.utils import (
    extract_name,
    load_components_defs,
)

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.custom_types import ConnectorName, YamlFileContent


@dataclasses.dataclass(slots=True, frozen=True)
class ConnectorsHasDocumentationLinkValidation:
    name: str = "Connectors Documentation Link Validation"

    @staticmethod
    def run(validation_path: Path) -> None:
        """Check if the integration's connectors has a documentation link.

        Args:
            validation_path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If any of the integration's connectors doesn't have a
            documentation link.

        """
        components_defs: dict[str, list[YamlFileContent]] = load_components_defs(
            validation_path, mp.core.constants.CONNECTORS_DIR
        )
        connectors_without_documentation_link: list[ConnectorName] = filter_and_map_yaml_files(
            components_defs.get(mp.core.constants.CONNECTORS_DIR, []),
            _missing_documentation_link,
            extract_name,
        )
        if connectors_without_documentation_link:
            formatted_connectors: str = "\n- ".join(connectors_without_documentation_link)
            msg: str = (
                f"Integration '{validation_path.name}' contains connectors with missing "
                f"documentation link:\n- {formatted_connectors}"
            )
            raise NonFatalValidationError(msg)


def _missing_documentation_link(yaml_content: YamlFileContent) -> bool:
    """Filter function to check if a component doesn't have a documentation link.

    Returns:
        True if the component doesn't have a documentation link.

    """
    return (
        not yaml_content.get("documentation_link")
        and yaml_content.get("name")
        not in mp.core.constants.EXCLUDED_CONNECTOR_NAMES_WITHOUT_DOCUMENTATION_LINK
    )
