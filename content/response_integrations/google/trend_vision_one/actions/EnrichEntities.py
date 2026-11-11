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

import dataclasses
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyDataModel import EntityTypes, DomainEntityInfo
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import (
    add_prefix_to_dict,
    extract_action_param,
    extract_configuration_param,
    flat_dict_to_csv,
    string_to_multi_value,
)
from ..core.TrendVisionOneManager import TrendVisionOneManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    ENRICH_ENTITIES_SCRIPT_NAME,
    ENRICHMENT_PREFIX,
    ENDPOINT_NOT_FOUND_MESSAGE,
)
from ..core.datamodels import Endpoint
from ..core.UtilsManager import (
    ErrorType,
    classify_exception,
    count_skipped_entities,
    get_endpoint_search_args,
    get_entity_original_identifier,
    log_action_result_summary,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]
ISOLATION_STATUS_KEY = "isolationStatus"
UNKNOWN_ISOLATION_STATUS = "unknown"


def get_target_identifier(target: DomainEntityInfo | str) -> str:
    """Get the identifier of a target.

    Args:
        target: The entity or Agent UUID.

    Returns:
        The Agent UUID, or the original identifier of the entity.
    """
    return target if isinstance(target, str) else get_entity_original_identifier(target)


@dataclasses.dataclass(slots=True)
class EnrichmentResult:
    """Outcome of the enrichment of all targets."""

    successful: list[DomainEntityInfo | Endpoint] = dataclasses.field(default_factory=list)
    failed: list[DomainEntityInfo | str] = dataclasses.field(default_factory=list)
    json_result: SingleJson = dataclasses.field(default_factory=dict)
    error_types: list[str] = dataclasses.field(default_factory=list)

    def add_failure(self, target: DomainEntityInfo | str, identifier: str, error: str, error_type: str) -> None:
        """Record a failed target in the failed list and in the JSON result.

        Args:
            target: The entity or Agent UUID that failed.
            identifier: The identifier of the target in the JSON result.
            error: The failure message.
            error_type: The failure reason.
        """
        self.failed.append(target)
        self.error_types.append(error_type)
        self.json_result[identifier] = {"error": error, "error_type": error_type}

    def add_run_error(self, targets: list[DomainEntityInfo | str], error: Exception) -> None:
        """Record a run error as a failure of each target that has no JSON result yet.

        Args:
            targets: The supported entities, then the Agent UUIDs.
            error: The exception that ended the run.
        """
        error_type = classify_exception(error)[0]
        for target in targets:
            identifier = get_target_identifier(target)
            if identifier not in self.json_result:
                self.add_failure(target, identifier, str(error), error_type)


def get_entities_list(entities_list: list[DomainEntityInfo | str]) -> list[str]:
    """Get a list of entity identifiers from a list of entities.

    Args:
        entities_list (list[DomainEntityInfo | str]): The list of entities.

    Returns:
        list[str]: A list of entity identifiers.
    """
    entities = []
    for entity in entities_list:
        if isinstance(entity, DomainEntityInfo):
            entities.append(entity.identifier)
        elif isinstance(entity, Endpoint):
            entities.append(entity.guid)
        else:
            entities.append(entity)

    return entities


def get_isolation_status(siemplify: SiemplifyAction, manager: TrendVisionOneManager, agent_guid: str) -> str:
    """Get the isolation status of an endpoint. Never fail the target if the lookup fails.

    Args:
        siemplify: The action object.
        manager: The Trend Vision One manager.
        agent_guid: The agent GUID of the endpoint.

    Returns:
        The isolation status, or unknown if the API has no value or the lookup fails.
    """
    try:
        return manager.get_endpoint_isolation_status(agent_guid) or UNKNOWN_ISOLATION_STATUS
    except Exception as e:
        siemplify.LOGGER.exception(f"Unable to get the isolation status of endpoint {agent_guid}. Reason: {e}")

        return UNKNOWN_ISOLATION_STATUS


