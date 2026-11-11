from __future__ import annotations

from typing import Any
import json

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_TIMEDOUT,
)
from google_gke.core import GKEConsts
from google_gke.core.GKEDatamodels import KubeCluster, KubeClusterNodePool, KubeClusterOperation
from google_gke.core.GKEExceptions import (
    GoogleGKEInvalidClusterNameError,
    GoogleGKEInvalidOperationNameError,
    GoogleGKEInvalidNodePoolNameError,
    GoogleGKENotFoundError,
    GoogleGKEServiceError,
)
from google_gke.core.GKEManagers import GKEApiManager
from google_gke.core.GKEUtils import remove_none_values


OPERATION_TIMEOUT_MESSAGE = (
    f"\nNote: This action is an async action. The Siemplify action timed out but the "
    f"{GKEConsts.INTEGRATION_DISPLAY_NAME} operation might be still running. Please "
    f'use the action "Get Operation Status" or check the status on the '
    f"{GKEConsts.INTEGRATION_DISPLAY_NAME}'s side. Additionally, consider adjusting "
    f"action's timeout in the IDE for action to be able to finish completely."
)


class GKEBaseService:
    """Base class for GKE Service."""

    def __init__(self, api_manager: GKEApiManager, logger, **kwargs):
        self.api_manager = api_manager
        self.logger = logger


class GKEOperationService(GKEBaseService):
    """This class provides access to GKE Operations Service."""

    def __init__(self, api_manager: GKEApiManager, logger, zone_name: str, **kwargs):
        super().__init__(api_manager=api_manager, logger=logger, **kwargs)
        self.zone_name = zone_name

    def list(self) -> list[KubeClusterOperation]:
        """List all operations in the configured zone.

        Returns:
            List of KubeClusterOperation data models
        """
        operations_json = self.api_manager.list_operations(self.zone_name)
        return [
            KubeClusterOperation(raw_data=operation_json, **operation_json)
            for operation_json in operations_json
        ]

    def get(
        self, operation_name: str, cluster_name: str | None = None
    ) -> KubeClusterOperation:
        """Get operation from the configured zone and operation_name.

        Args:
            operation_name: GKE operation name.
            cluster_name: Cluster name on which operation is running.

        Returns:
            KubeClusterOperation data model
        """
        try:
            operations_json = self.api_manager.get_operation(
                self.zone_name, operation_name
            )
        except GoogleGKENotFoundError as err:
            raise GoogleGKEInvalidOperationNameError(
                f'Provided operation name "{operation_name}" was not found.'
            ) from err

        return KubeClusterOperation(
            raw_data=operations_json, cluster_name=cluster_name, **operations_json
        )

    @staticmethod
    def check_status(
        operation: KubeClusterOperation, timeout_approached: bool = False
    ) -> tuple[str, Any, int]:
        """Check GKE operation status and return appropriate action results.

        Args:
            operation: {KubeClusterOperation} Kubernetes cluster data model
            timeout_approached: {bool} True if action's timeout is approaching,
                otherwise False

        Returns:
            Output message, result value and the status of the action
        """
        result_value = False
        status = EXECUTION_STATE_COMPLETED

        if (
            not timeout_approached
            and operation.status in GKEConsts.IN_PROGRESS_STATUSES
        ):
            status = EXECUTION_STATE_INPROGRESS
            output_message = (
                f"Operation {operation.name} is still in progress, "
                f"current status: {operation.status}."
            )
            result_value = json.dumps(operation.name)

        elif operation.status == GKEConsts.DONE:
            output_message = f"Operation {operation.name} successfully finished."
            result_value = True
        else:
            output_message = (
                f"Operation {operation.name} failed to complete with the "
                f"following status: {operation.status}."
            )
            if timeout_approached:
                status = EXECUTION_STATE_TIMEDOUT
                output_message += OPERATION_TIMEOUT_MESSAGE

        return output_message, result_value, status


