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

import mp.core.constants
from mp.core.exceptions import NonFatalValidationError
from mp.validate.utils import (
    load_integration_def,
)

if TYPE_CHECKING:
    import pathlib

    from mp.core.custom_types import YamlFileContent


class IntegrationHasDocumentationLinkValidation:
    name: str = "Documentation Link Validation"

    def run(self, validation_path: pathlib.Path) -> None:  # noqa: PLR6301
        """Check if the integration has a documentation link.

        Args:
            validation_path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If the integration doesn't have a documentation link.

        """
        if (
            validation_path.name
            in mp.core.constants.EXCLUDED_INTEGRATIONS_WITHOUT_DOCUMENTATION_LINK
        ):
            return
        integration_def: YamlFileContent = load_integration_def(validation_path)
        if not integration_def.get("documentation_link"):
            msg: str = f"'{validation_path.name}' is missing a documentation link"
            raise NonFatalValidationError(msg)
