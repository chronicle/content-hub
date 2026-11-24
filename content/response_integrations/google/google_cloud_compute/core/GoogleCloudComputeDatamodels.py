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

import copy
import dataclasses
from enum import Enum
import re
from typing import Dict, Optional

from TIPCommon.types import SingleJson

from .GoogleCloudComputeExceptions import GoogleCloudComputeOperationError
from .GoogleCloudComputeUtils import (
    extract_name_from_address,
    extract_tags_values,
    fix_json_results,
    prepare_instance_network_interfaces_to_enrich,
    prepare_instance_service_account_to_enrich,
)


class RolloutStrategy(Enum):
    ZONE_BY_ZONE = "Zone By Zone"
    CONCURRENT_ZONES = "Concurrent Zones"


class PatchJobStatus(Enum):
    STATE_UNSPECIFIED = "State Unspecified."
    STARTED = "The patch job was successfully initiated."
    INSTANCE_LOOKUP = (
        "The patch job is looking up instances to run the patch on."
    )
    PATCHING = "Instances are being patched."
    SUCCEEDED = "Patch job completed successfully."
    COMPLETED_WITH_ERRORS = "Patch job completed but there were errors."
    CANCELED = "The patch job was canceled."
    TIMED_OUT = "The patch job timed out."


class IPRangeType(Enum):
    SOURCE = "source_ranges"
    DESTINATION = "destination_ranges"


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def is_empty(self):
        return not bool(self.raw_data)


