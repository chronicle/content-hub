from __future__ import annotations
from ciaops.pollers.drp import DRPPoller
from .mapping import mapping_config


def create_drp_poller(username: str, api_key: str, api_url: str, verify_ssl: bool = True) -> DRPPoller:
    """Creates and configures a DRPPoller instance with field mappings.

    Args:
        username: DRP API login.
        api_key: DRP API key.
        api_url: Base URL for the DRP API.
        verify_ssl: When False, the underlying requests session skips TLS
            certificate verification. Defaults to True.

    Returns:
        A configured DRPPoller ready for use.
    """
    poller = DRPPoller(username=username, api_key=api_key, api_url=api_url)
    poller.set_verify(verify_ssl)
    for collection, keys in mapping_config.items():
        poller.set_keys(collection_name=collection, keys=keys)
    return poller
