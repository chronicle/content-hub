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

from typing import Iterable

from integration_testing import router
from integration_testing.common import get_request_payload
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction

from .product import GitSyncProduct


class GitSyncMockSession(MockSession[MockRequest, MockResponse, GitSyncProduct]):
    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.get_system_version,
            self.get_workflow_menu_cards_env_filter,
            self.get_workflow_menu_cards,
            self.get_workflow_full_info_env_filter,
            self.get_workflow_full_info,
            self.get_soc_roles,
            self.get_workflow_categories,
            self.save_workflow_definitions,
            self.get_environment_names,
            self.get_environment_groups,
            self.get_environment_installed_integrations,
        ]

    @router.post(r".*/settings/GetEnvironmentNames")
    def get_environment_names(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={"objectsList": ["Default Environment"], "metadata": {"totalNumberOfPages": 1}},
            status_code=200,
        )

    @router.get(r".*/environment-groups")
    def get_environment_groups(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={"groups": []},
            status_code=200,
        )

    @router.post(r".*/integrations/GetEnvironmentInstalledIntegrations")
    def get_environment_installed_integrations(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={"instances": []},
            status_code=200,
        )

    @router.get(r".*/settings/GetSystemVersion")
    def get_system_version(self, _: MockRequest) -> MockResponse:
        return MockResponse(content="\"6.1.38.77\"", status_code=200)

    @router.post(r".*/playbooks/GetWorkflowMenuCardsWithEnvFilter")
    def get_workflow_menu_cards_env_filter(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=[{"identifier": "local-playbook-uuid", "name": "Test Playbook"}],
            status_code=200,
        )

    @router.post(r".*/playbooks/GetWorkflowMenuCards")
    def get_workflow_menu_cards(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=[{"identifier": "local-playbook-uuid", "name": "Test Playbook"}],
            status_code=200,
        )

    @router.get(r".*/playbooks/GetWorkflowFullInfoWithEnvFilterByIdentifier/.*")
    def get_workflow_full_info_env_filter(self, _: MockRequest) -> MockResponse:
        return MockResponse(content=self._product.local_playbook, status_code=200)

    @router.get(r".*/playbooks/GetWorkflowFullInfoByIdentifier/.*")
    def get_workflow_full_info(self, _: MockRequest) -> MockResponse:
        return MockResponse(content=self._product.local_playbook, status_code=200)

    @router.post(r".*/socroles/getSocRoles")
    def get_soc_roles(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={"objectsList": [], "metadata": {"totalNumberOfPages": 1}},
            status_code=200,
        )

    @router.get(r".*/playbooks/GetWorkflowCategories")
    def get_workflow_categories(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=[{"id": 10, "name": "Default"}],
            status_code=200,
        )

    @router.post(r".*/playbooks/SaveWorkflowDefinitions")
    def save_workflow_definitions(self, request: MockRequest) -> MockResponse:
        payload = get_request_payload(request)
        self._product.saved_playbook = payload
        return MockResponse(content={"status": "success"}, status_code=200)
