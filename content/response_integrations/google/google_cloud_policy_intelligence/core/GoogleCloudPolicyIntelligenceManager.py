from __future__ import annotations

from collections import namedtuple
import json

from google.auth.exceptions import RefreshError
from urllib.parse import urljoin

from soar_sdk.SiemplifyLogger import SiemplifyLogger
from TIPCommon.rest.auth import build_credentials_from_sa
from TIPCommon.rest.gcp import (
    get_http_client,
    get_workload_sa_email,
    retrieve_project_id,
)
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_empty_string_or_none

from google_cloud_policy_intelligence.core.constants import ENDPOINTS, SCOPES, NOT_FOUND_STATUS, MAX_ACTIVITIES_LIMIT
from google_cloud_policy_intelligence.core.datamodels import Activity
from google_cloud_policy_intelligence.core.exceptions import (
    GoogleCloudPolicyIntelligenceError,
    ProjectNotFoundError,
    InvalidServiceAccountError,
)
from google_cloud_policy_intelligence.core import GoogleCloudPolicyIntelligenceParser as parser
from google_cloud_policy_intelligence.core.UtilsManager import validate_response


GoogleAPIResponse = namedtuple("GoogleAPIResponse", ["response_info", "content"])


class GoogleCloudPolicyIntelligenceManager:
    """Google Cloud Policy Intelligence Manager for handling
    action's core functionalities
    """

    def __init__(
        self,
        api_root: str,
        service_account_: SingleJson,
        verify_ssl: bool,
        logger: SiemplifyLogger,
        workload_identity_email: str,
        location_id: str,
        project_id: str = "",
        quota_project_id: str = "",
    ) -> None:
        """The method is used to init an object of Manager class

        Args:
            api_root: API root
            project_id: Project id
            service_account_: JSON string containing service account info
            verify_ssl: Specifies if certificate that is configured on the api
                root should be validated
            logger: To log the data in the console
            workload_identity_email: Workload identity email to impersonate
            location_id: Google Cloud location id to use in endpoint
            quota_project_id: The quota project ID to use for billing the account
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.service_account = service_account_
        self.verify_ssl = verify_ssl
        self.quota_project_id = quota_project_id
        self.workload_identity_email = workload_identity_email
        self.project_id = (
            project_id
            if not is_empty_string_or_none(project_id)
            else retrieve_project_id(service_account_, workload_identity_email)
        )
        self.location_id = location_id

        self.http_client = None
        self.logger = logger
        self._prepare_http_client()

    def _prepare_http_client(self) -> None:
        """Prepare http client"""

        try:
            credentials = build_credentials_from_sa(
                user_service_account=self.service_account,
                quota_project_id=self.quota_project_id,
                target_principal=self.workload_identity_email,
                scopes=SCOPES,
                verify_ssl=self.verify_ssl,
            )
        except RefreshError as e:
            workload_sa = get_workload_sa_email("Principal Could not be found")
            raise GoogleCloudPolicyIntelligenceError(
                "Impersonation is not allowed for the provided service "
                f"account {self.workload_identity_email}! In Order to use Workload "
                f'Identity Email, Add the "Service Account Token Creator" IAM Role to '
                f"{workload_sa} on the desired Service Account"
            ) from e

        self.http_client = get_http_client(credentials, self.verify_ssl)

    def _get_full_url(self, url_id: str, **kwargs) -> str:
        """Get full url from url identifier.

        Args:
            url_id: The id of url
            kwargs: Variables passed for string formatting
        Returns:
            The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self) -> None:
        """Test the connectivity"""
        url = self._get_full_url(
            "ping",
            project_id=self.project_id,
            location_id=self.location_id
        )
        self.validated_request(url, "GET")

    def validated_request(self, url: str, http_method: str) -> GoogleAPIResponse:
        """Gets the validated response from the API.

        Args:
            url: The full url for the API request
            http_method: HTTP Request method

        Returns:
            Google API response and its content
        """
        try:
            response_info, content = self.http_client.request(url, http_method)
        except json.JSONDecodeError as e:
            raise InvalidServiceAccountError("Invalid Service Account Details") from e

        status_code = int(response_info.get("status"))

        if not content and status_code == NOT_FOUND_STATUS:
            raise ProjectNotFoundError(
                f"The project {self.project_id} is invalid or not found"
            )

        validate_response(status_code, content)

        return GoogleAPIResponse(response_info=response_info, content=content)

    def search_service_account_activity(
        self, resource_names: list, limit: int = MAX_ACTIVITIES_LIMIT
    ) -> list[Activity]:
        """Search activity related to service accounts.

        Args:
            resource_names: Full resource names of the service accounts
            limit: Specify the maximum number of activity to return.
                You can specify between 1 and 1,000.

        Returns:
            A list of activity objects
        """
        urls = [
            self._get_full_url(
                "search_activity",
                project_id=self.project_id,
                location_id=self.location_id,
                filter=f'activities.full_resource_name="{name}"',
                page_size=limit,
            )
            for name in resource_names
        ]
        responses = (self.validated_request(url, "GET") for url in urls)
        result = []
        for response in responses:
            result.extend(parser.build_activity_objects(json.loads(response.content)))

        return result
