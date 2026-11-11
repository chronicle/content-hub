from __future__ import annotations

from urllib.parse import urljoin

import requests
import requests.adapters


from TIPCommon.types import SingleJson

from google_gke.core.GKEConsts import (
    INTEGRATION_DISPLAY_NAME,
    INVALID_ARGUMENT,
    NOT_FOUND,
    PERMISSION_DENIED,
    PROJECT_LOOKUP_ERROR_MESSAGE,
    LOCATION_ERROR_MESSAGE,
    NODE_POOL_ERROR_MESSAGE,
)
from google_gke.core.GKEExceptions import (
    GoogleGKEManagerError,
    GoogleGKEInvalidZoneError,
    GoogleGKEInvalidRequestArgumentError,
    GoogleGKENotFoundError,
    GoogleGKEInvalidNodePoolNameError,
    GoogleGKEProjectLookupError,
    GoogleGKEManagerCriticalError,
)


# ============================= CONSTS ===================================== #

ROOT_PATH = "v1/projects/{project_id}/locations/{zone_name}"
ENDPOINTS = {
    "clusters": "/clusters",
    "cluster": "/clusters/{cluster_name}",
    "operations": "/operations",
    "operation": "/operations/{operation_name}",
    "cluster-node-pools": "/clusters/{cluster_name}/nodePools",
    "cluster-node-pool": "/clusters/{cluster_name}/nodePools/{node_pool_name}",
}

# ============================= CLASSES ===================================== #


