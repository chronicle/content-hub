from __future__ import annotations
from typing import List

from google_cloud_compute.core.GoogleCloudComputeDatamodels import (
    Instance,
    InstanceNetworkInterface,
    InstanceIAMPolicy,
    OperationResource, PatchJob,
)


class GoogleCloudComputeParser:
    """
    Google Cloud Compute Transformation Layer.
    """

    @staticmethod
    def build_instances_objs(
        response_json, extract_key: str = "items"
    ) -> List[Instance]:
        """Build instance data models from raw data JSON."""
        return [
            GoogleCloudComputeParser.build_instance_obj(item)
            for item in response_json.get(extract_key, [])
        ]

    @staticmethod
    def build_instance_obj(instance_raw_data) -> Instance:
        network_interfaces = None
        if instance_raw_data.get("networkInterfaces"):
            network_interfaces = (
                GoogleCloudComputeParser.build_instance_network_interfaces_objs(
                    instance_raw_data.get("networkInterfaces")
                )
            )
        return Instance(
            raw_data=instance_raw_data,
            network_interfaces=network_interfaces,
            **instance_raw_data
        )

    @staticmethod
    def build_instance_network_interfaces_objs(
        network_interfaces,
    ) -> List[InstanceNetworkInterface]:
        return [
            GoogleCloudComputeParser.build_instance_network_interface_obj(item)
            for item in network_interfaces
        ]

    @staticmethod
    def build_instance_network_interface_obj(
        network_interfaces,
    ) -> InstanceNetworkInterface:
        return InstanceNetworkInterface(
            raw_data=network_interfaces, **network_interfaces
        )

    @staticmethod
    def build_instance_iam_policy_obj(raw_data) -> InstanceIAMPolicy:
        return InstanceIAMPolicy(raw_data, **raw_data)

    @staticmethod
    def build_operation_resource_obj(raw_data) -> OperationResource:
        return OperationResource(
            raw_data=raw_data,
            zone=raw_data.get("zone"),
            self_link=raw_data.get("selfLink"),
            status=raw_data.get("status"),
        )

    @staticmethod
    def build_patch_job(raw_data) -> PatchJob:
        return PatchJob.from_json(raw_data)
