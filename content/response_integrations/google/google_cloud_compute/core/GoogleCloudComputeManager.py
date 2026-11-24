# ============================================================================#
# title           :GoogleCloudComputeManager.py
# description     :This Module contain all Google Cloud Compute operations functionality
# author          :amit.levizky@siemplify.co
# date            :31-05-2021
# python_version  :3.7
# product_version :1.0
# ============================================================================#
from __future__ import annotations

from functools import reduce
import json
import re
from typing import List, Optional, Dict
from urllib.parse import urljoin

# ============================= IMPORTS ===================================== #
import requests
import requests.adapters
from google.auth.exceptions import TransportError, RefreshError
from google.auth.transport.requests import AuthorizedSession, Request

from TIPCommon.exceptions import EmptyMandatoryValues
from TIPCommon.rest.auth import build_credentials_from_sa
from TIPCommon.rest.gcp import (
    get_workload_sa_email,
    retrieve_project_id,
    validate_impersonation,
)
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_empty_string_or_none

from google_cloud_compute.core.GoogleCloudComputeParser import GoogleCloudComputeParser
from google_cloud_compute.core.GoogleCloudComputeConstants import (
    SCOPES,
    INTEGRATION_NAME,
    DEFAULT_MAX_RESULT,
    DEFAULT_ORDER,
    DEFAULT_PAGE_SIZE,
    INVALID_ZONE_ERROR,
    INVALID_LABELS_ERROR,
    NOT_FOUND_RESOURCE_ERROR,
    PROJECT_NOT_FOUND_ERROR,
)
from google_cloud_compute.core import GoogleCloudComputeDatamodels
from google_cloud_compute.core.GoogleCloudComputeExceptions import (
    GoogleCloudAuthenticationError,
    GoogleCloudComputeManagerError,
    GoogleCloudComputeInvalidZone,
    GoogleCloudTransportException,
    GoogleCloudComputeLabelsValidationError,
    GoogleCloudComputeInvalidInstanceID,
    GoogleCloudComputeValidationError,
)
from google_cloud_compute.core.GoogleCloudComputeUtils import parse_string_to_dict

# ============================= CLASSES ===================================== #

ENDPOINTS = {
    "ping": "compute/v1/projects/{project_id}/zones?maxResults=1",
    "list_instances": "compute/v1/projects/{project_id}/zones/{zone}/instances",
    "list_instances_aggregated": (
        "compute/v1/projects/{project_id}/aggregated/instances"
    ),
    "get_instance": "compute/v1/{resource_path}",
    "delete_instance": "compute/v1/{resource_path}",
    "start_instance": "compute/v1/{resource_path}/start",
    "stop_instance": "compute/v1/{resource_path}/stop",
    "add_labels_to_instance": "compute/v1/{resource_path}/setLabels",
    "set_instance_tags": "compute/v1/{resource_path}/setTags",
    "get_instance_iam_policy": "compute/v1/{resource_path}/getIamPolicy",
    "set_instance_iam_policy": "compute/v1/{resource_path}/setIamPolicy",
    "delete_instance_access_config": "compute/v1/{resource_path}/deleteAccessConfig",
    "patch_instance_network_interface": (
        "compute/v1/{resource_path}/updateNetworkInterface"
    ),
    "firewall_rule": "compute/v1/{resource_path}",
    "execute_patch_job": "v1/projects/{project_id}/patchJobs:execute",
    "get_patch_job": "v1/{resource_name}",
}


