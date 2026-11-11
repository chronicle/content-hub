from __future__ import annotations
from google_cloud_armor.core import datamodels
from TIPCommon.types import SingleJson


def build_list_security_policies(
    raw_data: SingleJson,
) -> list[datamodels.ListSecurityPolicy]:
    """Build a list of security policies object from JSON data.

    Args:
        raw_data (SingleJson): The JSON data representing security policies.

    Returns:
        list[datamodels.ListSecurityPolicy]: A list of security policy objects.
    """
    return [
        datamodels.ListSecurityPolicy.from_json(policy_json=policy_json)
        for policy_json in raw_data
    ]


def build_create_or_update_security_policy(
    raw_data: SingleJson,
) -> datamodels.CreateOrUpdateSecurityPolicy:
    """Build a create or update security policy object from JSON data.

    Args:
        raw_data (SingleJson): The JSON data representing the security policy.

    Returns:
        CreateOrUpdateSecurityPolicy: The created or updated security policy object.
    """
    return datamodels.CreateOrUpdateSecurityPolicy.from_json(policy_json=raw_data)