def enrich_entity(
    siemplify: SiemplifyAction,
    entity: DomainEntityInfo,
    identifier: str,
    endpoint: Endpoint,
    isolation_status: str,
) -> None:
    """Add the endpoint data and isolation status to the entity and to its entity table.

    Args:
        siemplify: The action object.
        entity: The entity to enrich.
        identifier: The original identifier of the entity.
        endpoint: The endpoint of the entity.
        isolation_status: The isolation status of the endpoint.
    """
    siemplify.LOGGER.info(f"Enriching entity {identifier}")
    isolation = {ISOLATION_STATUS_KEY: isolation_status}
    entity.additional_properties.update(endpoint.to_enrichment_data(prefix=ENRICHMENT_PREFIX))
    entity.additional_properties.update(add_prefix_to_dict(isolation, ENRICHMENT_PREFIX))
    entity.is_enriched = True
    siemplify.result.add_entity_table(identifier, flat_dict_to_csv({**endpoint.to_table(), **isolation}))


def enrich_targets(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    targets: list[DomainEntityInfo | str],
) -> EnrichmentResult:
    """Enrich each entity and Agent UUID. A failed target does not stop the others.

    Args:
        siemplify: The action object.
        manager: The Trend Vision One manager.
        targets: The supported entities, then the Agent UUIDs.

    Returns:
        The successful and failed targets, the JSON result, and the failure reasons.
    """
    result = EnrichmentResult()
    for target in targets:
        is_agent = isinstance(target, str)
        identifier = get_target_identifier(target)
        try:
            siemplify.LOGGER.info(f"Started processing entity: {identifier}")
            endpoint = manager.search_endpoint(**get_endpoint_search_args(target))
            if endpoint:
                isolation_status = get_isolation_status(siemplify, manager, endpoint.guid)
                if not is_agent:
                    enrich_entity(siemplify, target, identifier, endpoint, isolation_status)
                result.successful.append(endpoint if is_agent else target)
                json_key = endpoint.guid if is_agent else identifier
                result.json_result[json_key] = {**endpoint.to_json(), ISOLATION_STATUS_KEY: isolation_status}
            else:
                result.add_failure(target, identifier, ENDPOINT_NOT_FOUND_MESSAGE, ErrorType.ENDPOINT_NOT_FOUND)
            siemplify.LOGGER.info(f"Finish processing entity: {identifier}")
        except Exception as e:
            siemplify.LOGGER.exception(f"An error occurred on entity: {identifier}. Reason: {e}")
            result.add_failure(target, identifier, str(e), classify_exception(e)[0])

    return result


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    agent_uuids = string_to_multi_value(
        extract_action_param(
            siemplify,
            param_name="Agent UUID",
            print_value=True,
        ),
        only_unique=True,
    )

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result = EnrichmentResult()
    error = None

    try:
        manager = TrendVisionOneManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )
        manager.test_connectivity()

        result = enrich_targets(siemplify, manager, [*suitable_entities, *agent_uuids])
        successful_entities, failed_entities = result.successful, result.failed
        if successful_entities:
            output_message += (
                f"Successfully enriched the following entities using information from "
                f"{INTEGRATION_DISPLAY_NAME}: "
                f"{', '.join(get_entities_list(successful_entities))}\n\n"
            )
            siemplify.update_entities(
                [
                    entity
                    for entity in successful_entities
                    if isinstance(entity, DomainEntityInfo)
                ]
            )

            if failed_entities:
                output_message += (
                    f"Action wasn't able to enrich the following entities using information from"
                    f" {INTEGRATION_DISPLAY_NAME}: "
                    f"{', '.join(get_entities_list(failed_entities))}\n"
                )
        else:
            output_message = "None of the provided entities were enriched."
            result_value = False
        if result.json_result:
            siemplify.result.add_result_json(convert_dict_to_json_result_dict(result.json_result))

    except Exception as e:
        error = e
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {ENRICH_ENTITIES_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result.add_run_error([*suitable_entities, *agent_uuids], e)
        if result.json_result:
            siemplify.result.add_result_json(convert_dict_to_json_result_dict(result.json_result))

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    log_action_result_summary(
        siemplify,
        status,
        lambda: (
            len(suitable_entities) + len(agent_uuids),
            len(result.successful),
            result.error_types,
            count_skipped_entities(siemplify.target_entities, SUPPORTED_ENTITY_TYPES),
        ),
        error=error,
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
