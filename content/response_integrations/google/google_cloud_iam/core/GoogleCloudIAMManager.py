# ============================================================================#
# title           :GoogleCloudIAMManager.py
# description     :This Module contain all Google Cloud IAM operations functionality
# author          :gabriel.munits@siemplify.co
# date            :23-06-2021
# python_version  :3.7
# product_version :1.0
# ============================================================================#
from __future__ import annotations

from urllib.parse import urljoin

import requests
import requests.adapters
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import AuthorizedSession, Request

from TIPCommon.types import ChronicleSOAR
from TIPCommon.exceptions import ImpersonationUnauthorizedError, EmptyMandatoryValues
from TIPCommon.rest.auth import build_credentials_from_sa
from TIPCommon.rest.gcp import (
    get_workload_sa_email,
    retrieve_project_id,
    validate_impersonation,
)

from google_cloud_iam.core.consts import (
    DEFAULT_SA_KEY_TYPE,
    INTEGRATION_DISPLAY_NAME,
    SCOPES,
    INVALID_JSON_PAYLOAD,
    INVALID_ARGUMENT,
    MAX_PAGE_SIZE,
    DEFAULT_PAGE_SIZE,
    ALREADY_EXISTS,
    NON_EXISTING_ROLE_NAME,
    NOT_FOUND_STATUS_CODE,
    ROLE_ALREADY_DELETED,
    MAX_PAGE_SIZE_SERVICE_ACCOUNTS,
    INVALID_ROLE_ID,
)
from google_cloud_iam.core.datamodels import Policy, Role, ServiceAccount, ServiceAccountKey
from google_cloud_iam.core.GoogleCloudIAMParser import GoogleCloudIAMParser
from google_cloud_iam.core.exceptions import (
    GoogleCloudIAMManagerError,
    GoogleCloudIAMPolicyJSONError,
    GoogleCloudIAMRoleExistsError,
    GoogleCloudIAMRoleJSONError,
    GoogleCloudIAMRoleMissingError,
    GoogleCloudIAMServiceAccountExistsError,
    GoogleCloudIAMRoleIDInvalidError,
    GoogleCloudIAMValidationError,
    GoogleCloudIAMServiceAccountNotFoundError,
)
from google_cloud_iam.core.utils import parse_string_to_dict


# ============================= CONSTS ===================================== #

ENDPOINTS = {
    # Roles endpoints
    "list-roles": "v1/roles",
    "list-resource-roles": "v1/{resource_name}/roles",
    "ping": "v1/{resource_name}/roles",
    "create-resource-role": "v1/{resource_name}/roles",
    "delete-resource-role": "v1/{resource_name}/roles/{role_id}",
    "get-resource-role": "v1/{resource_name}/roles/{role_id}",
    # SA endpoints
    "get-service-account-iam-policy": (
        "v1/projects/{project_id}/serviceAccounts/{resource}:getIamPolicy"
    ),
    "set-service-account-iam-policy": (
        "v1/projects/{project_id}/serviceAccounts/{resource}:setIamPolicy"
    ),
    "disable-service-account": (
        "v1/projects/{project_id}/serviceAccounts/{resource}:disable"
    ),
    "enable-service-account": (
        "v1/projects/{project_id}/serviceAccounts/{resource}:enable"
    ),
    "get-service-account": "v1/projects/{project_id}/serviceAccounts/{resource}",
    "delete-service-account": "v1/projects/{project_id}/serviceAccounts/{resource}",
    "list-service-accounts": "v1/projects/{project_id}/serviceAccounts",
    "create-service-account": "v1/projects/{project_id}/serviceAccounts",
    "get-service-account-keys": (
        "v1/projects/{project_id}/serviceAccounts/{resource}/keys"
    ),
    "create-service-account-key": (
        "v1/projects/{project_id}/serviceAccounts/{resource}/keys"
    ),
    "delete-service-account-key": "v1/{key_name}",
}


# ============================= CLASSES ===================================== #


