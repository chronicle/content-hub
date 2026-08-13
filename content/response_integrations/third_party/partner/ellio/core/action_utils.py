"""Shared helpers for the ELLIO actions: config access and target-IP collection."""
from __future__ import annotations

import ipaddress
from collections.abc import Callable
from functools import partial
from typing import Any

from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.extraction import extract_configuration_param

from .constants import INTEGRATION_NAME


def config_reader(siemplify: Any) -> Callable[..., Any]:
    """Callable that reads an ELLIO integration configuration parameter.

    Usage: `cfg = config_reader(siemplify); cfg(param_name="API Key", is_mandatory=True)`.

    Args:
        siemplify: The SiemplifyAction instance.

    Returns:
        A callable wrapping extract_configuration_param for the ELLIO provider.
    """
    return partial(extract_configuration_param, siemplify, provider_name=INTEGRATION_NAME)


def is_public_ip(value: str) -> bool:
    """Check whether a value is a public, globally routable unicast IP address.

    Args:
        value: The IP address string to check.

    Returns:
        True for a public unicast IP; False for private, reserved, multicast,
        or unparsable input.
    """
    try:
        ip = ipaddress.ip_address(value.strip())
    except (ValueError, TypeError, AttributeError):
        return False
    return ip.is_global and not ip.is_multicast


def collect_target_ips(
    siemplify: Any, ip_csv: str | None
) -> tuple[list[str], dict[str, Any], list[str]]:
    """Public IPs to act on, de-duplicated in order.

    ADDRESS entities plus the comma-separated IPs from the `IP Addresses`
    parameter. SOAR-internal entities and any private/reserved/loopback address
    are ALWAYS skipped - ELLIO covers public (external) IPs only, so this
    filtering is built in (not an action option).

    Args:
        siemplify: The SiemplifyAction instance.
        ip_csv: Comma-separated IPs from the `IP Addresses` parameter, or None.

    Returns:
        A (target_ips, entity_by_ip, skipped) tuple.
    """
    ip_csv = ip_csv or ""
    entity_by_ip, skipped = {}, []
    for entity in siemplify.target_entities:
        if entity.entity_type != EntityTypes.ADDRESS:
            continue
        if getattr(entity, "is_internal", False) or not is_public_ip(entity.identifier):
            skipped.append(entity.identifier)
            continue
        entity_by_ip[entity.identifier] = entity
    param_ips = []
    for ip in (p.strip() for p in ip_csv.split(",")):
        if not ip:
            continue
        (param_ips if is_public_ip(ip) else skipped).append(ip)
    target_ips = list(dict.fromkeys(list(entity_by_ip) + param_ips))
    return target_ips, entity_by_ip, list(dict.fromkeys(skipped))
