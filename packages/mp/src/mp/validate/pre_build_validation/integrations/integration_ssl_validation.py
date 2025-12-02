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

from mp.core.exceptions import NonFatalValidationError
from mp.validate.utils import load_integration_def, validate_ssl_parameter_from_yaml

if TYPE_CHECKING:
    import pathlib

    from mp.core.custom_types import YamlFileContent


class SslParameterExistsInIntegrationValidation:
    name: str = "SSL Integration Validation"

    def run(self, integration_path: pathlib.Path) -> None:  # noqa: PLR6301
        """Run validation for SSL parameters in the integration.

        Args:
            integration_path: The path to the integration directory.

        Raises:
            NonFatalValidationError: If there are any SSL parameter validation errors
                in the integration.

        """
        integration_def: YamlFileContent = load_integration_def(integration_path)
        validation_output_msg: str | None = validate_ssl_parameter_from_yaml(integration_def)
        if validation_output_msg is not None:
            raise NonFatalValidationError(validation_output_msg)