class GoogleCloudIAMManager:
    """
    Google Cloud IAM Manager
    """

    def __init__(
        self,
        siemplify: ChronicleSOAR = None,
        api_root: str | None = None,
        account_type: str | None = None,
        project_id: str | None = None,
        quota_project_id: str | None = None,
        private_key_id: str | None = None,
        private_key: str | None = None,
        client_email: str | None = None,
        client_id: str | None = None,
        auth_uri: str | None = None,
        token_uri: str | None = None,
        auth_provider_x509_url: str | None = None,
        client_x509_cert_url: str | None = None,
        force_test_connectivity: bool = False,
        organization_id: str = None,
        service_account_json: str = None,
        verify_ssl: bool = True,
        workload_identity_email: str = None,
    ):
        if service_account_json is not None:
            service_account_json = parse_string_to_dict(service_account_json)

        try:
            credentials = build_credentials_from_sa(
                user_service_account=service_account_json,
                target_principal=workload_identity_email,
                scopes=SCOPES,
                verify_ssl=verify_ssl,
                account_type=account_type,
                project_id=project_id,
                quota_project_id=quota_project_id,
                private_key_id=private_key_id,
                private_key=private_key,
                client_email=client_email,
                client_id=client_id,
                auth_uri=auth_uri,
                token_uri=token_uri,
                auth_provider_x509_url=auth_provider_x509_url,
                client_x509_cert_url=client_x509_cert_url,
            )
        except EmptyMandatoryValues as e:
            raise GoogleCloudIAMValidationError(
                "Please fill either 'Service Account Json File Content', "
                "'Workload Identity Email' or all other parameters"
            ) from e
        except RefreshError as e:
            workload_sa = get_workload_sa_email("Unknown Principal")
            raise GoogleCloudIAMManagerError(
                "Impersonation is not allowed for the provided service "
                f"account {workload_identity_email}. "
                'Please add the "Service Account Token Creator" role to the '
                f"service account: {workload_sa}"
            ) from e

        fallback_project_id = retrieve_project_id(
            service_account_json, workload_identity_email
        )
        self.project_id = project_id or (organization_id and "-") or fallback_project_id
        self.resource_name = (
            f"projects/{project_id}"
            if project_id
            else (
                f"organizations/{organization_id}"
                if organization_id
                else f"projects/{fallback_project_id}"
            )
        )

        self.workload_identity_email = workload_identity_email
        self._session = AuthorizedSession(
            credentials, auth_request=self.prepare_auth_request(verify_ssl=verify_ssl)
        )
        self._session.verify = verify_ssl
        self._parser = GoogleCloudIAMParser()
        self.siemplify = siemplify
        self.api_root = api_root if api_root.endswith("/") else f"{api_root}/"

        if force_test_connectivity:
            self.test_connectivity()

    @staticmethod
    def prepare_auth_request(verify_ssl: bool = True):
        """
        Prepare an authenticated request.

        Note: This method is a duplicate of the same method in the GoogleCloudComputeManager class. The only change is
        that created session is using verify_ssl parameter to allow self-signed certificates.
        """
        auth_request_session = requests.Session()
        auth_request_session.verify = verify_ssl

        # Using an adapter to make HTTP requests robust to network errors.
        # This adapter retries HTTP requests when network errors occur
        # and the requests seems safely retryable.
        retry_adapter = requests.adapters.HTTPAdapter(max_retries=3)
        auth_request_session.mount("https://", retry_adapter)

        # Do not pass `self` as the session here, as it can lead to
        # infinite recursion.
        return Request(auth_request_session)

    def _get_full_url(self, url_key: str, **kwargs) -> str:
        """
        Get full url from url key.
        :param url_id: {str} The key of url
        :param kwargs: {dict} Key value arguments passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_key].format(**kwargs))

    def validate_response(
        self, response: requests.Response, error_msg: str = "An error occurred"
    ):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} Default message to display on error
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response_json = response.json()
                validate_impersonation(response_json)

                json_error_msg = response_json.get("error", {}).get(
                    "message", response.text
                )

                raise GoogleCloudIAMManagerError(
                    f"{error_msg}: {error} {json_error_msg}"
                )

            except (GoogleCloudIAMManagerError, ImpersonationUnauthorizedError):
                raise

            except Exception as e:
                raise GoogleCloudIAMManagerError(
                    f"{error_msg}: {error} {response.text}"
                ) from e

    def log_info(self, message: str) -> None:
        """Log message on info level if there is a logger available."""
        if self.siemplify is None:
            return

        self.siemplify.LOGGER.info(message)

    def test_connectivity(self):
        """
        Test connectivity with Google Cloud IAM
            raise Exception if failed to test connectivity
        """
        request_url = self._get_full_url("ping", resource_name=self.resource_name)
        response = self._session.get(request_url, params={"pageSize": 1})
        self.validate_response(
            response,
            error_msg=f"Failed to test connectivity with {INTEGRATION_DISPLAY_NAME}",
        )

    def get_service_account_iam_policy(
        self, service_account_email: str, service_account_project: str | None = None
    ) -> Policy:
        """Gets the IAM Policy that is attached to a Service Account.

        Args:
            service_account_email: {str} Service account email
            service_account_project: {str} Project ID where SA is located

        Returns:
            {IAMPolicy} IAM Policy data model
        """
        request_url = self._get_full_url(
            "get-service-account-iam-policy",
            project_id=service_account_project or self.project_id,
            resource=service_account_email,
        )
        response = self._session.post(request_url)
        self.validate_response(
            response,
            error_msg=(
                "Failed to get service account IAM policy "
                f"for account: {service_account_email}"
            ),
        )
        return self._parser.build_service_account_iam_policy(response.json())

    def set_service_account_iam_policy(
        self,
        service_account_email: str,
        policy_json: dict,
        service_account_project: str | None = None,
    ) -> Policy:
        """Sets an IAM policy that is attached to a ServiceAccount.

        Args:
            service_account_email: {str} Service account email
            policy_json: {dict} The complete policy to be applied to the service
                account. The size of the policy is limited to a few 10s of KB.
            service_account_project: {str} Project ID where SA is located

        Returns:
            {IAMPolicy} IAM Policy data model of the updated policy
        """
        request_url = self._get_full_url(
            "set-service-account-iam-policy",
            project_id=service_account_project or self.project_id,
            resource=service_account_email,
        )
        response = self._session.post(request_url, json={"policy": policy_json})
        error_msg = f"Failed to set IAM policy for account: {service_account_email}"
        try:
            self.validate_response(response, error_msg)
        except Exception as error:
            if INVALID_JSON_PAYLOAD in response.json().get("error", {}).get(
                "message", response.text
            ) or INVALID_ARGUMENT in response.json().get("error", {}).get("status", ""):
                raise GoogleCloudIAMPolicyJSONError(
                    f"{error_msg}: {error} {response.json().get('error', {}).get('message', response.text)}"
                )
            raise
        return self._parser.build_service_account_iam_policy(response.json())

    def disable_service_account(
        self, service_account_email: str, service_account_project: str | None = None
    ) -> None:
        """Disables a Service Account immediately.

        Args:
            service_account_email: {str} Service Account email
            service_account_project: {str} Project ID where SA is located
        """
        request_url = self._get_full_url(
            "disable-service-account",
            project_id=service_account_project or self.project_id,
            resource=service_account_email,
        )
        response = self._session.post(request_url)
        self.validate_response(
            response, error_msg=f"Failed to disable account: {service_account_email}"
        )

    def enable_service_account(
        self, service_account_email: str, service_account_project: str | None = None
    ) -> None:
        """Enables a Service Account that was disabled.

        Args:
            service_account_email: {str} Service Account email
            service_account_project: {str} Project ID where SA is located
        """
        request_url = self._get_full_url(
            "enable-service-account",
            project_id=service_account_project or self.project_id,
            resource=service_account_email,
        )
        response = self._session.post(request_url)
        self.validate_response(
            response, error_msg=f"Failed to enable account: {service_account_email}"
        )

    def delete_service_account(
        self, service_account_email: str, service_account_project: str | None = None
    ) -> None:
        """Deletes a Service Account.

        Args:
            service_account_email: {str} Service Account email
            service_account_project: {str} Project ID where SA is located
        """
        request_url = self._get_full_url(
            "delete-service-account",
            project_id=service_account_project or self.project_id,
            resource=service_account_email,
        )
        response = self._session.delete(request_url)
        self.validate_response(
            response,
            error_msg=f"Failed to delete service account: {service_account_email}",
        )

    def list_roles(
        self, show_deleted: bool, role_view: str, max_results: int
    ) -> list[Role]:
        """List every predefined Role that IAM supports.

        Also lists every custom role that is defined for an organization or project.

        Args:
            show_deleted: {bool} True if to include roles that have been deleted
            role_view: {str} View of roles. Can be BASIC or FULL.
            max_results: {int} Max roles to return

        Returns:
            {[Role]} List of Role data models
        """
        request_url = self._get_full_url("list-roles")
        response = self._session.get(
            request_url,
            params={
                "pageSize": min(max_results, MAX_PAGE_SIZE),
                "showDeleted": show_deleted,
                "view": role_view,
            },
        )
        self.validate_response(response, error_msg="Failed to list roles")
        roles = self._parser.build_role_obj_list(response.json())
        self.log_info(f"Fetched total of {len(roles)} roles")

        while len(roles) < max_results:
            # Fetch more roles if available
            next_page_token = self._parser.get_next_page_token_from_listed_roles(
                response.json()
            )
            if not next_page_token:
                break

            self.log_info("Fetching more roles..")
            response = self._session.get(
                request_url,
                params={
                    "pageToken": next_page_token,
                    "pageSize": DEFAULT_PAGE_SIZE,
                    "showDeleted": show_deleted,
                    "view": role_view,
                },
            )
            self.validate_response(response, error_msg="Failed to list more roles")
            more_fetched_roles = self._parser.build_role_obj_list(response.json())
            self.log_info(f"Fetched more {len(more_fetched_roles)} roles")
            roles.extend(more_fetched_roles)

        return roles[:max_results] if max_results else roles

    def list_resource_roles(
        self, show_deleted: bool, role_view: str, max_results: int
    ) -> list[Role]:
        """Lists every custom role that is defined for an organization or project.

        Args:
            show_deleted: {bool} True if to include roles that have been deleted
            role_view: {str} View of roles. Can be BASIC or FULL.
            max_results: {int} Max roles to return

        Returns:
            {[Role]} List of Role data models
        """
        request_url = self._get_full_url(
            "list-resource-roles", resource_name=self.resource_name
        )
        response = self._session.get(
            request_url,
            params={
                "pageSize": min(max_results, MAX_PAGE_SIZE),
                "showDeleted": show_deleted,
                "view": role_view,
            },
        )
        self.validate_response(response, error_msg="Failed to list roles")
        roles = self._parser.build_role_obj_list(response.json())
        self.log_info(f"Fetched total of {len(roles)} roles")

        while len(roles) < max_results:
            # Fetch more roles if available
            next_page_token = self._parser.get_next_page_token_from_listed_roles(
                response.json()
            )
            if not next_page_token:
                break

            self.log_info("Fetching more roles..")
            response = self._session.get(
                request_url,
                params={
                    "pageToken": next_page_token,
                    "pageSize": DEFAULT_PAGE_SIZE,
                    "showDeleted": show_deleted,
                    "view": role_view,
                },
            )
            self.validate_response(response, error_msg="Failed to list more roles")
            more_fetched_roles = self._parser.build_role_obj_list(response.json())
            self.log_info(f"Fetched more {len(more_fetched_roles)} roles")
            roles.extend(more_fetched_roles)

        return roles[:max_results] if max_results else roles

    def create_resource_role(self, role_id: str, role_definition_json: dict) -> Role:
        """Creates a new custom Role.

        Args:
            role_id: {str} The role ID to use for this role
            role_definition_json: {dict} Role resource to create

        Returns:
            {Role} Created Role data model
        """
        request_url = self._get_full_url(
            "create-resource-role", resource_name=self.resource_name
        )
        response = self._session.post(
            request_url, json={"roleId": role_id, "role": role_definition_json}
        )
        try:
            self.validate_response(
                response, error_msg=f"Failed to create role with id: {role_id}"
            )
        except Exception as error:
            if all(
                key in response.json().get("error", {}).get("message", response.text)
                for key in INVALID_ROLE_ID
            ):
                raise GoogleCloudIAMRoleIDInvalidError(
                    response.json().get("error", {}).get("message", response.text)
                )
            if INVALID_ARGUMENT in response.json().get("error", {}).get(
                "status", ""
            ) or INVALID_JSON_PAYLOAD in response.json().get("error", {}).get(
                "message", response.text
            ):
                raise GoogleCloudIAMRoleJSONError(error)
            if ALREADY_EXISTS in response.json().get("error", {}).get("status", ""):
                raise GoogleCloudIAMRoleExistsError(error)
            raise

        return self._parser.build_role_obj(response.json())

    def get_resource_role(self, role_id: str) -> Role:
        """Gets a definition of a Role.

        Args:
            role_id: {str} Role id

        Returns:
            {Role} Role data model
        """
        request_url = self._get_full_url(
            "get-resource-role", resource_name=self.resource_name, role_id=role_id
        )
        response = self._session.get(request_url)

        try:
            self.validate_response(
                response, error_msg=f"Failed to get role with id: {role_id}"
            )
        except Exception as error:
            if any(
                key in response.json().get("error", {}).get("message", response.text)
                for key in NON_EXISTING_ROLE_NAME
            ) or INVALID_ARGUMENT in response.json().get("error", {}).get("status", ""):
                raise GoogleCloudIAMRoleMissingError(error)
            raise
        return self._parser.build_role_obj(response.json())

    def delete_resource_role(self, role_id: str, etag: str) -> Role:
        """Deletes a custom Role.

        Args:
            role_id: {str} Role id
            etag: {str} etag of the Role

        Returns:
            {Role} Role data model
        """
        request_url = self._get_full_url(
            "delete-resource-role", resource_name=self.resource_name, role_id=role_id
        )
        response = self._session.delete(request_url, params={"etag": etag})

        try:
            self.validate_response(
                response, error_msg=f"Failed to delete role with id: {role_id}"
            )
        except GoogleCloudIAMManagerError:
            # Ignore exception if role was already deleted
            if not (
                any(
                    key
                    in (response.json().get("error", {}).get("message", response.text))
                    for key in ROLE_ALREADY_DELETED
                )
            ):
                raise

            self.log_info("Role {role_id} was already deleted")

        return self._parser.build_role_obj(response.json())

    def get_service_account(
        self, sa_identifier: str, sa_project: str | None = None
    ) -> ServiceAccount:
        """Get a service account by either ID or email address.

        Args:
            sa_identifier: The service account ID or email
            sa_project: The project ID where SA is located

        Returns:
            A service account data model
        """
        request_url = self._get_full_url(
            "get-service-account",
            project_id=sa_project or self.project_id,
            resource=sa_identifier,
        )
        response = self._session.get(request_url)
        self.validate_response(response, error_msg="Failed to get service account")
        return self._parser.build_service_account_obj(
            response.json(), project_id=sa_project or self.project_id
        )

    def list_service_accounts(self, max_results: int | None = None):
        """
        Lists evey Service Account that belongs to a specific project.
        :param max_results: {int} Max service accounts to return. If not provided, all service accounts will be returned.
        :return: {[ServiceAccount]} List of Service Account data models
        """
        request_url = self._get_full_url(
            "list-service-accounts", project_id=self.project_id
        )
        response = self._session.get(
            request_url,
            params={
                "pageSize": (
                    min(max_results, MAX_PAGE_SIZE_SERVICE_ACCOUNTS)
                    if max_results is not None
                    else MAX_PAGE_SIZE_SERVICE_ACCOUNTS
                )
            },
        )
        self.validate_response(response, error_msg="Failed to list service accounts")
        service_accounts = self._parser.build_service_account_obj_list(
            response.json(), project_id=self.project_id
        )
        self.log_info(f"Fetched total of {len(service_accounts)} service accounts")

        while (max_results is None) or len(service_accounts) < max_results:
            # Fetch more roles if available
            next_page_token = (
                self._parser.get_next_page_token_from_listed_service_accounts(
                    response.json()
                )
            )
            if not next_page_token:
                break

            self.log_info("Fetching more service accounts..")
            response = self._session.get(
                request_url,
                params={
                    "pageToken": next_page_token,
                    "pageSize": MAX_PAGE_SIZE_SERVICE_ACCOUNTS,
                },
            )
            self.validate_response(
                response, error_msg="Failed to list more service accounts"
            )
            more_fetched_service_accounts = self._parser.build_service_account_obj_list(
                response.json(), project_id=self.project_id
            )
            self.log_info(
                f"Fetched more {len(more_fetched_service_accounts)} service accounts"
            )
            service_accounts.extend(more_fetched_service_accounts)

        return (
            service_accounts[:max_results]
            if max_results is not None
            else service_accounts
        )

    def create_service_account(
        self,
        account_id: str,
        display_name: str | None = None,
        description: str | None = None,
    ) -> ServiceAccount:
        """Creates a Service Account.

        Args:
            account_id: {str} The account id that is used to generate the service
                account email address and a stable unique id.
            display_name: {str} Human-readable name for the service account.
            description: {str} Human-readable description of the service account.

        Returns:
            {ServiceAccount} Service Account data model
        """
        request_url = self._get_full_url(
            "create-service-account", project_id=self.project_id
        )
        payload = {"accountId": account_id, "serviceAccount": {}}
        if display_name:
            payload["serviceAccount"].update({"displayName": display_name})
        if description:
            payload["serviceAccount"].update({"description": description})

        response = self._session.post(
            request_url, json={k: v for k, v in payload.items() if v}
        )

        try:
            self.validate_response(
                response,
                error_msg=f"Failed to create service account with account id: {account_id}",
            )
        except Exception as error:
            if ALREADY_EXISTS in response.json().get("error", {}).get("status", ""):
                raise GoogleCloudIAMServiceAccountExistsError(error)
            raise

        return self._parser.build_service_account_obj(
            response.json(), project_id=self.project_id
        )

    def get_service_account_keys(
        self,
        sa_identifier: str,
        sa_project: str | None = None,
        key_type: str = DEFAULT_SA_KEY_TYPE,
    ) -> list[ServiceAccountKey]:
        """Get a service account by either ID or email address.

        Args:
            sa_identifier (str): The service account ID or email
            sa_project (str): The project ID where SA is located
            key_type (str): The type of keys to return. Defaults to "USER_MANAGED".

        Returns:
            list[ServiceAccountKey]: List of Service Account Key data models.
        """
        request_url = self._get_full_url(
            "get-service-account-keys",
            project_id=sa_project or self.project_id,
            resource=sa_identifier,
        )
        params = {"keyTypes": key_type}
        response = self._session.get(request_url, params=params)

        self.validate_response(response, error_msg="Failed to get service account keys")

        return [
            self._parser.build_service_account_key_obj(key)
            for key in response.json().get("keys", [])
        ]

    def create_service_account_key(
        self,
        service_account_email: str,
        project_id: str | None = None,
    ) -> ServiceAccountKey:
        """Creates a new key for a service account.

        Args:
            service_account_email (str): The service account email.
            project_id (str, optional): The project ID where the SA is located.
                Defaults to the manager's project ID.

        Returns:
            ServiceAccountKey: The created service account key data model.
        """
        request_url: str = self._get_full_url(
            "create-service-account-key",
            project_id=project_id or self.project_id,
            resource=service_account_email,
        )

        response: requests.Response = self._session.post(request_url, json={})
        try:
            self.validate_response(
                response,
                error_msg=(
                    f"Failed to create key for service account: {service_account_email}"
                )
            )
        except GoogleCloudIAMManagerError as e:
            if response.status_code == NOT_FOUND_STATUS_CODE:
                raise GoogleCloudIAMServiceAccountNotFoundError(
                    f"Service account '{service_account_email}' not found."
                ) from e
            raise

        return self._parser.build_service_account_key_obj(response.json())

    def delete_service_account_key(self, key_name: str) -> None:
        """Deletes a service account key.

        Args:
            key_name (str): The full resource name of the key to delete.
                        (e.g., projects/{project}/serviceAccounts/{account}/keys/{key})
        """
        request_url: str = self._get_full_url(
            "delete-service-account-key",
            key_name=key_name,
        )
        response: requests.adapters = self._session.delete(request_url)
        self.validate_response(
            response, error_msg=f"Failed to delete service account key: {key_name}"
        )
