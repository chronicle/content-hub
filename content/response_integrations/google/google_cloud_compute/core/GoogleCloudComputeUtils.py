from __future__ import annotations

import copy
import itertools
import json
import re
from typing import List, Dict, TYPE_CHECKING

from TIPCommon.types import SingleJson

from google_cloud_compute.core.GoogleCloudComputeExceptions import (
    GoogleCloudComputeResourceNameValidationError,
    GoogleCloudComputeValidationError,
)
from google_cloud_compute.core.GoogleCloudComputeConstants import (
    COLON,
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
    INSTANCE_RESOURCE_NAME_PATTERN,
    RUNNING_STATUS,
)


if TYPE_CHECKING:
    from google_cloud_compute.core import GoogleCloudComputeDatamodels as Datamodels


def load_csv_to_list(csv: str, param_name: str) -> List[str]:
    """
    Covert csv represented as string to a list. Remove duplicates if exist
    :param csv: {str} of comma separated values with delimiter ','
    :param param_name: {str} the name of the parameter we are loading csv to list
    :return: {[str]} List of separated string values
            raise GoogleCloudComputeValidationError if failed to parse csv string
    """
    try:
        return list({t.strip() for t in csv.split(",")})
    except Exception as error:
        raise GoogleCloudComputeValidationError(
            f'Failed to load comma separated string parameter "{param_name}"'
        ) from error


def create_names_or_statuses_string(attributes: list[str], type_: str) -> str:
    """Convert the provided list to filter string.

    For example:
        ['value1', 'value2'] to (type = "value1") OR (type = "value2")

    Args:
        attributes: {List[str]} List like ['value1', 'value2']
        type_: Status or Name

    Returns:
        (name = "value1") OR (name = "value2")
    """
    attributes_list = [f'({type_} = "{attribute}")' for attribute in attributes]
    return " OR ".join(attributes_list)


def create_labels_str(labels: list[str]) -> str:
    """Convert the provided list to filter string.

    For example:
        [Label1:value1, Label2:value2...] = (label.Label1 = "value1") OR
        (label.Label2 = "value2")

    Args:
        labels: List[str] List like [Label1:value1, Label2:value2...]

    Returns:
        String filter like (label.Label1 = "value1") OR (label.Label2 = "value2")
    """
    try:
        attributes_list = []
        for label in labels:
            label_name, value = label.split(":")
            attributes_list.append(f'(labels.{label_name} = "{value}")')

        return " OR ".join(attributes_list)

    except Exception as error:
        raise GoogleCloudComputeValidationError(
            "One of the provided labels filter is not in the format: labels:value"
        ) from error


def create_filter_string(
    names: list[str] | None = None,
    statuses: list[str] | None = None,
    labels: list[str] | None = None,
) -> str:
    """Create filter string to API requests from Google Cloud Compute.

    For example:
        '(name = "instance-1") OR (name = "instance-2") (status = "RUNNING")
        (label.vm_test_tag = "tag1")'

    Args:
        names: List{str} List of names to search: [instance-1, instance-2...]
        statuses: List{str} List of status to search: [RUNNING, STOPPING...]
        labels: List{str} List of names to search: [Label1:value1, Label2:value2...]

    Returns:
        String to filter the results from Google Cloud Compute
    """
    names_str = create_names_or_statuses_string(names, "name") if names else ""
    statuses_str = (
        create_names_or_statuses_string(statuses, "status") if statuses else ""
    )
    labels_str = create_labels_str(labels) if labels else ""

    existing_attributes_string = [
        attr_list for attr_list in [names_str, statuses_str, labels_str] if attr_list
    ]
    return " ".join(existing_attributes_string)


def load_dict_from_csv_kv_list(
    kv_csv: str, param_name: str, kv_delimiter: str | None = COLON
) -> SingleJson:
    """Load list of strings, each represented by a key value separated by a delimiter.

    For example: (kv_csv="hello:world,apple:table", kv_delimiter=':') ->
        {"hello":"world","apple":"table"}

    Args:
        kv_csv: {str} Comma-separated string. Each separated string is a key value
            separated by a delimiter. For example: hello:world, apple:table
        param_name: {str} The name of the Parameter we are loading the dictionary from
        kv_delimiter: {str} Delimiter for each key value

    Returns:
        Dictionary of key value pairs
    """
    try:
        return dict(
            [
                [x.strip() for x in kv.split(kv_delimiter)]
                for kv in load_csv_to_list(kv_csv, param_name)
            ]
        )
    except Exception as error:
        raise GoogleCloudComputeValidationError(
            f'Failed to load comma separated string parameter "{param_name}"'
        ) from error


def is_entity_contained_in_instance(
    instance_network_interfaces: list[Datamodels.InstanceNetworkInterface],
    ip_entity_address: str,
) -> bool:
    """Finds if ip_entity_address contained in instance_network_interfaces.

    Args:
        instance_network_interfaces: Entity network interfaces
        ip_entity_address: {str} IP address

    Returns:
        True if ip_entity_address in instance_network_interfaces. Else, False
    """
    for interface in instance_network_interfaces:
        network_raw_data = interface.raw_data
        if any(
            ip_entity_address.strip() in value for value in network_raw_data.values()
        ):
            return True

    return False


def get_instance_to_enrich_with(
    entity_instances: list[Datamodels.Instance],
) -> Datamodels.Instance | None:
    """Retrieve The instance that the entity should be enriched with.

    if entity_instances > 1 we should get the RUNNING instance. If there are more
    than one RUNNING instance, we will take the last created one.

    Args:
        entity_instances: instances to check

    Returns:
        instance that the entity should be enriched with
    """
    running_instances = [
        instance for instance in entity_instances if instance.status == RUNNING_STATUS
    ]

    if len(entity_instances) == 1 or len(running_instances) != 1:
        return entity_instances[0]

    if len(running_instances) == 1:
        return running_instances[1]

    return None


