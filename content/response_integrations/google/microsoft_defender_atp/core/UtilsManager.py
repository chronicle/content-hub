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
from dataclasses import dataclass

import re

from TIPCommon.consts import BLACKLIST_FILTER, WHITELIST_FILTER
from TIPCommon.types import ChronicleSOAR

from .MicrosoftDefenderATPManager import (
    MicrosoftDefenderATPManager,
    MicrosoftDefenderATPManagerV2,
)

UNIX_FORMAT = 1
DATETIME_FORMAT = 2


def pass_whitelist_filter(
    siemplify, whitelist_as_a_blacklist, model, model_key, whitelist=None
):
    # whitelist filter
    whitelist = whitelist or siemplify.whitelist
    whitelist_filter_type = (
        BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER
    )
    model_value = getattr(model, model_key)
    model_values = model_value if isinstance(model_value, list) else [model_value]

    if whitelist:
        for value in model_values:
            if whitelist_filter_type == BLACKLIST_FILTER and value in whitelist:
                siemplify.LOGGER.info(f"'{value}' did not pass blacklist filter.")
                return False

            if whitelist_filter_type == WHITELIST_FILTER and value not in whitelist:
                siemplify.LOGGER.info(f"'{value}' did not pass whitelist filter.")
                return False

    return True


def is_valid_domain(domain_name):
    regex = "^((?!-)[A-Za-z0-9-]" + "{1,63}(?<!-)\\.)" + "+[A-Za-z]{2,6}"
    p = re.compile(regex)

    if domain_name is None:
        return False

    if re.search(p, domain_name):
        return True
    else:
        return False


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


@dataclass(slots=True)
class DefenderATPManagerConfig:
    client_id: str
    client_secret: str
    tenant_id: str
    resource: str
    chronicle_soar: ChronicleSOAR
    login_api_root: str = None
    defender_api_resource: str = None
    verify_ssl: bool = False
    entities_scope: bool = False
    microsoft_graph_url: str = None


def init_defender_atp_manager(
    config: DefenderATPManagerConfig,
) -> MicrosoftDefenderATPManager | MicrosoftDefenderATPManagerV2:
    """Returns the correct Microsoft Defender ATP Manager based on API version.
    Args:
        config(DefenderATPManagerConfig): Configuration params.

    Returns:
        MicrosoftDefenderATPManager | MicrosoftDefenderATPManagerV2: Microsoft Defender
        ATP Manager.
    """
    if config.microsoft_graph_url:
        manager_class = MicrosoftDefenderATPManagerV2
    else:
        manager_class = MicrosoftDefenderATPManager

    kwargs = {
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "tenant_id": config.tenant_id,
        "resource": config.resource,
        "login_api_root": config.login_api_root,
        "defender_api_resource": config.defender_api_resource,
        "verify_ssl": config.verify_ssl,
        "entities_scope": config.entities_scope,
        "siemplify": config.chronicle_soar,
    }

    if config.microsoft_graph_url and manager_class == MicrosoftDefenderATPManagerV2:
        return manager_class(microsoft_graph_url=config.microsoft_graph_url, **kwargs)

    return manager_class(**kwargs)
