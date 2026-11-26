"""Helpers shared by the Portnox Cloud actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.extraction import extract_configuration_param

from .constants import DEFAULT_API_ROOT, INTEGRATION_IDENTIFIER
from .portnox_manager import PortnoxManager

if TYPE_CHECKING:
    from soar_sdk.SiemplifyAction import SiemplifyAction
    from soar_sdk.SiemplifyDataModel import DomainEntityInfo
    from TIPCommon.types import SingleJson

DEVICE_ENTITY_TYPES = (EntityTypes.MACADDRESS, EntityTypes.HOSTNAME, EntityTypes.ADDRESS)


def create_manager(siemplify: SiemplifyAction) -> PortnoxManager:
    """Build a Portnox Cloud client from the integration instance configuration.

    Args:
        siemplify: The running action.

    Returns:
        A configured client.
    """
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Root",
        default_value=DEFAULT_API_ROOT,
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Token",
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Username",
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Password",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        input_type=bool,
        default_value=True,
        print_value=True,
    )
    return PortnoxManager(
        api_root=api_root,
        api_token=api_token,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
        logger=siemplify.LOGGER,
    )


def parse_account_input(raw: str | None) -> list[str]:
    """Turn the value a playbook placeholder produced into a list of account names.

    Placeholders do not always deliver a bare string. A YARA-L outcome variable
    built with array_distinct() arrives as a bracketed list, for example:

        ["user@example.com"]                   -> ["user@example.com"]
        ['a@example.com','b@example.com']      -> ["a@example.com", "b@example.com"]
        user@example.com, other@example.com    -> ["user@example.com", "other@example.com"]
        user@example.com                       -> ["user@example.com"]

    Args:
        raw: The raw parameter value.

    Returns:
        The account names, without empty, "none" and "null" values.
    """
    if raw is None:
        return []
    text = str(raw).strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]

    accounts = []
    for chunk in text.split(","):
        value = chunk.strip().strip('"').strip("'").strip()
        if value and value.lower() not in ("none", "null"):
            accounts.append(value)
    return accounts


def user_entity_accounts(entities: list[DomainEntityInfo]) -> list[str]:
    """Return the account names of the User entities.

    The platform stores entity identifiers in uppercase, while Portnox Cloud account
    names are e-mail addresses, so the identifiers are lowercased.

    Args:
        entities: The action's target entities.

    Returns:
        The lowercased identifiers of the User entities.
    """
    return [e.identifier.lower() for e in entities if e.entity_type == EntityTypes.USER]


def find_devices_for_entity(
    manager: PortnoxManager,
    entity: DomainEntityInfo,
    max_pages: int,
) -> list[SingleJson]:
    """Look up the Portnox Cloud devices that match a MAC address, IP address or hostname entity.

    Args:
        manager: The Portnox Cloud client.
        entity: A MAC address, IP address or hostname entity.
        max_pages: The maximum number of device list pages to read.

    Returns:
        The matching devices.
    """
    if entity.entity_type == EntityTypes.MACADDRESS:
        return manager.find_devices_by_mac(entity.identifier, max_pages=max_pages)
    if entity.entity_type == EntityTypes.ADDRESS:
        return manager.find_devices_by_ip(entity.identifier, max_pages=max_pages)
    return manager.find_devices_by_text(entity.identifier, max_pages=max_pages)
