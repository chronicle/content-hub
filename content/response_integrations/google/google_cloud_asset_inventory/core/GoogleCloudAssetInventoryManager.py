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

import json
import re
from typing import Iterable
from urllib.parse import urljoin, quote_plus

from google.auth.exceptions import RefreshError

from soar_sdk.SiemplifyLogger import SiemplifyLogger
from TIPCommon.rest.auth import build_credentials_from_sa
from TIPCommon.rest.gcp import (
    get_http_client,
    get_workload_sa_email,
    retrieve_project_id,
)
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_empty_string_or_none
from . import constants
from . import datamodels
from .exceptions import (
    GoogleCloudAssetInventoryError,
    ProjectOrOrganizationNotFoundError,
    InvalidServiceAccountError,
)
from .GoogleCloudAssetInventoryParser import GoogleCloudAssetInventoryParser
from .UtilsManager import validate_response


class GoogleCloudAssetInventoryManager:
    """Google Cloud Asset Inventory Manager for handling
    action's core functionalities
    """

    def __init__(
        self,
        api_root: str,
        service_account_: SingleJson,
        workload_identity_email: str,
        verify_ssl: bool,
        logger: SiemplifyLogger,
        organization_id: str = "",
        quota_project_id: str = "",
        project_id: str = "",
    ) -> None:
        """The method is used to init an object of Manager class

        Args:
            api_root: API root
            service_account_: JSON string containing service account info
            workload_identity_email: Workload identity email to impersonate
            verify_ssl: Specifies if certificate that is configured on the api
                root should be validated
            logger: To log the data in the console
            organization_id: Organization id
            quota_project_id: The quota project ID to use for billing the account
            project_id: Project id. takes precedence over organization id
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.logger = logger

        self.request_level_type = "projects"
        if not is_empty_string_or_none(project_id):
            self.request_level_id = project_id
        elif not is_empty_string_or_none(organization_id):
            self.request_level_type = "organizations"
            self.request_level_id = organization_id
        else:
            self.request_level_id = retrieve_project_id(
                service_account_, workload_identity_email
            )

        self.parser = GoogleCloudAssetInventoryParser()
        try:
            credentials = build_credentials_from_sa(
                user_service_account=service_account_,
                quota_project_id=quota_project_id,
                target_principal=workload_identity_email,
                scopes=constants.SCOPES,
                verify_ssl=verify_ssl,
            )
        except RefreshError as e:
            workload_sa = get_workload_sa_email("Principal Could not be found")
            raise GoogleCloudAssetInventoryError(
                "Impersonation is not allowed for the provided service "
                f"account {workload_identity_email}! In Order to use Workload Identity "
                'Email, Add the "Service Account Token Creator" IAM Role to '
                f"{workload_sa} on the desired Service Account"
            ) from e

        self.http_client = get_http_client(credentials, verify_ssl)

    def _get_full_url(self, url_id: str, **kwargs) -> str:
        """Get full url from url identifier.

        Args:
            url_id: The id of url
            kwargs: Variables passed for string formatting
        Returns:
            The full url
        """
        return urljoin(self.api_root, constants.ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self) -> None:
        """Test the connectivity"""

        if not self.request_level_id:
            raise ProjectOrOrganizationNotFoundError(
                "No project id or organization id was found"
            )
        url = self._get_full_url(
            "ping", type=self.request_level_type, id=self.request_level_id
        )

        try:
            response_info, content = self.http_client.request(url, "GET")
        except json.decoder.JSONDecodeError as e:
            raise InvalidServiceAccountError("Invalid Service Account Details") from e

        status_code = response_info.get("status")
        validate_response(int(status_code), content)

    def get_resource_details(
        self, resource_names: set[str], fields_read_mask: Iterable[str]
    ) -> list:
        """Get asset details by resource names

        Args:
            resource_names: List of resource names for filtering
            fields_read_mask: List of fields to return in response for resource
        Returns:
            list of Resource objects
        """
        resource_objects = []
        query_string = ""
        or_operator = "%20OR%20"
        read_mask = ",".join(fields_read_mask)

        for name in resource_names:
            name_filter = f'name="{name}"'

            if (
                len(query_string) + len(or_operator) + len(name_filter)
                > constants.QUERY_CHARACTER_LIMIT
            ):
                resource_objects.extend(
                    self._get_resource_details_by_filter(
                        read_mask=read_mask, query_string=query_string
                    )
                )
                # Reset query string to avoid exceeding the query char limit
                query_string = name_filter
            else:
                query_string += (
                    or_operator + name_filter if query_string else name_filter
                )

        resource_objects.extend(
            self._get_resource_details_by_filter(
                read_mask=read_mask, query_string=query_string
            )
        )
        return resource_objects

    def _get_resource_details_by_filter(
        self, read_mask: str, query_string: str
    ) -> list:
        """Execute the resource details call with provided read_maks and query_string.

        Args:
            read_mask: CSV Read mask string will all fields needed to be retrieved
            query_string: Full query string to use in request
        Returns:
            List of Resource data models from parsed response
        """
        url = self._get_full_url(
            "get_resource_details",
            type=self.request_level_type,
            id=self.request_level_id,
            page_size=500,
            read_mask=read_mask,
            query=query_string,
        )
        response_info, content = self.http_client.request(url, "GET")
        status_code = response_info.get("status")
        validate_response(int(status_code), content)
        return self.parser.build_resource_objects(json.loads(content))

    def analyze_iam_policy(
        self,
        identity: str,
        roles: list[str],
        permissions: list[str],
        expand_roles: bool,
    ) -> list[datamodels.AnalysisQueryResult]:
        """Analyze IAM policy for specified identity.

        Args:
            identity: IAM identity to analyze
            roles: List of roles to look for
            permissions: List of permissions to look for
            expand_roles: Whether to expand permissions from roles

        Returns:
            List of analysis results.
        """
        url = self._get_full_url(
            "analyze_iam_policy", type=self.request_level_type, id=self.request_level_id
        )
        analysis_query = {
            "analysisQuery": {
                "identitySelector": {"identity": f"serviceAccount:{identity}"},
                "accessSelector": {"roles": roles, "permissions": permissions},
                "options": {"expandRoles": expand_roles},
            }
        }

        response_info, content = self.http_client.request(
            url,
            method="POST",
            body=json.dumps(analysis_query),
            headers={"X-HTTP-Method-Override": "GET"},
        )
        status_code = response_info.get("status")
        validate_response(int(status_code), content)

        json_response = json.loads(content)

        return (
            self.parser.build_analysis_query_results(
                json_response["mainAnalysis"]["analysisResults"]
            )
            if "analysisResults" in json_response["mainAnalysis"]
            else []
        )

    def _get_resource_snapshots(
        self, read_mask: list[str], asset_names: set[str]
    ) -> list[datamodels.ResourceSnapshot]:
        """Get resource snapshots call with provided read_mask and asset_names.

        Args:
            read_mask: List of fields to retrieve
            asset_names: Asset names to enrich snapshots for

        Returns:
            List of Resource data models from parsed response
        """
        url = self._get_full_url(
            "get_resource_snapshots",
            type=self.request_level_type,
            id=self.request_level_id,
            read_mask=",".join(read_mask),
            asset_names="&assetNames=".join(asset_names),
        )
        response_info, content = self.http_client.request(url, "GET")
        status_code = response_info.get("status")
        validate_response(int(status_code), content)
        return self.parser.build_resource_snapshots(json.loads(content))

    def get_resource_snapshots(
        self, read_mask: list[str], asset_names: set[str]
    ) -> list[datamodels.ResourceSnapshot]:
        """Get resource snapshots by batches up to 100 entries, handle not found.

        Args:
            read_mask: List of fields to retrieve
            asset_names: Asset names to enrich snapshots for

        Returns:
            List of Resource data joined across all responses.
        """

        assets_to_enrich = [quote_plus(asset) for asset in asset_names]
        query_assets = set()
        results = []

        while query_assets or assets_to_enrich:
            if assets_to_enrich and len(query_assets) < constants.MAX_ASSETS_TO_QUERY:
                query_assets.add(assets_to_enrich.pop())
                continue

            try:
                results.extend(
                    self._get_resource_snapshots(
                        read_mask=read_mask, asset_names=query_assets
                    )
                )
                query_assets = set()

            except GoogleCloudAssetInventoryError as e:
                not_found_resources_match = re.search(
                    constants.NOT_FOUND_RESOURCES_PATTERN, str(e)
                )
                if not_found_resources_match is None:
                    raise

                not_found_resources = [
                    quote_plus(resource_name)
                    for resource_name in not_found_resources_match.group(3).split(",")
                ]
                if not query_assets.intersection(not_found_resources):
                    raise

                query_assets.difference_update(not_found_resources)

        return results
