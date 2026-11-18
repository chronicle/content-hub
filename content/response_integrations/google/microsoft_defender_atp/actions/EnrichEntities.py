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

from typing import TYPE_CHECKING

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import add_prefix_to_dict, convert_dict_to_json_result_dict, output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    ENRICH_ENTITIES_SCRIPT_NAME,
    ENRICH_ENTITY_TYPES,
    LOGIN_API_ROOT_DEFAULT,
    PROVIDER_NAME,
    ErrorType,
)
from ..core.exceptions import DefenderException, DefenderNotFoundException
from ..core.MicrosoftDefenderATPManager import MicrosoftDefenderATPError, MicrosoftDefenderATPManager
from ..core.UtilsManager import (
    ActionResultSummaryInput,
    classify_exception,
    get_summary_scope,
    log_action_result_summary,
)

if TYPE_CHECKING:
    from soar_sdk.SiemplifyLogger import SiemplifyLogger
    from TIPCommon.types import SingleJson

    from ..core.datamodels import Machine


def _enrich_machine_isolation_status(
    manager: MicrosoftDefenderATPManager,
    machine: Machine,
    logger: SiemplifyLogger,
) -> None:
    """Enrich a machine with its isolation status and is_isolated flag.

    Args:
        manager: Defender manager instance.
        machine: Target machine to enrich.
        logger: Siemplify logger for recording warnings.
    """
    try:
        machine.isolation_status, machine.is_isolated = manager.get_machine_isolation_status(machine.id)
    except Exception as error:
        logger.warn(f"Failed to get the isolation status of machine {machine.id}: {error}")


def _record_enriched_machine(
    siemplify: SiemplifyAction,
    manager: MicrosoftDefenderATPManager,
    machine: Machine,
    machine_id: str,
) -> SingleJson:
    """Enrich a machine with its isolation status and attach it to the action result.

    Args:
        siemplify: SiemplifyAction instance for action results.
        manager: Defender manager instance.
        machine: Machine found for the Machine ID.
        machine_id: Machine ID that keys the entity result.

    Returns:
        The JSON data of the enriched machine.
    """
    _enrich_machine_isolation_status(manager, machine, siemplify.LOGGER)
    json_data = machine.to_json()
    siemplify.result.add_entity_json(entity_identifier=machine_id, json_data=json_data)
    siemplify.result.add_entity_table(entity_identifier=machine_id, data_table=construct_csv([machine.to_table()]))

    return json_data


