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

""" Google Cloud Asset Inventory Parser module."""
from __future__ import annotations

from .datamodels import (
    AccessControlList,
    AnalysisQueryResult,
    Resource,
    ResourceSnapshot,
)


class GoogleCloudAssetInventoryParser:
    """Parses the json object of the resources from the response"""

    def build_resource_objects(self, raw_json: dict) -> list:
        """Builds multiple resource objects

        Args:
            raw_json: Raw json from the response having information
            for multiple resources

        Returns:
            A list of resource objects
        """
        raw_json = raw_json.get("results", [])
        return [self.build_resource_object(raw_data) for raw_data in raw_json]

    def build_resource_object(self, raw_data: dict) -> Resource:
        """Builds a single resource object

        Args:
            raw_data: A dict object for a single resource
        Returns:
            Resource object
        """
        return Resource(raw_data=raw_data, resource_name=raw_data["name"])

    def build_resource_snapshots(self, raw_json: dict) -> list:
        """Builds multiple resource snapshot objects

        Args:
            raw_json: Raw json from the response with information
            for multiple resource snapshots

        Returns:
            A list of resource snapshot objects
        """
        raw_json = raw_json.get("assets", [])
        return [self.build_resource_snapshot_object(raw_data) for raw_data in raw_json]

    def build_resource_snapshot_object(self, raw_data: dict) -> ResourceSnapshot:
        """Builds a single resource snapshot object

        Args:
            raw_data: A dict object for a single resource snapshot
        Returns:
            Resource object
        """
        return ResourceSnapshot(raw_data=raw_data, asset_name=raw_data["asset"]["name"])

    @staticmethod
    def build_access_control_list(raw_data: dict) -> AccessControlList:
        """Builds a list of parsed access control list object,

        Args:
            raw_data: A list of raw json from the response

        Returns:
            A parsed access control list object.
        """
        permissions = []
        roles = []

        for access in raw_data["accesses"]:
            if access.get("role"):
                roles.append(access.get("role"))
            elif access.get("permission"):
                permissions.append(access.get("permission"))

        return AccessControlList(
            raw_data=raw_data,
            resources=[r["fullResourceName"] for r in raw_data["resources"]],
            roles=roles,
            permissions=permissions,
        )

    def build_analysis_query_results(
        self, raw_data: list[dict]
    ) -> list[AnalysisQueryResult]:
        """Builds a list of analysis query result objects.

        Args:
            raw_data: A list of raw json from the response

        Returns:
            A list of analysis query parsed objects
        """
        return [
            AnalysisQueryResult(
                raw_data=aqr,
                attached_resource_full_name=aqr["attachedResourceFullName"],
                iam_binding_role=aqr["iamBinding"]["role"],
                access_control_lists=[
                    self.build_access_control_list(acl)
                    for acl in aqr["accessControlLists"]
                ],
            )
            for aqr in raw_data
        ]
