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

"""HTTP session router for Google Cloud Compute tests.

Routes are matched against the request URL using the @router.<method> decorator.
The ``MockSession`` base class dispatches every requests.Session call through the
registered routes so that no real network traffic is produced.
"""
from __future__ import annotations

from typing import Iterable

from google_cloud_compute.tests.core.product import GoogleCloudCompute
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class GoogleCloudComputeSession(
    MockSession[MockRequest, MockResponse, GoogleCloudCompute]
):
    """Routes HTTP calls to the GoogleCloudCompute fake product."""

    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            # Ping / zones
            self.list_zones,
            # Instances
            self.list_instances_aggregated,
            self.list_instances,
            self.get_instance,
            self.start_instance,
            self.stop_instance,
            self.delete_instance,
            # Labels
            self.set_labels,
            # Tags
            self.set_tags,
            # IAM policy
            self.get_instance_iam_policy,
            self.set_instance_iam_policy,
            # External IP / network interfaces
            self.delete_access_config,
            self.update_network_interface,
            # Firewall rules
            self.get_firewall_rule,
            self.patch_firewall_rule,
            # OS Config patch jobs
            self.execute_patch_job,
            self.get_patch_job,
            # Generic operation polling (self-link)
            self.get_operation_by_self_link,
            # Platform SDK endpoints (entity enrichment, result reporting)
            self.update_entities,
        ]

    # ------------------------------------------------------------------ #
    # Zones / Ping                                                        #
    # ------------------------------------------------------------------ #

    @router.get(r".*/zones(\?.*)?$")
    def list_zones(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.get_zones()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    # ------------------------------------------------------------------ #
    # Instances                                                           #
    # ------------------------------------------------------------------ #

    @router.get(r".*/aggregated/instances(\?.*)?$")
    def list_instances_aggregated(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.get_instances_aggregated()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    @router.get(r".*/zones/[^/]+/instances(\?.*)?$")
    def list_instances(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.get_instances()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    @router.get(r".*/zones/[^/]+/instances/[^/]+$")
    def get_instance(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.get_instance()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    @router.post(r".*/instances/[^/]+/start$")
    def start_instance(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.post_operation()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    @router.post(r".*/instances/[^/]+/stop$")
    def stop_instance(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.post_operation()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    @router.delete(r".*/instances/[^/]+$")
    def delete_instance(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.delete_operation()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    # ------------------------------------------------------------------ #
    # Labels                                                              #
    # ------------------------------------------------------------------ #

    @router.post(r".*/instances/[^/]+/setLabels$")
    def set_labels(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.post_operation()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    # ------------------------------------------------------------------ #
    # Tags                                                                #
    # ------------------------------------------------------------------ #

    @router.post(r".*/instances/[^/]+/setTags$")
    def set_tags(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.post_operation()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    # ------------------------------------------------------------------ #
    # IAM policy                                                          #
    # ------------------------------------------------------------------ #

    @router.get(r".*/instances/[^/]+/getIamPolicy$")
    def get_instance_iam_policy(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.get_instance_iam_policy()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    @router.post(r".*/instances/[^/]+/setIamPolicy$")
    def set_instance_iam_policy(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.set_instance_iam_policy_api()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    # ------------------------------------------------------------------ #
    # External IP removal                                                 #
    # ------------------------------------------------------------------ #

    @router.post(r".*/instances/[^/]+/deleteAccessConfig$")
    def delete_access_config(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.post_operation()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    @router.patch(r".*/instances/[^/]+/updateNetworkInterface$")
    def update_network_interface(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.patch_operation()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    # ------------------------------------------------------------------ #
    # Firewall rules                                                      #
    # ------------------------------------------------------------------ #

    @router.get(r".*/global/firewalls/[^/]+$")
    def get_firewall_rule(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.get_firewall_rule()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    @router.patch(r".*/global/firewalls/[^/]+$")
    def patch_firewall_rule(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.patch_firewall_rule()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    # ------------------------------------------------------------------ #
    # OS Config patch jobs                                                #
    # ------------------------------------------------------------------ #

    @router.post(r".*/patchJobs:execute$")
    def execute_patch_job(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.execute_patch_job()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    @router.get(r".*patchJobs/[^/]+$")
    def get_patch_job(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.get_patch_job()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    # ------------------------------------------------------------------ #
    # Generic operation polling (operations/<id>)                        #
    # ------------------------------------------------------------------ #

    @router.get(r".*/operations/[^/]+$")
    def get_operation_by_self_link(self, _: MockRequest) -> MockResponse:
        try:
            data = self._product.get_operation()
            return MockResponse(content=data, status_code=200)
        except Exception as exc:
            return MockResponse(content={"error": {"message": str(exc)}}, status_code=500)

    # ------------------------------------------------------------------ #
    # Platform SDK endpoints                                              #
    # ------------------------------------------------------------------ #

    @router.post(r".*/sdk/UpdateEntities")
    def update_entities(self, _: MockRequest) -> MockResponse:
        """Stub for the SOAR platform entity-update endpoint."""
        return MockResponse(content="", status_code=201)
