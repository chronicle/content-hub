from __future__ import annotations
import copy
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from pydantic.alias_generators import to_camel

from TIPCommon.transformation import dict_to_flat

from google_gke.core.GKEConsts import COMMA_SPACE


class FilterLogicParam(Enum):
    EQUAL = "Equal"
    CONTAINS = "Contains"

    def __str__(self):
        return self.value


class BaseGKEModel(BaseModel):
    raw_data: Optional[Dict[str, Any]] = None

    class Config:
        alias_generator = to_camel
        populate_by_name = True

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.to_json())

    def to_table(self):
        return [self.to_csv()]

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def is_empty(self):
        return not self.raw_data

    @classmethod
    def to_csv_table_value(cls, obj):
        """
        Parse dictionary to CSV table square value
        :param obj: {dict or list} Dictionary to parse
        :return: {str} Parsed values
        """
        if isinstance(obj, dict):
            return COMMA_SPACE.join([f"{key}:{value}" for key, value in obj.items()])
        if isinstance(obj, list):
            return COMMA_SPACE.join(obj)
        return obj


class KubeCluster(BaseGKEModel):
    """Kubernetes Cluster data model."""

    cluster_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    cluster_network: Optional[str] = None
    cluster_ipv4_cidr: Optional[str] = None
    labels: Optional[Dict[str, Any]] = {}
    cluster_endpoint: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    zone: Optional[str] = None
    initial_cluster_version: Optional[str] = None
    current_master_version: Optional[str] = None
    current_node_version: Optional[str] = None
    create_time: Optional[str] = None
    label_fingerprint: Optional[str] = None

    @classmethod
    def get_name_attribute(cls):
        return "name"

    def to_csv(self):
        return {
            "ID": self.cluster_id,
            "Name": self.name,
            "Description": self.description,
            "Cluster Network": self.cluster_network,
            "Cluster Ipv4 CIDR": self.cluster_ipv4_cidr,
            "Labels": self.to_csv_table_value(self.labels),
            "Cluster Endpoint": self.cluster_endpoint,
            "Status": self.status,
            "Location": self.location,
            "Zone": self.zone,
            "Initial Cluster Version": self.initial_cluster_version,
            "Current Master Version": self.current_master_version,
            "Current Node Version": self.current_node_version,
            "Create Time": self.create_time,
        }


class KubeClusterOperation(BaseGKEModel):
    """Kubernetes Cluster Operation data model."""

    name: Optional[str] = None
    operation_type: Optional[str] = None
    status: Optional[str] = None
    zone: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    target_link: Optional[str] = None
    self_link: Optional[str] = None
    cluster_name: Optional[str] = None

    @classmethod
    def get_name_attribute(cls):
        return "name"

    def to_csv(self):
        return {
            "Name": self.name,
            "Zone": self.zone,
            "Operation Type": self.operation_type,
            "Status": self.status,
            "Start Time": self.start_time,
            "End Time": self.end_time,
            "Target Link": self.target_link,
            "Self Link": self.self_link,
        }

    def to_json(self):
        if self.cluster_name:
            data = copy.deepcopy(super().to_json())
            data.update({"cluster_name": self.cluster_name})
            return data
        return super().to_json()


class KubeClusterNodePool(BaseGKEModel):
    """Kubernetes Cluster Node Pool data model."""

    name: Optional[str] = None
    status: Optional[str] = None
    version: Optional[str] = None
    machine_type: Optional[str] = None
    tags: Optional[List[str]] = []
    service_account: Optional[str] = None
    initial_node_count: Optional[int] = None
    autoscaling: Optional[Dict[str, Any]] = {}
    max_pods_constraint: Optional[Dict[str, Any]] = {}
    locations: Optional[List[str]] = []
    auto_repair: Optional[bool] = None
    auto_upgrade: Optional[bool] = None

    @classmethod
    def get_name_attribute(cls):
        return "name"

    def to_csv(self):
        return {
            "Name": self.name,
            "Status": self.status,
            "Version": self.version,
            "Machine Type": self.machine_type,
            "Tags": self.to_csv_table_value(self.tags),
            "Service Account": self.service_account,
            "Initial Node Count": self.initial_node_count,
            "Autoscaling": self.to_csv_table_value(self.autoscaling),
            "Max Pods Constraint": self.to_csv_table_value(self.max_pods_constraint),
            "Locations": self.to_csv_table_value(self.locations),
        }
