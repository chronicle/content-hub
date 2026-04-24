from __future__ import annotations
from ciaops.pollers.drp import DRPPoller
from .mapping import mapping_config


def create_drp_poller(username, api_key, api_url):
    """Creates and configures a DRPPoller instance with field mappings."""
    poller = DRPPoller(username=username, api_key=api_key, api_url=api_url)
    for collection, keys in mapping_config.items():
        poller.set_keys(collection_name=collection, keys=keys)
    return poller