class GKEApiManager:
    """
    Google Kubernetes Engine API Manager
    """

    def __init__(
        self,
        api_root: str,
        session: requests.Session,
        project_id: str,
        location_id: str | None = None
    ):
        self.api_root = api_root if api_root.endswith("/") else f"{api_root}/"
        self.project_id = project_id
        self._session = session
        self.location_id = location_id

    def _get_full_url(self, url_key: str, postfix: str = None, **kwargs) -> str:
        """
        Get full url from url key.

        Args:
            url_id: {str} The key of url
            postfix: {str} The postfix to add to the url path
            kwargs: {dict} Key value arguments passed for string formatting

        Returns:
            {str} The full url
        """
        if "project_id" not in kwargs:
            kwargs["project_id"] = self.project_id

        url = (ROOT_PATH + ENDPOINTS[url_key]).format(**kwargs)
        full_url = urljoin(self.api_root, url)
        if postfix is not None:
            full_url += postfix

        return full_url

    @classmethod
    def validate_response(
        cls, response: requests.Response, error_msg: str = "An error occurred"
    ) -> None:
        """Validate API response.

        Args:
            response: {requests.Response} The response to validate
            error_msg: {str} Default message to display on error
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                response_json = response.json()
                error_json = response_json.get("error", {})

                message, status = error_json.get("message"), error_json.get("status")
                if (
                    status == PERMISSION_DENIED
                    and PROJECT_LOOKUP_ERROR_MESSAGE in message
                ):
                    raise GoogleGKEProjectLookupError(
                        f"{error_msg}: {error} {message or response.text}"
                    ) from error
                if status == INVALID_ARGUMENT and all(
                    err in message for err in LOCATION_ERROR_MESSAGE
                ):
                    raise GoogleGKEInvalidZoneError(
                        f"{error_msg}: {error} {message or response.text}"
                    ) from error
                if (
                    (
                        status == INVALID_ARGUMENT
                        and all(err in message for err in NODE_POOL_ERROR_MESSAGE)
                    )
                    or (
                        status == NOT_FOUND
                        and all(
                            err.lower() in message for err in NODE_POOL_ERROR_MESSAGE
                        )
                    )
                    or (
                        status == INVALID_ARGUMENT
                        and "Unable to find node pool" in message
                    )
                ):
                    raise GoogleGKEInvalidNodePoolNameError(
                        f"{error_msg}: {error} {message or response.text}"
                    ) from error
                if status == INVALID_ARGUMENT:
                    raise GoogleGKEInvalidRequestArgumentError(
                        f"{error_msg}: {error} {message or response.text}"
                    ) from error
                if status == NOT_FOUND:
                    raise GoogleGKENotFoundError(
                        f"{error_msg}: {error} {message or response.text}"
                    ) from error
                raise GoogleGKEManagerError(
                    f"{error_msg}: {error} {message or response.text}"
                ) from error
            except (GoogleGKEManagerError, GoogleGKEManagerCriticalError):
                raise
            except Exception as e:
                raise GoogleGKEManagerCriticalError(
                    f"{error_msg}: {error} {response.text}"
                ) from e

    def test_connectivity(self):
        """
        Test connectivity with Google GKE
            raise Exception if failed to test connectivity
        """
        response = self._session.get(
            self._get_full_url(
                "clusters",
                project_id=self.project_id,
                zone_name=self.location_id
            )
        )
        self.validate_response(
            response,
            error_msg=f"Failed to test connectivity with {INTEGRATION_DISPLAY_NAME}",
        )

    def list_clusters(self, zone_name: str) -> list[SingleJson]:
        """Lists all clusters in a project in specified zone or all zones.

        Args:
            zone_name: {str} The name of the Compute Engine zone in which the
                clusters reside, or "-" for all zones.

        Returns:
            List of JSON objects representing the clusters
        """
        response = self._session.get(
            self._get_full_url(
                "clusters", project_id=self.project_id, zone_name=zone_name
            )
        )
        self.validate_response(
            response,
            error_msg=(
                f'Failed to list clusters from zone "{zone_name}" '
                f"in {INTEGRATION_DISPLAY_NAME}"
            ),
        )
        return response.json().get("clusters", [])

    def get_cluster(self, zone_name: str, cluster_name: str) -> SingleJson:
        """Gets the details of a specific cluster.

        Args:
            zone_name: {str} The name of the Google Compute Engine zone in which the
                cluster resides
            cluster_name: {str} The name of the cluster to retrieve

        Returns:
            JSON object containing the details of the cluster
        """
        response = self._session.get(
            self._get_full_url(
                "cluster",
                project_id=self.project_id,
                zone_name=zone_name,
                cluster_name=cluster_name,
            )
        )
        self.validate_response(
            response,
            error_msg=(
                f'Failed to get cluster "{cluster_name}" from zone "{zone_name}" '
                f"in {INTEGRATION_DISPLAY_NAME}"
            ),
        )
        return response.json()

    def update_cluster(
        self, zone_name: str, cluster_name: str, json_body: SingleJson, action: str
    ):
        """Update a cluster using specified action.

        Args:
            zone_name: {str} The name of the Google Compute Engine zone in which the
                cluster resides
            cluster_name: {str} The name of the cluster to update
            json_body: {SingleJson} The body of the update request
            action: {str} Update action to add to path

        Returns:
            JSON object containing the details of the operation
        """
        response = self._session.post(
            self._get_full_url(
                "cluster",
                project_id=self.project_id,
                zone_name=zone_name,
                cluster_name=cluster_name,
                postfix=f":{action}",
            ),
            json=json_body,
        )
        self.validate_response(
            response,
            error_msg=(
                f'Failed to update cluster "{cluster_name}" from '
                f'zone "{zone_name}" in {INTEGRATION_DISPLAY_NAME}'
            ),
        )
        return response.json()

    def list_operations(self, zone_name: str) -> list[SingleJson]:
        """Lists all operations in a project in a specific zone or all zones.

        Args:
            zone_name: {str} The name of the Google Compute Engine zone in which
                the clusters reside, or "-" for all zones.

        Returns:
            List of JSON object representing the operations
        """
        response = self._session.get(
            self._get_full_url(
                "operations", project_id=self.project_id, zone_name=zone_name
            )
        )
        self.validate_response(
            response,
            error_msg=f"Failed to list operations in {INTEGRATION_DISPLAY_NAME}",
        )
        return response.json().get("operations", [])

    def get_operation(self, zone_name: str, operation_name: str):
        """Gets the specified operation.

        Args:
            zone_name: {str} The name of the Google Compute Engine zone
                in which the cluster resides
            operation_name: {str} The server-assigned name of the operation.

        Returns:
            JSON object representing the operation
        """
        response = self._session.get(
            self._get_full_url(
                "operation",
                project_id=self.project_id,
                zone_name=zone_name,
                operation_name=operation_name,
            )
        )
        self.validate_response(
            response,
            error_msg=(
                f'Failed to get operation "{operation_name}"'
                f'from zone "{zone_name}" in {INTEGRATION_DISPLAY_NAME}'
            ),
        )
        return response.json()

    def list_cluster_node_pools(
        self, zone_name: str, cluster_name: str
    ) -> list[SingleJson]:
        """Lists the node pools for a cluster.

        Args:
            zone_name: {str} The name of the Google Compute Engine zone
                in which the cluster resides
            cluster_name: {str} The name of the cluster to list node pools from

        Returns:
            List of JSON objects representing Kubernetes cluster's node pools
        """
        response = self._session.get(
            self._get_full_url(
                "cluster-node-pools",
                project_id=self.project_id,
                zone_name=zone_name,
                cluster_name=cluster_name,
            )
        )
        self.validate_response(
            response,
            error_msg=(
                f'Failed to list cluster\'s "{cluster_name}" node pools from '
                f'zone "{zone_name}" in {INTEGRATION_DISPLAY_NAME}'
            ),
        )

        return response.json().get("nodePools", [])

    def get_cluster_node_pool(
        self, zone_name: str, cluster_name: str, node_pool_name: str
    ) -> SingleJson:
        """Retrieves the requested node pool.

        Args:
            zone_name: {str} The name of the Google Compute Engine zone in which
                the cluster resides
            cluster_name: {str} The name of the cluster to retrieve the node pool from
            node_pool_name: {str} The name of the node pool to retrieve

        Returns:
            JSON object representing Kubernetes cluster node pool
        """
        response = self._session.get(
            self._get_full_url(
                "cluster-node-pool",
                project_id=self.project_id,
                zone_name=zone_name,
                cluster_name=cluster_name,
                node_pool_name=node_pool_name,
            )
        )
        self.validate_response(
            response,
            error_msg=(
                f'Failed to get cluster\'s "{cluster_name}" '
                f'node pool "{node_pool_name}" from zone "{zone_name}" in'
                f" {INTEGRATION_DISPLAY_NAME}"
            ),
        )

        return response.json()

    def update_cluster_node_pool(
        self,
        zone_name: str,
        cluster_name: str,
        node_pool_name: str,
        json_body: SingleJson,
        action: str,
    ) -> SingleJson:
        """Update cluster node pool with given JSON and action.

        Args:
            zone_name: {str} The name of the Google Compute Engine zone
            cluster_name: {str} The name of the cluster to retrieve the node pool from
            node_pool_name: {str} The name of the node pool to update
            json_body: {SingleJson} The JSON body for request
            action: {str} The action to be performed

        Returns:
            JSON object representing cluster operation.
        """
        response = self._session.post(
            self._get_full_url(
                "cluster-node-pool",
                project_id=self.project_id,
                zone_name=zone_name,
                cluster_name=cluster_name,
                node_pool_name=node_pool_name,
                postfix=f":{action}",
            ),
            json=json_body,
        )
        self.validate_response(
            response,
            error_msg=(
                f'Failed to update cluster\'s "{cluster_name}" node pool '
                f'"{node_pool_name}" {INTEGRATION_DISPLAY_NAME}'
            ),
        )

        return response.json()