class GoogleCloudComputeManager:
    """
    Google Cloud Compute Manager
    """

    def __init__(
        self,
        api_root: str | None = None,
        os_config_api_root: str | None = None,
        account_type: str | None = None,
        project_id: str | None = None,
        private_key_id: str | None = None,
        private_key: str | None = None,
        client_email: str | None = None,
        client_id: str | None = None,
        auth_uri: str | None = None,
        token_uri: str | None = None,
        auth_provider_x509_url: str | None = None,
        client_x509_cert_url: str | None = None,
        service_account_json: str | None = None,
        workload_identity_email: str | None = None,
        force_test_connectivity: bool = False,
        verify_ssl: bool = True,
    ):

        if not is_empty_string_or_none(service_account_json):
            service_account_json = parse_string_to_dict(service_account_json)

        try:
            credentials = build_credentials_from_sa(
                user_service_account=service_account_json,
                target_principal=workload_identity_email,
                scopes=SCOPES,
                verify_ssl=verify_ssl,
                account_type=account_type,
                project_id=project_id,
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
            raise GoogleCloudComputeValidationError(
                "Please fill either 'Service Account Json File Content', "
                "'Workload Identity Email' or all other parameters"
            ) from e
        except RefreshError as e:
            workload_sa_email = get_workload_sa_email("Unknown Principal")
            raise GoogleCloudAuthenticationError(
                "Impersonation is not allowed for the provided service "
                f"account {workload_identity_email}. "
                'Please add the "Service Account Token Creator" role to the '
                f"service account: {workload_sa_email}"
            ) from e

        if is_empty_string_or_none(project_id):
            project_id = retrieve_project_id(
                service_account_json, workload_identity_email
            )

        self.api_root = api_root if api_root.endswith("/") else f"{api_root}/"
        self.os_config_api_root = (
            os_config_api_root + "/"
            if os_config_api_root and not os_config_api_root.endswith("/")
            else os_config_api_root
        )
        self.parser = GoogleCloudComputeParser()
        self.project_id = project_id
        self.workload_identity_email = workload_identity_email

        self.session = AuthorizedSession(
            credentials, auth_request=self.prepare_auth_request(verify_ssl)
        )
        self.session.verify = verify_ssl

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

    def validate_response(
        self, response: requests.Response, error_msg="An error occurred"
    ):
        """Validate a response.

        Args:
            response: The response
            error_msg: Error message prefix

        Raises:
            ImpersonationUnauthorizedError: if impersonation fails.
            GoogleCloudComputeLabelsValidationError: if invalid labels.
            GoogleCloudComputeInvalidZone: If invalid zone.
            GoogleCloudComputeInvalidInstanceID: If invalid compute instance id.
            GoogleCloudComputeManagerException: if any other unknown HTTPError occurs.
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response_json = response.json()

            except json.JSONDecodeError as e:
                raise GoogleCloudComputeManagerError(
                    f"{error_msg}: {error} {response.content}"
                ) from e

            validate_impersonation(response_json)
            json_err_message = response_json.get("error", {}).get("message", "")

            if response.status_code in (401, 403):
                raise GoogleCloudAuthenticationError(
                    f"Authentication error - {error} "
                    f"{json_err_message or response.content}"
                ) from error

            if INVALID_LABELS_ERROR in json_err_message:
                raise GoogleCloudComputeLabelsValidationError(
                    f"{error_msg}: {json_err_message or response.content}"
                ) from error

            if INVALID_ZONE_ERROR in json_err_message:
                raise GoogleCloudComputeInvalidZone(
                    f"{error_msg}: {json_err_message or response.content}"
                ) from error

            if all(s in json_err_message for s in NOT_FOUND_RESOURCE_ERROR):
                if re.match(PROJECT_NOT_FOUND_ERROR, json_err_message):
                    raise GoogleCloudAuthenticationError(
                        f"Authentication error - {error} "
                        f"{json_err_message or response.content}"
                    ) from error

                raise GoogleCloudComputeInvalidInstanceID(
                    f"{error_msg}: {json_err_message or response.content}"
                ) from error

            raise GoogleCloudComputeManagerError(
                f"{error_msg}: {error} {json_err_message or response.content}"
            ) from error

    def _get_full_url(self, url_key, api_root: str | None = None, **kwargs) -> str:
        """Get full url from url key.

        Args:
            url_id: The key of url
            api_root: The API root
            kwargs: Variables passed for string formatting

        Returns:
            The full url
        """
        return urljoin(api_root or self.api_root, ENDPOINTS[url_key].format(**kwargs))

    def test_connectivity(self) -> None:
        """Test connectivity."""
        request_url = self._get_full_url("ping", **{"project_id": self.project_id})
        response = self.session.get(request_url)
        self.validate_response(response, f"Unable to connect to {INTEGRATION_NAME}")

    def list_instances_aggregated(
        self,
        limit: int = DEFAULT_MAX_RESULT,
        filter_: str | None = None,
        order: str = DEFAULT_ORDER,
    ) -> list[GoogleCloudComputeDatamodels.Instance]:
        """Get list of instances aggregated by all available zones.

        Args:
            limit (int, optional): Max number of instances to be returned.
            filter_ (str, optional): Filter string to filter out instances by.
            order (str, optional): Order string to dictate instances order
                Currently, only sorting by name or creationTimestamp desc is supported.

        Returns:
            list[Instance]: List of instances aggregated by all available zones
        """
        params = {"maxResults": DEFAULT_PAGE_SIZE}

        if order:
            params["orderBy"] = order

        if filter_:
            params["filter"] = filter_

        request_url = self._get_full_url(
            "list_instances_aggregated", project_id=self.project_id
        )
        instances = []

        while len(instances) < limit:
            response = self.session.get(request_url, params=params)
            self.validate_response(
                response, f"Unable to list instances from {INTEGRATION_NAME}"
            )
            response_json = response.json()

            fetched_instances = reduce(
                lambda instances_, zone_instances: instances_ + zone_instances,
                (
                    self.parser.build_instances_objs(zone_payload, "instances")
                    for zone_payload in response_json.get("items", {}).values()
                    if "instances" in zone_payload
                ),
                [],
            )
            instances.extend(fetched_instances)

            params["pageToken"] = response_json.get("nextPageToken")
            if not params.get("pageToken") or not fetched_instances:
                break

        return instances[:limit]

    def list_instances(
        self,
        zone: str,
        limit: int = DEFAULT_MAX_RESULT,
        filter_: str = None,
        order: str = DEFAULT_ORDER,
    ) -> List[GoogleCloudComputeDatamodels.Instance]:
        """
        List Google Cloud Compute instances based on the specified search criteria.
        :param zone: {str} instance zone name to search for instances in.
        :param limit: {int} how many instances to return.
        :param filter_: {str} Filter the instances according to attributes. for example:
        :param order: {int} Sorts list results by a certain order.
        (status = \"RUNNING\") (name = \"instance-1\")
        :return: {List[datamodels.instances]} List of Instances model
        """
        params = {"maxResults": DEFAULT_PAGE_SIZE}

        if order and not filter_:
            params["orderBy"] = order

        if filter_:
            params["filter"] = filter_
            params["pageToken"] = None

        request_url = self._get_full_url(
            "list_instances", **{"project_id": self.project_id, "zone": zone}
        )
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response, f"Unable to list instances from {INTEGRATION_NAME}"
        )

        instances = []
        while response.json().get("items"):
            instances.extend(self.parser.build_instances_objs(response.json()))

            params["pageToken"] = response.json().get("nextPageToken")

            if not params["pageToken"] or len(instances) >= limit:
                break

            response = self.session.get(request_url, params=params)
            self.validate_response(
                response, f"Unable to list instances from {INTEGRATION_NAME}"
            )

        return instances[:limit]

    def get_instance(self, resource_path: str) -> GoogleCloudComputeDatamodels.Instance:
        """Get specific instance data.

        Args:
            resource_path: {str} The full resource name of an instance.

        Returns:
            {datamodels.Instance} Instance data model
        """
        try:
            request_url = self._get_full_url(
                "get_instance", resource_path=resource_path
            )
            response = self.session.get(request_url)
            self.validate_response(
                response,
                f"Unable to get resource: {resource_path} from {INTEGRATION_NAME}",
            )
            return self.parser.build_instance_obj(response.json())

        except TransportError as error:
            raise GoogleCloudTransportException(error)

    def get_instance_iam_policy(
        self, resource_path: str
    ) -> GoogleCloudComputeDatamodels.InstanceIAMPolicy:
        """Gets the access control policy for the instance.

        Note:
            May be empty if no such policy or instance exists.

        Args:
            resource_path: {str} Full resource path of an Instance

        Returns:
            {InstanceIAMPolicy} Instance IAM Policy data model
        """
        request_url = self._get_full_url(
            "get_instance_iam_policy", resource_path=resource_path
        )
        response = self.session.get(request_url)
        self.validate_response(
            response,
            error_msg=f"Failed to get IAM policy for instance: {resource_path}",
        )
        return self.parser.build_instance_iam_policy_obj(response.json())

    def set_instance_iam_policy(
        self, resource_path: str, policy_json: dict
    ) -> GoogleCloudComputeDatamodels.InstanceIAMPolicy:
        """Sets the access control policy for the instance.

        Args:
            resource_path: {str} Full resource path of an Instance
            policy_json: {dict} Policy JSON to set

        Returns:
            {InstanceIAMPolicy} Instance IAM Policy data model
        """
        request_url = self._get_full_url(
            "set_instance_iam_policy", resource_path=resource_path
        )
        response = self.session.post(request_url, json=policy_json)
        self.validate_response(
            response,
            error_msg=f"Failed to set IAM policy for instance: {resource_path}",
        )
        return self.parser.build_instance_iam_policy_obj(response.json())

    def set_labels_to_instance(
        self,
        resource_path: str,
        labels: Optional[Dict[str, str]],
        label_fingerprint: str,
    ):
        """Set labels on an instance.

        Args:
            resource_path: {str} The full resource path of the instance.
            labels: [{str}] List of labels to set
            label_fingerprint: {str} Fingerprint of the previous set of labels for this
                instance, used to prevent conflicts. A base64-encoded string.

        Returns:
            {OperationResource} Operation resource data model
        """
        request_url = self._get_full_url(
            "add_labels_to_instance", resource_path=resource_path
        )
        payload = {"labels": labels, "labelFingerprint": label_fingerprint}
        response = self.session.post(request_url, json=payload)
        self.validate_response(
            response, error_msg=f"Failed to set labels for instance: {resource_path}"
        )
        return self.parser.build_operation_resource_obj(response.json())

    def set_instance_tags(
        self,
        resource_path: str,
        tags: List[str],
        fingerprint: str,
    ):
        """Set labels on an instance.

        Args:
            resource_path: {str} The full resource path of the instance.
            tags: [{str}] List of tags to set
            fingerprint: {str} Fingerprint of the previous set of tags for this
                instance, used to prevent conflicts. A base64-encoded string.

        Returns:
            {OperationResource} Operation resource data model
        """
        request_url = self._get_full_url(
            "set_instance_tags", resource_path=resource_path
        )
        payload = {"items": tags, "fingerprint": fingerprint}
        response = self.session.post(request_url, json=payload)
        self.validate_response(
            response, error_msg=f"Failed to set tags for instance: {resource_path}"
        )
        return self.parser.build_operation_resource_obj(response.json())

    def start_instance(self, resource_path: str) -> Dict:
        """Start a previously stopped Google Cloud Compute Instance.

        Note:
            it can take a few minutes for the instance to enter the  running status.

        Args:
            resource_path: {str} Full resource path of an Instance.

        Returns:
            {Dict} The results of the operation
        """
        request_url = self._get_full_url("start_instance", resource_path=resource_path)
        response = self.session.post(request_url)
        self.validate_response(
            response, error_msg=f"Failed to start instance: {resource_path}"
        )
        return response.json()

    def stop_instance(self, resource_path: str) -> Dict:
        """Stops a running instance.

        Shutting it down cleanly, and allows you to restart the instance at a later
        time. Stopped instances do not incur VM usage charges while they are stopped.
        However, resources that the VM is using, such as persistent disks and static
        IP addresses, will continue to be charged until they are deleted.

        Args:
            resource_path: {str} Full resource path of an Instance.

        Returns:
            {Dict} The results of the operation
        """
        request_url = self._get_full_url("stop_instance", resource_path=resource_path)
        response = self.session.post(request_url)
        self.validate_response(
            response, error_msg=f"Failed to stop instance: {resource_path}"
        )
        return response.json()

    def delete_instance(self, resource_path: str) -> SingleJson:
        """Deletes the specified Instance resource.

        Args:
            resource_path: {str} Name of the instance resource to delete.

        Returns:
            {Dict} The results of the operation
        """
        request_url = self._get_full_url("delete_instance", resource_path=resource_path)
        response = self.session.delete(request_url)
        self.validate_response(
            response, error_msg=f"Failed to delete instance: {resource_path}"
        )
        return response.json()

    def delete_access_config(
        self, resource_path: str, network_interface: str, access_config: str
    ) -> GoogleCloudComputeDatamodels.OperationResource:
        """Delete the specified access config for instance resource.

        Args:
            resource_path: {str} Name of the instance resource
            network_interface: {str} Name of the network interface that has
            access config
            access_config: {str} Name of the access config to delete

        Returns:
            {OperationResource} An object representing the operation
        """
        params = {"networkInterface": network_interface, "accessConfig": access_config}
        request_url = self._get_full_url(
            "delete_instance_access_config", resource_path=resource_path
        )

        response = self.session.post(request_url, params=params)
        self.validate_response(
            response,
            error_msg=(
                f"Failed to delete access config {access_config} "
                f"in instance {resource_path}"
            ),
        )
        return self.parser.build_operation_resource_obj(response.json())

    def patch_network_interface(
        self,
        resource_path: str,
        network_interface: str,
        fingerprint: str,
        stack_type: str,
    ) -> GoogleCloudComputeDatamodels.OperationResource:
        """Patch existing networkInterface.

        Args:
            resource_path: {str} Name of the instance resource
            network_interface: {str} Network Interface data model
            fingerprint: {str} Resource fingerprint
            stack_type: {str} Stack type to update

        Returns:
            {OperationResource} An object representing the operation
        """
        params = {"networkInterface": network_interface}
        request_body = {"fingerprint": fingerprint, "stackType": stack_type}
        request_url = self._get_full_url(
            "patch_instance_network_interface", resource_path=resource_path
        )

        response = self.session.patch(request_url, params=params, json=request_body)
        self.validate_response(
            response,
            error_msg=(
                f"Failed to patch network interface {network_interface} "
                f"in instance {resource_path}"
            ),
        )
        return self.parser.build_operation_resource_obj(response.json())

    def get_firewall_rule(
        self, resource_path: str
    ) -> GoogleCloudComputeDatamodels.FirewallRule:
        """Get existing firewall rule.

        Args:
            resource_path: {str} Name of the instance resource

        Returns:
            {datamodels.FirewallRule} firewall rule data model.
        """
        request_url = self._get_full_url("firewall_rule", resource_path=resource_path)

        response = self.session.get(request_url)
        self.validate_response(
            response, error_msg=(f"Failed to get firewall rule {resource_path} ")
        )
        return GoogleCloudComputeDatamodels.FirewallRule.from_dict(response.json())

    def patch_firewall_rule(
        self, resource_path: str, firewall: GoogleCloudComputeDatamodels.FirewallRule
    ) -> GoogleCloudComputeDatamodels.OperationResource:
        """Patch existing firewall rule.

        Args:
            resource_path: {str} Name of the instance resource
            firewall: {FirewallRule} Firewall rule object

        Returns:
            {OperationResource} An object representing the operation
        """
        request_url = self._get_full_url("firewall_rule", resource_path=resource_path)

        response = self.session.patch(request_url, json=firewall.as_dict())
        self.validate_response(
            response, error_msg=(f"Failed to patch firewall rule {resource_path} ")
        )
        return self.parser.build_operation_resource_obj(response.json())

    def get_operation(
        self, self_link: str
    ) -> GoogleCloudComputeDatamodels.OperationResource:
        """Get operation by its self link.

        Args:
            self_link: {str} full link of the operation

        Returns:
            {OperationResource} An object representing the operation
        """
        response = self.session.get(self_link)
        self.validate_response(
            response, error_msg=(f"Failed to fetch operation by self link {self_link} ")
        )
        return self.parser.build_operation_resource_obj(response.json())

    def execute_patch_job(
            self,
            patch_job: GoogleCloudComputeDatamodels.PatchJob
    ) -> GoogleCloudComputeDatamodels.PatchJob:
        """Start execution of a patch job.

        Args:
            patch_job: Patch Job data model to be created

        Returns:
            Patch Job data model
        """
        request_url = self._get_full_url(
            "execute_patch_job",
            api_root=self.os_config_api_root,
            project_id=self.project_id
        )

        response = self.session.post(request_url, json=patch_job.as_dict())
        self.validate_response(
            response, error_msg=(
                f"Failed to execute patch job {patch_job.display_name}."
            )
        )
        return self.parser.build_patch_job(response.json())

    def get_patch_job(
            self,
            patch_job_name: str
    ) -> GoogleCloudComputeDatamodels.PatchJob:
        """Start execution of a patch job.

        Args:
            patch_job_name: Patch Job name

        Returns:
            Patch Job data model
        """
        request_url = self._get_full_url(
            "get_patch_job",
            api_root=self.os_config_api_root,
            resource_name=patch_job_name,
        )

        response = self.session.get(request_url)
        self.validate_response(
            response, error_msg=(
                f"Failed to fetch patch job {patch_job_name}."
            )
        )
        return self.parser.build_patch_job(response.json())
