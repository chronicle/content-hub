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

import re

from integration_testing import router
from integration_testing.common import get_request_payload
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction

from .product import CloudIdentity


class CloudIdentitySession(MockSession[MockRequest, MockResponse, CloudIdentity]):
    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.list_policies,
            self.create_policy,
            self.patch_policy,
            self.get_policy,
            self.delete_policy,
            self.list_org_units,
        ]

    @router.get(r"/v1(?:beta1)?/policies$")
    def list_policies(self, request: MockRequest) -> MockResponse:
        try:
            if self._product._fail_requests_active:
                return MockResponse(content={"error": {"message": "Simulated API failure"}}, status_code=500)

            filter_str = request.kwargs.get("params", {}).get("filter")
            matched_policies = []
            for p in self._product.policies.values():
                if filter_str:
                    match = re.search(r'setting\.type\.matches\("([^"]+)"\)', filter_str)
                    if match:
                        setting_type = match.group(1)
                        p_setting_type = p.setting.get("type") if isinstance(p.setting, dict) else p.setting.type
                        if setting_type != ".*" and p_setting_type != setting_type:
                            continue
                matched_policies.append(p.to_dict())

            return MockResponse(content={"policies": matched_policies})
        except Exception as e:
            return MockResponse(content={"error": {"message": str(e)}}, status_code=500)

    @router.post(r"/v1beta1/policies$")
    def create_policy(self, request: MockRequest) -> MockResponse:
        try:
            if self._product._fail_requests_active:
                return MockResponse(content={"error": {"message": "Simulated API failure"}}, status_code=500)

            payload = get_request_payload(request)
            from cloud_identity.core.datamodels import Policy
            policy = Policy.from_dict(payload)
            created_policy = self._product.create_policy(policy)

            operation = {
                "done": True,
                "name": f"operations/create_{created_policy.get_id()}",
                "response": created_policy.to_dict(),
            }
            return MockResponse(content=operation)
        except Exception as e:
            return MockResponse(content={"error": {"message": str(e)}}, status_code=500)

    @router.patch(r"/v1beta1/policies/(?P<policy_id>[^/]+)$")
    def patch_policy(self, request: MockRequest) -> MockResponse:
        try:
            if self._product._fail_requests_active:
                return MockResponse(content={"error": {"message": "Simulated API failure"}}, status_code=500)

            payload = get_request_payload(request)
            from cloud_identity.core.datamodels import Policy
            policy = Policy.from_dict(payload)
            updated_policy = self._product.patch_policy(policy)

            operation = {
                "done": True,
                "name": f"operations/patch_{updated_policy.get_id()}",
                "response": updated_policy.to_dict(),
            }
            return MockResponse(content=operation)
        except Exception as e:
            return MockResponse(content={"error": {"message": str(e)}}, status_code=500)

    @router.get(r"/v1(?:beta1)?/policies/(?P<policy_id>[^/]+)$")
    def get_policy(self, request: MockRequest) -> MockResponse:
        try:
            if self._product._fail_requests_active:
                return MockResponse(content={"error": {"message": "Simulated API failure"}}, status_code=500)

            policy_id = request.kwargs.get("policy_id") or request.url.path.split("/")[-1]
            policy = self._product.get_policy(policy_id)
            return MockResponse(content=policy.to_dict())
        except Exception as e:
            return MockResponse(content={"error": {"message": str(e)}}, status_code=404)

    @router.delete(r"/v1beta1/policies/(?P<policy_id>[^/]+)$")
    def delete_policy(self, request: MockRequest) -> MockResponse:
        try:
            if self._product._fail_requests_active:
                return MockResponse(content={"error": {"message": "Simulated API failure"}}, status_code=500)

            policy_id = request.kwargs.get("policy_id") or request.url.path.split("/")[-1]
            policy = self._product.get_policy(policy_id)
            del self._product.policies[policy_id]

            operation = {
                "done": True,
                "name": f"operations/delete_{policy_id}",
                "response": policy.to_dict(),
            }
            return MockResponse(content=operation)
        except Exception as e:
            return MockResponse(content={"error": {"message": str(e)}}, status_code=500)

    @router.get(r"/admin/directory/v1/customer/(?P<customer_id>[^/]+)/orgunits$")
    def list_org_units(self, request: MockRequest) -> MockResponse:
        try:
            if self._product._fail_requests_active:
                return MockResponse(content={"error": {"message": "Simulated API failure"}}, status_code=500)

            org_units_list = [ou.to_dict() for ou in self._product.get_org_units()]
            return MockResponse(content={"organizationUnits": org_units_list})
        except Exception as e:
            return MockResponse(content={"error": {"message": str(e)}}, status_code=500)
