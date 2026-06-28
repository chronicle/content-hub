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
import json
from collections import defaultdict

from TIPCommon.types import SingleJson
from vertex_ai.core.VertexAIExceptions import VertexAIInvalidJsonException

EXCLUDE_ENTITY_FIELDS = [
    # Entity fields
    "caseId",
    "isArtifact",
    "isEnriched",
    "isVulnerable",
    "isPivot",
    # Field group fields
    "Type",
    "Environment",
    "OriginalIdentifier",
    "IsInternalAsset",
    "IsSuspicious",
    "IsEnriched",
    "IsVulnerable",
    "IsArtifact",
    "IsTestCase",
    "Network_Priority",
    "IsAttacker",
    "Alert_Id",
    "SourceSystemUrl",
    "IsManuallyCreated",
]


def parse_string_to_dict(string: str) -> SingleJson:
    """Parse json string to dict.

    Args:
        string: string to parse

    Raises:
        GoogleCloudApiInvalidJsonException: If provided JSON string is invalid

    Returns:
        SingleJson: parsed dict

    """
    try:
        return json.loads(string)
    except Exception as err:
        raise VertexAIInvalidJsonException(
            f"Unable to parse provided json. Error is: {err}",
        ) from err


def flatten_entity_data_for_generation(entity_data: SingleJson) -> SingleJson:
    """Flatten entity JSON for generation."""
    flattened_entity_data = {}
    entity = copy.deepcopy(entity_data["entity"])
    field_groups = entity.pop("fields", [])

    allowed_names = {"Default", "Raw Enrichment"}
    for field_group in field_groups:
        group_name_val = field_group.get("groupName")
        display_name_val = field_group.get("displayName")

        if (group_name_val not in allowed_names) and (
            display_name_val not in allowed_names
        ):
            continue

        for field in field_group.get("items", []):
            entity[field.get("originalName")] = field.get("value")

    flattened_entity_data["entity"] = entity

    exclude_fields_from_entity(flattened_entity_data, keys=EXCLUDE_ENTITY_FIELDS)

    flattened_entity_data["affectedEnvironments"] = copy.deepcopy(
        entity_data.get("entityEnvironmentsList", [])
        or entity_data.get("environments", []),
    )

    related_entities = defaultdict(list)
    for ent in entity_data.get("linkedEntities", []):
        entity_type = ent.get("entityType") or ent.get("type")
        if entity_type:
            related_entities[entity_type].append(ent["identifier"])

    flattened_entity_data["relatedEntities"] = related_entities
    return flattened_entity_data


def exclude_fields_from_entity(entity: SingleJson, keys: list[str]) -> SingleJson:
    """Exclude keys from dictionary."""
    _exact_match_keys = set()
    _partial_match_keys = []
    for key in keys:
        if key.endswith("*"):
            _partial_match_keys.append(key)
            continue

        _exact_match_keys.add(key)

    _exclude_fields(entity, _exact_match_keys, _partial_match_keys)
    return entity


def _match_key(
    key_: str, exact_match_keys: set[str], partial_match_keys: list[str],
) -> bool:
    """Check if key matches exact or partial matches."""
    if key_ in exact_match_keys:
        return True

    for prefix in partial_match_keys:
        if key_.startswith(prefix[:-1]):
            return True

    return False


def _exclude_fields(
    entity: SingleJson,
    exact_match_keys: set[str],
    partial_match_keys: list[str],
) -> None:
    """Exclude keys from dictionary internal recursive callable."""
    for field, value in entity.copy().items():
        if _match_key(field, exact_match_keys, partial_match_keys):
            del entity[field]
            continue

        if isinstance(value, dict):
            _exclude_fields(value, exact_match_keys, partial_match_keys)


def get_publisher_name(input_publisher_name: str, default_publisher: str) -> str:
    """Returns the normalized publisher name in lowercase.
    If no input is provided, default to default.

    Args:
        input_publisher_name: The input publisher name.
        default_publisher: The default publisher configured in action params.

    Return:
        str: Normalized publisher name in lowercase if provided,
        otherwise default publisher.

    """
    return (input_publisher_name or default_publisher).lower()
