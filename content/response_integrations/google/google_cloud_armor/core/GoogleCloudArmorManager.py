from __future__ import annotations

import dataclasses
import json

import google_auth_httplib2
import httplib2
from soar_sdk.SiemplifyLogger import SiemplifyLogger

from TIPCommon.types import SingleJson
from google_cloud_armor.core import api_utils
from google_cloud_armor.core import constants
from google_cloud_armor.core import datamodels
from google_cloud_armor.core import GoogleCloudArmorParser as parser
from google_cloud_armor.core import AuthenticationManager as auth_manager


@dataclasses.dataclass
class ApiParameters:
    api_root: str
    project_id: str
    user_service_account: SingleJson = None
    workload_identity_email: str = None


class ApiManager:

    def __init__(
        self,
        session: httplib2.Http | google_auth_httplib2.AuthorizedHttp,
        api_parameters: ApiParameters,
        logger: SiemplifyLogger,
    ) -> None:
        """Manager for handling API interactions.

        This class provides functionality for managing API interactions.

        Args:
            session (httplib2.Http | google_auth_httplib2.AuthorizedHttp): Authenticated
                session httplib2.Http | google_auth_httplib2.AuthorizedHttp.
            api_parameters (ApiParameters): The parameters for the API.
            logger (SiemplifyLogger): The logger object.
        """
        self.session = session
        self.api_root = api_parameters.api_root
        self.project_id = auth_manager.create_resource_name(
            project_id=api_parameters.project_id,
            user_service_account=api_parameters.user_service_account,
            workload_identity_email=api_parameters.workload_identity_email,
        )
        self.logger = logger

    def test_connectivity(self) -> None:
        """Test connectivity for ping action to list security policies."""
        self.list_security_policies()

    def list_security_policies(
        self,
        region: str = constants.DEFAULT_ENVIRONMENT,
        limit: int = constants.DEFAULT_LIMIT_1,
    ) -> list[datamodels.ListSecurityPolicy]:
        """Get a list of security policies.

        Args:
            region (str): The name of the region.
            limit (int): Max results to fetch.

        Returns:
            list[ListSecurityPolicy]: The list of datamodels.ListSecurityPolicy object.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            endpoint_id="list_security_policies",
            endpoints=constants.ENDPOINTS,
            project_id=self.project_id,
            environment=api_utils.get_environment_string(region),
            limit=limit,
        )
        response_info, content = self.session.request(url, constants.GET)
        api_utils.validate_response(response_info, content)

        return parser.build_list_security_policies(json.loads(content).get("items", []))

    def create_security_policy(
        self, region: str, policy_json: SingleJson
    ) -> datamodels.CreateOrUpdateSecurityPolicy:
        """Create a security policy.

        Args:
            region (str): The region for which the security policy is created.
            policy_json (SingleJson): The JSON data representing the security policy to
                create.

        Returns:
            CreateOrUpdateSecurityPolicy: The created security policy object.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            endpoint_id="create_security_policy",
            endpoints=constants.ENDPOINTS,
            project_id=self.project_id,
            environment=api_utils.get_environment_string(region),
        )
        policy_data = json.dumps(policy_json)

        response_info, content = self.session.request(url, constants.POST, policy_data)
        api_utils.validate_response(response_info, content)

        return parser.build_create_or_update_security_policy(json.loads(content))

    def get_security_policy(
        self, region: str, security_policy: str
    ) -> datamodels.ListSecurityPolicy:
        """Get a security policy by name.

        Args:
            region (str): The region where the security policy is located.
            security_policy (str): The name of the security policy to retrieve.

        Returns:
            ListSecurityPolicy: The retrieved security policy object.

        Raises:
            GoogleCloudArmorPolicyNotFoundError: If the specified security policy is not
                found.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            endpoint_id="get_security_policy",
            endpoints=constants.ENDPOINTS,
            project_id=self.project_id,
            environment=api_utils.get_environment_string(region),
            security_policy=security_policy,
        )
        response_info, content = self.session.request(url, constants.GET)
        api_utils.validate_response(response_info, content)

        policy = parser.build_list_security_policies([json.loads(content)])

        return policy[0]

    def update_security_policy(
        self, policy_name: str, region: str, policy_json: SingleJson
    ) -> datamodels.CreateOrUpdateSecurityPolicy:
        """Update a security policy.

        Args:
            policy_name (str): The name of the security policy to update.
            region (str): The region where the security policy is located.
            policy_json (SingleJson): The JSON data representing the updated security
                policy.

        Returns:
            CreateOrUpdateSecurityPolicy: The updated security policy object.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            endpoint_id="update_security_policy",
            endpoints=constants.ENDPOINTS,
            project_id=self.project_id,
            environment=api_utils.get_environment_string(region),
            security_policy=policy_name,
        )
        policy_data = json.dumps(policy_json)

        response_info, content = self.session.request(url, constants.PATCH, policy_data)
        api_utils.validate_response(response_info, content)

        return parser.build_create_or_update_security_policy(json.loads(content))

    def add_rule_to_security_policy(
        self, policy_name: str, region: str, policy_json: SingleJson
    ) -> datamodels.CreateOrUpdateSecurityPolicy:
        """Add a rule to a security policy.

        Args:
            policy_name (str): The name of the security policy.
            region (str): The region where the security policy is located.
            policy_json (SingleJson): The JSON data representing the rule to add.

        Returns:
            CreateOrUpdateSecurityPolicy: The updated security policy object.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            endpoint_id="add_rule_to_policy",
            endpoints=constants.ENDPOINTS,
            project_id=self.project_id,
            environment=api_utils.get_environment_string(region),
            security_policy=policy_name,
        )
        policy_data = json.dumps(policy_json)

        response_info, content = self.session.request(url, constants.POST, policy_data)
        api_utils.validate_response(response_info, content)

        return parser.build_create_or_update_security_policy(json.loads(content))