def prepare_instance_network_interfaces_to_enrich(
    instance: Datamodels.Instance,
) -> SingleJson:
    """Prepare the network interfaces to fit to the enrichment form.

    Args:
        The instance to take the network interfaces from

    Returns:
        Prepared dictionary to enriched with
    """
    network_interfaces = instance.network_interfaces

    if not network_interfaces:
        return {}

    enrichment_data = {}
    for idx, interface in enumerate(network_interfaces):
        access_configs = interface.access_configs
        access_config_type = (
            access_configs[0].get("type") if access_configs[0] else None
        )
        access_config_name = (
            access_configs[0].get("name") if access_configs[0] else None
        )
        access_config_nat_ip = (
            access_configs[0].get("natIP") if access_configs[0] else None
        )

        enrichment_data[f"instance_network_interfaces_name_{idx}"] = interface.name
        enrichment_data[
            f"instance_network_interfaces_name_access_configs_type_{idx}"
        ] = access_config_type
        enrichment_data[
            f"instance_network_interfaces_name_access_configs_name_{idx}"
        ] = access_config_name
        enrichment_data[
            f"instance_network_interfaces_name_access_configs_natIP_{idx}"
        ] = access_config_nat_ip

    return enrichment_data


def prepare_instance_service_account_to_enrich(
    instance: Datamodels.Instance,
) -> SingleJson:
    """Prepare the network interfaces to fit to the enrichment form

    Args:
        The instance to take the network interfaces from

    Returns:
        Prepared dictionary to enriched with
    """
    service_accounts = instance.service_accounts

    if not service_accounts:
        return {}

    enrichment_data = {}
    for idx, service in enumerate(service_accounts):
        enrichment_data[f"service_account_{idx}"] = service.get("email")
        enrichment_data[f"service_account_scopes{idx}"] = (
            ", ".join(service.get("scopes")) if service.get("scopes") else None
        )

    return enrichment_data


def remove_none_from_dict(_dict: Dict) -> Dict:
    """
    Return dictionary without items with None values.
    :param _dict: {Dict} The requested dictionary
    :return: {Dict} dictionary without items with None values
    """
    return {key: value for key, value in _dict.items() if value is not None}


def extract_name_from_address(full_address: str) -> str:
    """Extract display name from resource name.

    Instead of full address, for example:
        https://www.googleapis.com/compute/v1/projects/project/zones/us-central1-a
    The specific value will be returned, for example:
        us-central1-a

    Args:
        full_address:

    Returns:
        Real value
    """
    if not full_address:
        return ""
    start_index = full_address.rfind("/") + 1
    return full_address[start_index:] if full_address[start_index + 1] else ""


def extract_tags_values(tags_dict: Dict) -> List:
    """
    Get list of values from tag attribute of an instance
    :param tags_dict: {Dict} tags dictionary from Google Cloud Compute instance
    :return: {List} list of tags of an instance
    """
    tags_list = []
    if tags_dict.get("items"):
        tags_list.extend(tags_dict.get("items"))

    if tags_dict.get("fingerprint"):
        tags_list.append(tags_dict.get("fingerprint"))

    return tags_list


def fix_json_results(raw_data: Dict) -> Dict:
    """
    Fix raw data to be a valid json.
    :param raw_data: {Dict} Instance raw data
    :return: {Dict} Formatted json result.
    """
    copy_raw_data = copy.deepcopy(raw_data)
    copy_raw_data["zone"] = extract_name_from_address(copy_raw_data.get("zone", ""))
    copy_raw_data["machineType"] = extract_name_from_address(
        copy_raw_data.get("machineType", "")
    )
    for network in copy_raw_data.get("networkInterfaces", []):
        if network.get("network"):
            network["network"] = extract_name_from_address(network.get("network"))

        if network.get("subnetwork"):
            network["subnetwork"] = extract_name_from_address(network.get("subnetwork"))

    for disk in copy_raw_data.get("disks", []):
        if disk.get("source"):
            disk["source"] = extract_name_from_address(disk.get("source"))

            formatted_licenses = []
            for _license in disk.get("licenses", []):
                formatted_licenses.append(extract_name_from_address(_license))

            if formatted_licenses:
                disk["licenses"] = formatted_licenses
    return copy_raw_data


def parse_string_to_dict(string):
    """
    Parse json string to dict
    :param string: string to parse
    :return: {dict} parsed dict
    """
    try:
        return json.loads(string)
    except Exception as err:
        raise GoogleCloudComputeValidationError(
            f"Unable to parse provided json. Error is: {err}"
        ) from err


def extract_instance_resource_path(
    resource_name_str: str, resource_name_pattern: str = INSTANCE_RESOURCE_NAME_PATTERN
) -> str:
    """Extract instance resource path from a given string by known PATTERN.

    Args:
        resource_name_str (str): String that contains instance resource path
        resource_name_pattern (str): Resource name regex pattern

    Raises:
        GoogleCloudComputeValidationError: If string does not contain the PATTERN

    Returns:
        str: Instance resource path
    """
    resource_name_match = re.search(resource_name_pattern, resource_name_str)
    if resource_name_match is None:
        raise GoogleCloudComputeResourceNameValidationError(
            f"Given resource name string does not match expected pattern - "
            f"{resource_name_pattern}"
        )

    return resource_name_match.group()


def snake_to_camel(snake_str):
    first, *other = snake_str.split("_")
    return "".join(itertools.chain(first, *map(lambda s: s.title(), other)))


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60
    )