class Instance(BaseModel):
    def __init__(
        self,
        raw_data: SingleJson,
        name: str = None,
        description: str = None,
        status: str = None,
        tags: dict = None,
        labels: Optional[Dict] = None,
        network_interfaces=None,
        zone: str = None,
        metadata: Dict = None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.id = kwargs.get("id")
        self.creation_timestamp = kwargs.get("creationTimestamp")
        self.name = name
        self.tags = tags or {}
        self.type = kwargs.get("type")
        self.description = description
        self.status = status
        self.labels = labels or {}
        self.label_fingerprint = kwargs.get("labelFingerprint")
        self.machine_type = kwargs.get("machineType")
        self.network_interfaces = network_interfaces
        self.zone = zone
        self.can_ip_forward = kwargs.get("canIpForward")
        self.metadata = metadata or {}
        self.service_accounts = kwargs.get("serviceAccounts")
        self.self_link = kwargs.get("selfLink")
        self.last_start_timestamp = kwargs.get("lastStartTimestamp")
        self.last_stop_timestamp = kwargs.get("lastStopTimestamp")

    def as_json(self) -> Dict:
        return fix_json_results(self.raw_data)

    def as_csv(self) -> Dict:
        return {
            "Instance Name": self.name,
            "Instance ID": self.id,
            "Instance Creation Time": self.creation_timestamp,
            "Instance Description": self.description,
            "Instance Type": extract_name_from_address(self.machine_type),
            "Instance Status": self.status,
            "Instance Labels": self.labels,
        }

    def as_enrichment(self):
        """Return instance information as a enriched dictionary."""
        enrichment_data = {
            "instance_id": self.id,
            "creation_timestamp": self.creation_timestamp,
            "instance_name": self.name,
            "description": self.description,
            "tags": ", ".join(extract_tags_values(self.tags)) if self.tags else None,
            "machine_type": extract_name_from_address(self.machine_type),
            "instance_status": self.status,
            "zone": extract_name_from_address(self.raw_data.get("zone", "")),
            "can_ip_forward": self.can_ip_forward,
            "metadata": self.get_flat_value(self.metadata) if self.metadata else None,
            "link_to_Google_Compute": self.self_link,
            "labels": self.get_flat_value(self.labels) if self.labels else None,
            "instance_last_start_timestamp": self.last_start_timestamp,
            "instance_last_stop_timestamp": self.last_stop_timestamp,
        }

        enrichment_data.update(prepare_instance_network_interfaces_to_enrich(self))
        enrichment_data.update(prepare_instance_service_account_to_enrich(self))

        return enrichment_data

    def get_flat_value(self, object_) -> str:
        """Flatten an object into a string, join it with comma separated values."""
        if isinstance(object_, list):
            return ",".join(self.get_flat_value(el) for el in object_)

        if isinstance(object_, dict):
            return ",".join(self.get_flat_value(el) for el in object_.values())

        return str(object_)

    def as_enrichment_csv(self, enrichment_dict: Dict):
        return [{"key": key, "value": value} for key, value in enrichment_dict.items()]


class InstanceIAMPolicy(BaseModel):
    """
    Instance IAM Policy data model
    """

    def __init__(self, raw_data, etag: Optional[str] = None, **_):
        super().__init__(raw_data)
        self.etag = etag


class OperationResource(BaseModel):
    """
    Operation Resource data model
    """

    def __init__(
        self,
        raw_data: Optional[SingleJson] = None,
        zone: Optional[str] = None,
        status: Optional[str] = None,
        self_link: Optional[str] = None,
    ):
        super().__init__(raw_data)
        self.zone = zone
        self.status = status
        self.self_link = self_link

    @property
    def is_running(self) -> bool:
        return self.status in ["RUNNING", "PENDING"]

    @property
    def is_finished(self) -> bool:
        return self.status == "DONE"

    def to_json(self):
        try:
            if self.zone:
                raw_data = copy.deepcopy(self.raw_data)
                raw_data.update({"zone": self.zone.rsplit("/", 1)[-1]})
                return raw_data
        except:
            pass
        return self.raw_data

    def raise_for_errors(self) -> None:
        """Raise GoogleCloudComputeOperationError if operation has errors."""
        operation_error = self.raw_data.get("error", {})
        if not operation_error:
            return

        errors = operation_error.get("errors", [])
        errors_message = ", ".join(
            err.get("message") for err in errors if "message" in err
        )
        raise GoogleCloudComputeOperationError(errors_message)


class InstanceNetworkInterface:
    def __init__(
        self,
        raw_data: Optional[SingleJson] = None,
        network: str = None,
        subnetwork: str = None,
        name: str = None,
        fingerprint: str = None,
        kind: str = None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.network = network
        self.subnetwork = subnetwork
        self.network_ip = kwargs.get("networkIP")
        self.name = name
        self.access_configs = kwargs.get("accessConfigs", [])
        self.ipv6_access_configs = kwargs.get("ipv6AccessConfigs", [])
        self.fingerprint = fingerprint
        self.stack_type = kwargs.get("stackType")
        self.kind = kind


@dataclasses.dataclass
class PatchJob:
    display_name: str
    instance_filter: SingleJson
    description: str | None
    patch_config: SingleJson | None
    duration: str
    rollout: SingleJson
    name: str | None = None
    percent_complete: float | None = None
    error_message: str | None = None
    state: PatchJobStatus | None = None
    raw_data: SingleJson | None = None

    @property
    def is_cancelled(self) -> bool:
        return self.state == PatchJobStatus.CANCELED

    @property
    def is_finished(self) -> bool:
        return self.state == PatchJobStatus.SUCCEEDED

    @property
    def is_failed(self) -> bool:
        return self.state == PatchJobStatus.COMPLETED_WITH_ERRORS

    @property
    def is_running(self) -> bool:
        return self.state in (
            PatchJobStatus.STATE_UNSPECIFIED,
            PatchJobStatus.STARTED,
            PatchJobStatus.INSTANCE_LOOKUP,
            PatchJobStatus.PATCHING,
        )

    @property
    def is_timed_out(self) -> bool:
        return self.state == PatchJobStatus.TIMED_OUT

    @classmethod
    def from_json(cls, json_data: SingleJson) -> PatchJob:
        return PatchJob(
            display_name=json_data["displayName"],
            instance_filter=json_data["instanceFilter"],
            description=json_data.get("description"),
            patch_config=json_data.get("patchConfig"),
            duration=json_data["duration"],
            rollout=json_data["rollout"],
            name=json_data["name"],
            percent_complete=json_data.get("percentComplete"),
            error_message=json_data.get("errorMessage"),
            state=PatchJobStatus[json_data["state"]],
            raw_data=json_data,
        )

    def as_dict(self) -> SingleJson:
        return {
            "description": self.description,
            "instanceFilter": self.instance_filter,
            "patchConfig": self.patch_config,
            "duration": self.duration,
            "displayName": self.display_name,
            "rollout": self.rollout,
        }


@dataclasses.dataclass
class FirewallRule:
    raw_data: SingleJson | None = None
    name: str | None = None
    source_ranges: list[str] | None = None
    source_tags: list[str] | None = None
    source_service_accounts: list[str] | None = None
    destination_ranges: list[str] | None = None
    allowed: list[dict[str, str | list[str]]] | None = None
    denied: list[dict[str, str | list[str]]] | None = None

    def to_json(self):
        return self.raw_data

    def as_dict(self) -> SingleJson:
        """Prepare firewall rule as a dictionary."""
        dict_ = {"name": self.name}

        if self.allowed is not None or self.denied is not None:
            dict_["allowed"] = self.allowed
            dict_["denied"] = self.denied

        if self.source_ranges:
            dict_["sourceRanges"] = (
                self.source_ranges if self.source_ranges != ["none"] else None
            )

        if self.source_tags:
            dict_["sourceTags"] = (
                self.source_tags if self.source_tags != ["none"] else None
            )

        if self.source_service_accounts:
            dict_["sourceServiceAccounts"] = (
                self.source_service_accounts
                if self.source_service_accounts != ["none"]
                else None
            )

        if self.destination_ranges:
            dict_["destinationRanges"] = (
                self.destination_ranges if self.destination_ranges != ["none"] else None
            )

        return dict_

    @staticmethod
    def camel_to_snake(value: str) -> str:
        return re.sub(r"([A-Z]+)", r"_\1", value).lower()

    @classmethod
    def from_dict(cls, dict_) -> FirewallRule:
        class_fields = {f.name for f in dataclasses.fields(cls)}
        return cls(
            raw_data=dict_, **{
                cls.camel_to_snake(k): v for k, v in dict_.items()
                if cls.camel_to_snake(k) in class_fields
            }
        )

    def extend_ip_ranges(self, type_: IPRangeType, ip_ranges: set[str]) -> None:
        """Add the IP ranges to firewall rule."""
        ip_range_ = getattr(self, type_.value) or []
        setattr(self, type_.value, list(ip_ranges.union(ip_range_)))

    def remove_ip_ranges(self, type_: IPRangeType, ip_ranges: set[str]) -> None:
        """Remove the IP ranges from firewall rule."""
        ip_range_ = set(getattr(self, type_.value) or [])
        ip_range_.difference_update(ip_ranges)
        setattr(self, type_.value, list(ip_range_) or ["none"])

    def update_ports(self, protocol, ports_list):
        """Update ports list with new protocol and ports."""
        ports_and_protocols = self.allowed if self.allowed is not None else self.denied
        existing_tcp_config = next(
            filter(
                lambda config: config["IPProtocol"] == protocol, ports_and_protocols
            ),
            None,
        )

        if not existing_tcp_config:
            existing_tcp_config = {"IPProtocol": protocol, "ports": []}
            ports_and_protocols.append(existing_tcp_config)

        if ports_list == ["none"]:
            ports_and_protocols.remove(existing_tcp_config)
            return

        existing_tcp_config["ports"] = ports_list if ports_list != ["all"] else []
