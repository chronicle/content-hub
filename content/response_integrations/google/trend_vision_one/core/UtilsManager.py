# Copyright 2026 Google LLC
# ruff: file-ignore[invalid-module-name, error-instead-of-exception, verbose-log-message]
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

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyDataModel import DomainEntityInfo, EntityTypes

try:
    from TIPCommon.extraction import extract_action_param
    from TIPCommon.transformation import string_to_multi_value
except ImportError:
    from TIPCommon import extract_action_param, string_to_multi_value

from . import datamodels
from .constants import (
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
    OBJECT_TYPE_DOMAIN,
    OBJECT_TYPE_FILE_SHA1,
    OBJECT_TYPE_FILE_SHA256,
    OBJECT_TYPE_IP,
    OBJECT_TYPE_SENDER_MAIL_ADDRESS,
    OBJECT_TYPE_URL,
    PARAM_DOMAINS,
    PARAM_EMAIL_ADDRESSES,
    PARAM_FILE_HASHES,
    PARAM_IPS,
    PARAM_URLS,
    SHA1_HEX_REGEX,
    SHA256_HEX_REGEX,
)
from .TrendVisionOneExceptions import TrendVisionOneException

if TYPE_CHECKING:
    from soar_sdk.SiemplifyAction import SiemplifyAction
    from soar_sdk.SiemplifyLogger import SiemplifyLogger
    from TIPCommon.types import SingleJson

    from .TrendVisionOneManager import TrendVisionOneManager