def _enrich_by_machine_id(
    siemplify: SiemplifyAction,
    manager: MicrosoftDefenderATPManager,
    machine_id: str,
) -> tuple[dict[str, SingleJson], list[str], str, str | None]:
    """Enrich a machine directly by Machine ID, skipping the entity loop.

    Args:
        siemplify: SiemplifyAction instance for action results.
        manager: Defender manager instance.
        machine_id: Target machine ID to look up and enrich.

    Returns:
        Tuple of (json_result, output_messages, result, error_type), where error_type is None on success.
    """
    try:
        found_machine = manager.get_machine_by_id(machine_id)
    except DefenderNotFoundException:
        siemplify.LOGGER.info(f"Machine ID {machine_id} was not enriched because nothing was found")
        messages = [
            "0 entities enriched",
            "1 entities missed",
            "0 entities failed",
            f"Missing Entities: {machine_id}",
            "Failed Entities: ",
            "No entities were enriched",
        ]
        return {}, messages, "false", ErrorType.ENDPOINT_NOT_FOUND
    except (MicrosoftDefenderATPError, DefenderException) as error:
        siemplify.LOGGER.exception(f"Failed to enrich Machine ID {machine_id}: {error}")
        messages = [
            "0 entities enriched",
            "0 entities missed",
            "1 entities failed",
            f"Failed Entities: {machine_id}",
            "No entities were enriched",
        ]
        return {}, messages, "false", classify_exception(error)[0]

    json_result = {machine_id: _record_enriched_machine(siemplify, manager, found_machine, machine_id)}
    messages = [
        "1 entities enriched",
        "0 entities missed",
        "0 entities failed",
        f"Enriched Entities: {machine_id}",
        "Missing Entities: ",
        "Failed Entities: ",
    ]

    return json_result, messages, "true", None


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Login API Root",
        default_value=LOGIN_API_ROOT_DEFAULT,
        is_mandatory=True,
    )

    api_root = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Api Root", input_type=str
    )

    client_id = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Client ID", input_type=str
    )

    client_secret = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client Secret",
        input_type=str,
    )

    tenant_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Azure Active Directory ID",
        input_type=str,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )

    machine_id: str | None = extract_action_param(siemplify, param_name="Machine ID", print_value=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_result = {}
    failed_entities = []
    missing_entities = []
    enriched_entities = []
    target_results: dict[str, str | None] = {}
    error: Exception | None = None

    try:
        microsoft_defender_atp = MicrosoftDefenderATPManager(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            resource=api_root,
            login_api_root=login_api_root,
            verify_ssl=verify_ssl,
        )

        for entity in [] if machine_id else siemplify.target_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            if entity.entity_type in [EntityTypes.HOSTNAME, EntityTypes.ADDRESS]:
                if entity.entity_type == EntityTypes.HOSTNAME:
                    machines = microsoft_defender_atp.get_machines_by_name(
                        starts_with_name=entity.identifier
                    )
                else:
                    machines = microsoft_defender_atp.get_machines(ip=entity.identifier)

                if machines:
                    found_machine = machines[-1]
                    _enrich_machine_isolation_status(microsoft_defender_atp, found_machine, siemplify.LOGGER)

                    enrichment_data = add_prefix_to_dict(
                        found_machine.to_enrichment_data(), "Defender ATP"
                    )
                    entity.additional_properties.update(enrichment_data)
                    entity.is_enriched = True

                    enriched_entities.append(entity)
                    target_results[entity.identifier] = None

                    json_result[entity.identifier] = found_machine.to_json()
                    siemplify.result.add_entity_json(
                        entity_identifier=entity.identifier,
                        json_data=found_machine.to_json(),
                    )

                    siemplify.result.add_entity_table(
                        entity_identifier=entity.identifier,
                        data_table=construct_csv([found_machine.to_table()]),
                    )
                else:
                    missing_entities.append(entity)
                    target_results[entity.identifier] = ErrorType.ENDPOINT_NOT_FOUND
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} was not enriched because nothing was found"
                    )

            elif entity.entity_type == EntityTypes.FILEHASH:
                try:
                    file_data = microsoft_defender_atp.get_file(entity.identifier)
                    enrichment_data = add_prefix_to_dict(
                        file_data.to_enrichment_data(), "Defender ATP"
                    )
                    entity.additional_properties.update(enrichment_data)
                    entity.is_enriched = True

                    enriched_entities.append(entity)
                    target_results[entity.identifier] = None

                    json_result[entity.identifier] = file_data.to_json()
                    siemplify.result.add_entity_json(
                        entity_identifier=entity.identifier,
                        json_data=file_data.to_json(),
                    )

                    siemplify.result.add_entity_table(
                        entity_identifier=entity.identifier,
                        data_table=construct_csv([file_data.to_table()]),
                    )
                except MicrosoftDefenderATPError as e:
                    siemplify.LOGGER.error(e)
                    siemplify.LOGGER.exception(e)
                    failed_entities.append(entity)
                    target_results[entity.identifier] = classify_exception(e)[0]

            else:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type, skipping..."
                )

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        output_messages = [
            f"{len(enriched_entities)} entities enriched",
            f"{len(missing_entities)} entities missed",
            f"{len(failed_entities)} entities failed",
        ]

        if enriched_entities:
            siemplify.update_entities(enriched_entities)

            output_messages.append(
                f"Enriched Entities: {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string( [entity.identifier for entity in enriched_entities] )}"
            )

            output_messages.append(
                f"Missing Entities: {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string( [entity.identifier for entity in missing_entities] )}"
            )

            failed_names = MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(
                [entity.identifier for entity in failed_entities],
            )
            output_messages.append(f"Failed Entities: {failed_names}")

            result = "true"
        elif not machine_id:
            output_messages.append("No entities were enriched")
            result = "false"
            siemplify.LOGGER.warn("No entities were enriched")

        if machine_id:
            json_result, output_messages, result, error_type = _enrich_by_machine_id(
                siemplify,
                microsoft_defender_atp,
                machine_id,
            )
            target_results = {machine_id: error_type}

        status = EXECUTION_STATE_COMPLETED
        output_message = "\n".join(output_messages)

    except MicrosoftDefenderATPError as e:
        error = e
        output_message = f"Action didn't completed due to error: {e}"
        result = "false"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        error = e
        log_action_result_summary(
            siemplify.LOGGER,
            lambda: ActionResultSummaryInput(
                execution_state=EXECUTION_STATE_FAILED,
                target_results=target_results,
                skipped=(s := get_summary_scope(siemplify.target_entities, ENRICH_ENTITY_TYPES, machine_id))[1],
                unfinished=max(s[0] - len(target_results), 0),
                error=error,
            ),
        )
        raise

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
    log_action_result_summary(
        siemplify.LOGGER,
        lambda: ActionResultSummaryInput(
            execution_state=status,
            target_results=target_results,
            skipped=(s := get_summary_scope(siemplify.target_entities, ENRICH_ENTITY_TYPES, machine_id))[1],
            unfinished=max(s[0] - len(target_results), 0) if error else 0,
            error=error,
        ),
    )
    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
