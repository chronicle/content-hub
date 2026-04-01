# Copyright 2026 Google LLC
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

from unittest.mock import NonCallableMagicMock

import pytest
from core.action_wrapper import ActionContext
from core.api_manager import (
    GoogleCloudIdentityApiManager,
)
from core.orgunits_api_resource import (
    OrgUnitsApiResource,
)
from core.policies_api_resource import (
    PoliciesApiResource,
)
from google.auth.transport.requests import AuthorizedSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def auth_session() -> AuthorizedSession:
    """Authorized session"""
    return NonCallableMagicMock(spec=AuthorizedSession)


@pytest.fixture
def api_manager() -> GoogleCloudIdentityApiManager:
    """CloudIdentity manager"""
    return NonCallableMagicMock(
        spec=GoogleCloudIdentityApiManager,
    )


@pytest.fixture
def action_context() -> ActionContext:
    """Action context"""
    return NonCallableMagicMock(ActionContext)


@pytest.fixture
def policies_resource() -> PoliciesApiResource:
    """PoliciesApiResource for API Manager tests."""
    return NonCallableMagicMock(spec=PoliciesApiResource)


@pytest.fixture
def org_units_resource() -> PoliciesApiResource:
    """OrgUnitsApiResource for API Manager tests."""
    return NonCallableMagicMock(spec=OrgUnitsApiResource)