class GKEClustersService(GKEBaseService):
    """This class provides access to GKE Clusters Service."""

    def __init__(
        self, api_manager: GKEApiManager, logger, zone_name: str = "-", **kwargs
    ):
        super().__init__(api_manager=api_manager, logger=logger, **kwargs)
        self.zone_name = zone_name

    def list(self) -> list[KubeCluster]:
        """Lists all clusters in a project in configured zone or all zones.

        Returns:
            List of Kubernetes cluster data models
        """
        clusters_json = self.api_manager.list_clusters(self.zone_name)
        return [
            KubeCluster(raw_data=cluster_json, **cluster_json)
            for cluster_json in clusters_json
        ]

    def get(self, cluster_name: str) -> KubeCluster:
        """Gets a Kubernetes cluster by configured zone and cluster name.

        Args:
            cluster_name: GKE cluster name

        Returns:
            Kubernetes cluster data model
        """
        if not (self.zone_name and self.zone_name != "-"):
            raise GoogleGKEServiceError("zone_name must be provided.")

        try:
            cluster_json = self.api_manager.get_cluster(
                zone_name=self.zone_name, cluster_name=cluster_name
            )
        except GoogleGKENotFoundError as e:
            raise GoogleGKEInvalidClusterNameError(
                f'Provided cluster name "{cluster_name}" was not found.'
            ) from e

        return KubeCluster(raw_data=cluster_json, **cluster_json)

    def update_labels(
        self, cluster_name: str, label_fingerprint: str, labels: dict
    ) -> KubeClusterOperation:
        """Update labels of a specified cluster.

        Args:
            cluster_name: GKE cluster name
            label_fingerprint: {str} The fingerprint of the previous set of labels
                for this resource
            labels: {dict} The labels to set for that cluster.

        Returns:
            Kubernetes cluster operation data model
        """
        if not (self.zone_name and self.zone_name != "-"):
            raise GoogleGKEServiceError("zone_name must be provided.")

        action = "setResourceLabels"
        json_body = {"resourceLabels": labels, "labelFingerprint": label_fingerprint}

        try:
            response_json = self.api_manager.update_cluster(
                zone_name=self.zone_name,
                cluster_name=cluster_name,
                json_body=json_body,
                action=action,
            )
        except GoogleGKENotFoundError as e:
            raise GoogleGKEInvalidClusterNameError(
                f'Provided cluster name "{cluster_name}" was not found.'
            ) from e

        return KubeClusterOperation(
            raw_data=response_json, cluster_name=cluster_name, **response_json
        )

    def update_addons(
        self,
        cluster_name: str,
        http_load_balancing_disabled: bool | None = None,
        horizontal_pod_autoscaling_disabled: bool | None = None,
        network_policy_config_disabled: bool | None = None,
        cloud_run_config_disabled: bool | None = None,
        cloud_run_config_load_balancer_type: str | None = None,
        dns_cache_config_enabled: bool | None = None,
        config_connector_config_enabled: bool | None = None,
        gce_persistent_disk_csi_driver_config_enabled: bool | None = None,
    ) -> KubeClusterOperation:
        """Update the addons for a specific cluster.

        Args:
            cluster_name (str): GKE cluster name
            http_load_balancing_disabled: {bool} Whether the HTTP Load Balancing
                controller is disabled in the cluster.
            horizontal_pod_autoscaling_disabled: {bool} Whether the Horizontal Pod
                Autoscaling feature is disabled in the cluster.
            network_policy_config_disabled: {str} Configuration for NetworkPolicy.
                This only tracks whether the addon is disabled or not on the Master,
                it does not track whether network policy is enabled for the nodes.
            cloud_run_config_disabled: {bool} Whether the Cloud Run addon disable or
                not in the cluster. If enabled, cloud_run_config_load_balancer_type
                must be provided
            cloud_run_config_load_balancer_type: {str} Load balancer type of ingress
                service of Cloud Run. Possible Values: LOAD_BALANCER_TYPE_UNSPECIFIED,
                LOAD_BALANCER_TYPE_EXTERNAL or LOAD_BALANCER_TYPE_INTERNAL.
                Note: cloud_run_config_disabled parameter must be provided if
                this parameter is provided
            dns_cache_config_enabled: {bool} Whether NodeLocal DNSCache is enabled
                for this cluster.
            config_connector_config_enabled: {bool} Whether Cloud Connector is enabled
                for this cluster.
            gce_persistent_disk_csi_driver_config_enabled: {bool} Whether the Compute
                Engine PD CSI driver is enabled for this cluster.

        Returns:
             Kubernetes cluster operation data model
        """
        if not (self.zone_name and self.zone_name != "-"):
            raise GoogleGKEServiceError("zone_name must be provided.")

        action = "setAddons"
        json_body = {
            "addonsConfig": remove_none_values(
                {
                    "httpLoadBalancing": (
                        {"disabled": http_load_balancing_disabled}
                        if isinstance(http_load_balancing_disabled, bool)
                        else None
                    ),
                    "horizontalPodAutoscaling": (
                        {"disabled": horizontal_pod_autoscaling_disabled}
                        if isinstance(horizontal_pod_autoscaling_disabled, bool)
                        else None
                    ),
                    "networkPolicyConfig": (
                        {"disabled": network_policy_config_disabled}
                        if isinstance(network_policy_config_disabled, bool)
                        else None
                    ),
                    "cloudRunConfig": (
                        remove_none_values(
                            {
                                "disabled": cloud_run_config_disabled,
                                "loadBalancerType": cloud_run_config_load_balancer_type,
                            }
                        )
                        if isinstance(cloud_run_config_disabled, bool)
                        else None
                    ),
                    "dnsCacheConfig": (
                        {"enabled": dns_cache_config_enabled}
                        if isinstance(dns_cache_config_enabled, bool)
                        else None
                    ),
                    "configConnectorConfig": (
                        {"enabled": config_connector_config_enabled}
                        if isinstance(config_connector_config_enabled, bool)
                        else None
                    ),
                    "gcePersistentDiskCsiDriverConfig": (
                        {"enabled": gce_persistent_disk_csi_driver_config_enabled}
                        if isinstance(
                            gce_persistent_disk_csi_driver_config_enabled, bool
                        )
                        else None
                    ),
                }
            )
        }

        try:
            response_json = self.api_manager.update_cluster(
                zone_name=self.zone_name,
                cluster_name=cluster_name,
                json_body=json_body,
                action=action,
            )
        except GoogleGKENotFoundError as e:
            raise GoogleGKEInvalidClusterNameError(
                f'Provided cluster name "{cluster_name}" was not found.'
            ) from e

        return KubeClusterOperation(
            raw_data=response_json, cluster_name=cluster_name, **response_json
        )