def get_entity_original_identifier(entity: DomainEntityInfo) -> str:
    """Get the original identifier from a Chronicle entity.

    Args:
        entity: Chronicle entity instance.

    Returns:
        Original identifier string.

    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def check_submit_files_in_system(files: list[str]) -> list[str]:
    """Return not accessible or not found files in filesystem.

    Args:
        files: List of file paths to check.

    Returns:
        List of file paths that do not exist or are not readable.

    """
    return [
        file
        for file in files
        if not (Path(file).exists() and os.access(file, os.R_OK))
    ]


def is_async_action_global_timeout_approaching(
    siemplify: SiemplifyAction, start_time: int
) -> bool:
    """Check whether the SOAR global execution deadline is approaching.

    Args:
        siemplify: SiemplifyAction execution instance.
        start_time: Unix timestamp (in ms) when the current iteration started.

    Returns:
        True if the remaining time is below the threshold, False otherwise.

    """
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60 * 1000
    )


def process_agents(
    manager: TrendVisionOneManager,
    agent_uids: list[str],
) -> datamodels.AgentResult:
    """Search for each agent UUID and categorize them as successful or failed.

    Args:
        manager: TrendVisionOneManager instance for interacting with the API.
        agent_uids: List of agent UUIDs to process.

    Returns:
        AgentResult containing `successful_agents` and `failed_agents`.

    """
    agent_result: datamodels.AgentResult = datamodels.AgentResult([], [])
    for agent_id in agent_uids:
        try:
            if (agent := manager.search_endpoint(agent_id=agent_id)) is not None:
                agent_result.successful_agents.append(agent)
            else:
                agent_result.failed_agents.append(agent_id)
                manager.siemplify.LOGGER.info(f"Agent UUID not found: {agent_id}")

        except TrendVisionOneException as e:
            agent_result.failed_agents.append(agent_id)
            manager.siemplify.LOGGER.error(f"An error occurred on agent: {agent_id}")
            manager.siemplify.LOGGER.exception(e)

    return agent_result


SUPPORTED_BLOCKLIST_ENTITY_TYPES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.DOMAIN,
    EntityTypes.URL,
    EntityTypes.USER,
    EntityTypes.FILEHASH,
]

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def _validate_and_normalize_ioc(
    obj_type: str, raw_value: str, logger: SiemplifyLogger
) -> tuple[str, str] | None:
    """Validate and normalize a single indicator of compromise.

    Args:
        obj_type: Target object type or 'hash' for file hashes.
        raw_value: Raw indicator string.
        logger: SiemplifyLogger instance for logging skipped indicators.

    Returns:
        Tuple of (resolved_object_type, normalized_value) or None if invalid.

    """
    if obj_type == "hash":
        if re.match(SHA1_HEX_REGEX, raw_value):
            return (OBJECT_TYPE_FILE_SHA1, raw_value.lower())
        if re.match(SHA256_HEX_REGEX, raw_value):
            return (OBJECT_TYPE_FILE_SHA256, raw_value.lower())
        logger.info(
            f"Skipping hash '{raw_value}' because only valid hexadecimal SHA1 (40 chars) "
            "and SHA256 (64 chars) are supported."
        )
        return None

    if obj_type == OBJECT_TYPE_SENDER_MAIL_ADDRESS:
        if EMAIL_REGEX.match(raw_value):
            return (OBJECT_TYPE_SENDER_MAIL_ADDRESS, raw_value)
        logger.info(
            f"Skipping email '{raw_value}' because it does not match a valid email address pattern."
        )
        return None

    return (obj_type, raw_value)


def _extract_entity_object(
    entity: DomainEntityInfo, siemplify: SiemplifyAction
) -> tuple[str, str, str] | None:
    """Extract suspicious object type and normalized value from a Chronicle entity.

    Args:
        entity: Chronicle DomainEntityInfo object.
        siemplify: SiemplifyAction instance for logging.

    Returns:
        Tuple of (object_type, normalized_value, original_identifier) or None if skipped.

    """
    original_identifier = get_entity_original_identifier(entity).strip()
    if not original_identifier:
        return None

    entity_type_to_obj_type = {
        EntityTypes.ADDRESS: OBJECT_TYPE_IP,
        EntityTypes.HOSTNAME: OBJECT_TYPE_DOMAIN,
        EntityTypes.DOMAIN: OBJECT_TYPE_DOMAIN,
        EntityTypes.URL: OBJECT_TYPE_URL,
        EntityTypes.USER: OBJECT_TYPE_SENDER_MAIL_ADDRESS,
        EntityTypes.FILEHASH: "hash",
    }
    raw_obj_type = entity_type_to_obj_type.get(entity.entity_type)
    if not raw_obj_type:
        return None

    validated = _validate_and_normalize_ioc(
        raw_obj_type, original_identifier, siemplify.LOGGER
    )
    if not validated:
        return None

    resolved_type, normalized_val = validated
    return (resolved_type, normalized_val, original_identifier)


def _extract_manual_parameter_objects(
    siemplify: SiemplifyAction,
) -> list[tuple[str, str, str]]:
    """Extract and normalize suspicious objects from manual action parameters.

    Args:
        siemplify: SiemplifyAction instance to extract parameters from.

    Returns:
        List of tuples (object_type, normalized_value, raw_value).

    """
    param_configs = [
        (PARAM_IPS, OBJECT_TYPE_IP),
        (PARAM_DOMAINS, OBJECT_TYPE_DOMAIN),
        (PARAM_URLS, OBJECT_TYPE_URL),
        (PARAM_FILE_HASHES, "hash"),
        (PARAM_EMAIL_ADDRESSES, OBJECT_TYPE_SENDER_MAIL_ADDRESS),
    ]
    extracted_objects: list[tuple[str, str, str]] = []

    for param_name, obj_type in param_configs:
        raw_val = extract_action_param(
            siemplify, param_name=param_name, is_mandatory=False
        )
        if not raw_val:
            continue
        for item in string_to_multi_value(raw_val):
            item_clean = item.strip()
            if not item_clean:
                continue
            validated = _validate_and_normalize_ioc(
                obj_type, item_clean, siemplify.LOGGER
            )
            if validated:
                resolved_type, normalized_val = validated
                extracted_objects.append((resolved_type, normalized_val, item_clean))

    return extracted_objects


def build_blocklist_payloads(
    siemplify: SiemplifyAction,
    suitable_entities: list[DomainEntityInfo],
    description: str | None = None,
    *,
    include_description: bool = True,
) -> tuple[list[SingleJson], dict[str, str]]:
    """Build deduplicated suspicious object payloads and a normalized-to-original identifier map.

    Args:
        siemplify: SiemplifyAction instance.
        suitable_entities: Supported Chronicle entities in scope.
        description: Optional description to attach when adding suspicious objects.
        include_description: Whether to include the description field in payloads.

    Returns:
        Tuple of (list of suspicious object dictionaries, dict mapping normalized_value -> original_identifier).

    """
    payloads: list[SingleJson] = []
    entity_map: dict[str, str] = {}
    seen_keys: set[tuple[str, str]] = set()

    def _add_payload(obj_type: str, val: str, entity_ident: str) -> None:
        key = (obj_type, val)
        if key in seen_keys:
            return
        seen_keys.add(key)
        item: SingleJson = {obj_type: val}
        if include_description and description:
            item["description"] = description
        payloads.append(item)
        entity_map[val] = entity_ident

    # 1. Process entities in scope
    for entity in suitable_entities:
        extracted = _extract_entity_object(entity, siemplify)
        if extracted:
            obj_type, val, entity_ident = extracted
            _add_payload(obj_type, val, entity_ident)

    # 2. Process manual free-text parameter inputs
    for obj_type, val, raw_ident in _extract_manual_parameter_objects(siemplify):
        _add_payload(obj_type, val, raw_ident)

    return payloads, entity_map
