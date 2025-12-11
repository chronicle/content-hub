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

from mp.validate.pre_build_validation.common.version_bump_validation import VersionBumpValidation

from .connectors_documentation_link_validation import ConnectorsHasDocumentationLinkValidation
from .connectors_ssl_validation import SslParameterExistsInConnectorsValidation
from .custom_validation import NoCustomComponentsInIntegrationValidation
from .disabled_validation import NoDisabledComponentsInIntegrationValidation
from .documentation_link_validation import IntegrationHasDocumentationLinkValidation
from .integration_ssl_validation import SslParameterExistsInIntegrationValidation
from .mapping_rules_validation import IntegrationHasMappingRulesIfHasConnectorValidation
from .ping_validation import IntegrationHasPingActionValidation
from .required_dependencies_validation import RequiredDevDependenciesValidation
from .structure_validation import IntegrationFileStructureValidation
from .uv_lock_validation import UvLockValidation

if TYPE_CHECKING:
    from mp.validate.pre_build_validation import Validator


def get_integration_pre_build_validations() -> list[Validator]:
    """Get a list of all available pre-build validations.

    Returns:
        A list of all `Validator` instances.

    """
    return _get_non_priority_validations() + _get_priority_validations()


def _get_non_priority_validations() -> list[Validator]:
    return [
        UvLockValidation(),
        VersionBumpValidation(),
        RequiredDevDependenciesValidation(),
        NoCustomComponentsInIntegrationValidation(),
        NoDisabledComponentsInIntegrationValidation(),
        IntegrationHasPingActionValidation(),
        IntegrationHasMappingRulesIfHasConnectorValidation(),
        SslParameterExistsInIntegrationValidation(),
        SslParameterExistsInConnectorsValidation(),
        IntegrationHasDocumentationLinkValidation(),
        ConnectorsHasDocumentationLinkValidation(),
    ]


def _get_priority_validations() -> list[Validator]:
    return [
        IntegrationFileStructureValidation(),
    ]