def cluster_node_service_wrapper(func):
    """ClusterNodeService wrapper to handle common exceptions."""

    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)

        except GoogleGKEInvalidNodePoolNameError as err:
            raise GoogleGKEInvalidNodePoolNameError(
                f'Provided node pool name "{self.node_pool_name}" ' f"was not found."
            ) from err
        except GoogleGKENotFoundError as err:
            raise GoogleGKEInvalidClusterNameError(
                f'Provided cluster name "{self.cluster_name}" ' f"was not found."
            ) from err

    return wrapper


class GKEClusterNodesService(GKEBaseService):
    """This class provides access to GKE Cluster Nodes Service."""

    def __init__(
        self,
        api_manager: GKEApiManager,
        logger,
        zone_name: str,
        cluster_name: str,
        **kwargs,
    ):
        super().__init__(api_manager=api_manager, logger=logger, **kwargs)
        self.zone_name = zone_name
        self.cluster_name = cluster_name

    @cluster_node_service_wrapper
    def list(self) -> list[KubeClusterNodePool]:
        """List GKE Cluster Node Pools using configured zone and cluster.

        Returns:
            List of KubeClusterNodePool data models
        """
        node_pools_json = self.api_manager.list_cluster_node_pools(
            zone_name=self.zone_name, cluster_name=self.cluster_name
        )
        return [
            KubeClusterNodePool(raw_data=node_pool_json, **node_pool_json)
            for node_pool_json in node_pools_json
        ]

    @cluster_node_service_wrapper
    def get(self, node_pool_name: str) -> KubeClusterNodePool:
        """GetCluster Node Pool using zone, cluster_name and node_pool_name.

        Args:
            node_pool_name: GKE cluster node pool name

        Returns:
            KubeClusterNodePool object
        """
        node_pool_json = self.api_manager.get_cluster_node_pool(
            zone_name=self.zone_name,
            cluster_name=self.cluster_name,
            node_pool_name=node_pool_name,
        )
        return KubeClusterNodePool(raw_data=node_pool_json, **node_pool_json)

    @cluster_node_service_wrapper
    def set_pool_autoscaling(
        self,
        node_pool_name: str,
        autoscaling_enabled: bool | None = None,
        min_node_count: int | None = None,
        max_node_count: int | None = None,
    ) -> KubeClusterOperation:
        """Sets the autoscaling settings for the specified node pool.

        Args:
            node_pool_name: GKE cluster node pool name
            autoscaling_enabled: {bool} Is autoscaling enabled for this node pool
            min_node_count: {int} Minimum number of nodes in the NodePool.
                Must be >= 1 and <= maxNodeCount
            max_node_count: {int} Maximum number of nodes in the NodePool.
                Must be >= minNodeCount. There has to be enough quota to scale
                up the cluster

        Returns:
             Kubernetes cluster operation data model
        """
        action = "setAutoscaling"
        json_body = {
            "autoscaling": remove_none_values(
                {
                    "enabled": autoscaling_enabled,
                    "minNodeCount": min_node_count,
                    "maxNodeCount": max_node_count,
                    "autoprovisioned": False,
                }
            )
        }

        operation_json = self.api_manager.update_cluster_node_pool(
            zone_name=self.zone_name,
            cluster_name=self.cluster_name,
            node_pool_name=node_pool_name,
            json_body=json_body,
            action=action,
        )
        return KubeClusterOperation(
            raw_data=operation_json, cluster_name=self.cluster_name, **operation_json
        )

    @cluster_node_service_wrapper
    def set_pool_management(
        self,
        node_pool_name: str,
        auto_upgrade: bool | None = None,
        auto_repair: bool | None = None,
    ) -> KubeClusterOperation:
        """Sets the node management options for the specified node pool.

        Args:
            node_pool_name (str): GKE cluster node pool name
            auto_upgrade: {bool} A flag that specifies whether node auto-upgrade
                is enabled for the node pool. If enabled, node auto-upgrade
                helps keep the nodes in your node pool up to date with the
                latest release version of Kubernetes.
            auto_repair: {bool} A flag that specifies whether the node auto-repair
                is enabled for the node pool. If enabled, the nodes in this node
                pool will be monitored and, if they fail health checks too many
                times, an automatic repair action will be triggered.

        Returns:
             Kubernetes cluster operation data model
        """
        action = "setManagement"
        json_body = {
            "management": remove_none_values(
                {"autoUpgrade": auto_upgrade, "autoRepair": auto_repair}
            )
        }

        operation_json = self.api_manager.update_cluster_node_pool(
            zone_name=self.zone_name,
            cluster_name=self.cluster_name,
            node_pool_name=node_pool_name,
            json_body=json_body,
            action=action,
        )
        return KubeClusterOperation(
            raw_data=operation_json, cluster_name=self.cluster_name, **operation_json
        )

    @cluster_node_service_wrapper
    def set_pool_size(
        self, node_pool_name: str, node_count: int
    ) -> KubeClusterOperation:
        """Sets the size for a specific node pool.

        The new size will be used for all replicas, including future replicas
        created by modifying NodePool.locations.

        Args:
            node_pool_name (str): GKE cluster node pool name
            node_count: {int} The desired node count for the pool.

        Returns:
             Kubernetes cluster operation data model
        """
        action = "setSize"
        json_body = {"nodeCount": node_count}

        operation_json = self.api_manager.update_cluster_node_pool(
            zone_name=self.zone_name,
            cluster_name=self.cluster_name,
            node_pool_name=node_pool_name,
            json_body=json_body,
            action=action,
        )
        return KubeClusterOperation(
            raw_data=operation_json, cluster_name=self.cluster_name, **operation_json
        )
