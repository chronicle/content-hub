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

from enum import Enum
from typing import Any

from ..core.MISPManager import (
    MISPManager,
    URL,
    HOSTNAME,
    DOMAIN,
    USER,
    EMAIL_SUBJECT,
    THREAT_ACTOR,
    PHONE_NUMBER,
    FILENAME,
)
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    output_handler,
    unix_now,
    convert_unixtime_to_datetime,
)
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from ..core.constants import (
    ADD_ATTRIBUTE_SCRIPT_NAME,
    INTEGRATION_NAME,
    ATTRIBUTES_EXISTING_CATEGORY_TYPES,
    FALLBACK_IP_TYPES_MAPPER,
    FALLBACK_EMAIL_TYPES_MAPPER,
    COMMUNITY,
    ATTRIBUTE_DISTRIBUTION,
    IP_TYPES,
    EMAIL_TYPES,
    EMAIL_TYPE,
    DOMAIN_TYPE,
)
from ..core.exceptions import (
    MISPManagerError,
    MISPManagerInvalidCategoryError,
    MISPManagerEventIdNotFoundError,
    MISPNotAcceptableNumberOrStringError,
)
from ..core.utils import (
    get_hash_type,
    get_domain_from_entity,
    get_entity_original_identifier,
    get_entity_type,
)
from ..core.utils import adjust_categories
import re


class ExecutionScope(Enum):
    ExecutionScopeUnspecified = 0
    Alert = 1
    Case = 2


SUITABLE_ENTITY_TYPES = [
    EntityTypes.HOSTNAME,
    EntityTypes.URL,
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
    EntityTypes.USER,
    EntityTypes.FILENAME,
    EntityTypes.EMAILMESSAGE,
    EntityTypes.THREATCAMPAIGN,
    EntityTypes.THREATACTOR,
    EntityTypes.PHONENUMBER,
]


def is_src(alert, identifier):
    for relation in alert.relations:
        if relation.from_identifier == identifier:
            return True


def is_dst(alert, identifier):
    for relation in alert.relations:
        if relation.to_identifier == identifier:
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


def get_entity_type_for_request(
    alert_obj: Any,
    entity: Any,
    identifier: str,
    extract_domain: bool,
    entity_type_mapper: dict[str, str],
) -> str | None:
    """Get the corresponding MISP entity type for a specific request.

    Args:
        alert_obj: The alert object (current alert or alert from case).
        entity: The entity object.
        identifier: The entity identifier.
        extract_domain: Whether to extract domain from URL.
        entity_type_mapper: A dictionary mapping entity types to MISP types.

    Returns:
        The MISP entity type or None if not identified.
    """
    entity_type = entity_type_mapper.get(get_entity_type(entity, extract_domain))

    if (
        entity.entity_type == EntityTypes.HOSTNAME
        or entity.entity_type == DOMAIN_TYPE
    ):
        entity_type = (
            entity_type
            if is_valid_domain(identifier)
            else entity_type_mapper.get(EntityTypes.USER)
        )

    if entity.entity_type == EntityTypes.ADDRESS:
        if alert_obj.relations:
            if is_src(alert_obj, identifier):
                entity_type = IP_TYPES[FALLBACK_IP_TYPES_MAPPER["ip-src"]]
            if is_dst(alert_obj, identifier):
                entity_type = IP_TYPES[FALLBACK_IP_TYPES_MAPPER["ip-dst"]]

    if entity.entity_type == EMAIL_TYPE:
        if alert_obj.relations:
            if is_src(alert_obj, identifier):
                entity_type = FALLBACK_EMAIL_TYPES_MAPPER["email-src"]
            if is_dst(alert_obj, identifier):
                entity_type = FALLBACK_IP_TYPES_MAPPER["email-dst"]

    if not entity_type and entity.entity_type == EntityTypes.FILEHASH:
        entity_type = get_hash_type(identifier)

    return entity_type


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_ATTRIBUTE_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Root"
    )
    api_token = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use SSL",
        default_value=False,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )

    event_id = extract_action_param(
        siemplify, param_name="Event ID", is_mandatory=True, print_value=True
    )
    category = adjust_categories(
        extract_action_param(siemplify, param_name="Category", print_value=True)
    )
    distribution = extract_action_param(
        siemplify,
        param_name="Distribution",
        print_value=True,
        default_value=COMMUNITY,
    )
    to_ids = extract_action_param(
        siemplify,
        param_name="For Intrusion Detection System",
        print_value=True,
        input_type=bool,
        default_value=False,
    )
    comment = extract_action_param(
        siemplify, param_name="Comment", print_value=True
    )
    fallback_ip_type = extract_action_param(
        siemplify,
        param_name="Fallback IP Type",
        print_value=True,
        default_value=FALLBACK_IP_TYPES_MAPPER["ip-src"],
    )
    fallback_email_type = extract_action_param(
        siemplify,
        param_name="Fallback Email Type",
        print_value=True,
        default_value=FALLBACK_EMAIL_TYPES_MAPPER["email-src"],
    )
    extract_domain = extract_action_param(
        siemplify,
        param_name="Extract Domain",
        print_value=True,
        input_type=bool,
        default_value=True,
    )
    id_type = "ID" if event_id.isdigit() else "UUID"

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    successful_entities, failed_entities, json_results = [], [], []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUITABLE_ENTITY_TYPES
    ]

    entity_type_mapper = {
        EntityTypes.HOSTNAME: HOSTNAME,
        EntityTypes.URL: URL,
        EntityTypes.FILEHASH: "",
        EntityTypes.ADDRESS: IP_TYPES[fallback_ip_type],
        EntityTypes.USER: USER,
        EntityTypes.FILENAME: FILENAME,
        EntityTypes.EMAILMESSAGE: EMAIL_SUBJECT,
        EntityTypes.THREATCAMPAIGN: THREAT_ACTOR,
        EntityTypes.THREATACTOR: THREAT_ACTOR,
        EntityTypes.PHONENUMBER: PHONE_NUMBER,
        EMAIL_TYPE: EMAIL_TYPES[fallback_email_type],
        DOMAIN_TYPE: DOMAIN,
    }

    try:
        if distribution.lower() not in map(
            str,
            tuple(ATTRIBUTE_DISTRIBUTION.keys())
            + tuple(ATTRIBUTE_DISTRIBUTION.values()),
        ):
            raise MISPNotAcceptableNumberOrStringError(
                "Distribution",
                acceptable_strings=ATTRIBUTE_DISTRIBUTION.keys(),
                acceptable_numbers=ATTRIBUTE_DISTRIBUTION.values(),
            )
        distribution = int(
            ATTRIBUTE_DISTRIBUTION[distribution.lower()]
            if not distribution.isdigit()
            else distribution
        )

        if category and category.lower() not in ATTRIBUTES_EXISTING_CATEGORY_TYPES:
            raise MISPManagerInvalidCategoryError(
                'Invalid value was provided for the parameter "Category".'
                "Acceptable values: {}.".format(
                    ", ".join(
                        [
                            category.capitalize()
                            for category in ATTRIBUTES_EXISTING_CATEGORY_TYPES
                        ]
                    )
                )
            )

        manager = MISPManager(api_root, api_token, use_ssl, ca_certificate)
        event_id = manager.get_event_by_id_or_raise(event_id).id

        def _process_alert_entities(
            alert_obj: Any,
            entities_to_process: list[Any],
        ) -> int:
            for entity in entities_to_process:
                if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                    deadline_str = convert_unixtime_to_datetime(
                        siemplify.execution_deadline_unix_time_ms
                    )
                    siemplify.LOGGER.error(
                        f"Timed out. execution deadline ({deadline_str}) has passed"
                    )
                    return EXECUTION_STATE_TIMEDOUT

                identifier = (
                    get_entity_original_identifier(entity)
                    if not (
                        extract_domain and entity.entity_type == EntityTypes.URL
                    )
                    else get_domain_from_entity(
                        get_entity_original_identifier(entity)
                    )
                )

                entity_type = get_entity_type_for_request(
                    alert_obj,
                    entity,
                    identifier,
                    extract_domain,
                    entity_type_mapper,
                )
                try:
                    siemplify.LOGGER.info(
                        f"Started processing entity: {identifier}"
                    )
                    siemplify.LOGGER.info(
                        f"Adding {identifier} attribute for event {event_id}"
                    )

                    if entity_type:
                        attribute = manager.add_attribute(
                            event_id=event_id,
                            value=identifier,
                            type=entity_type,
                            category=category,
                            to_ids=to_ids,
                            distribution=distribution,
                            comment=comment,
                        )
                        json_results.append(attribute)
                        successful_entities.append(identifier)
                    else:
                        failed_entities.append(identifier)
                    siemplify.LOGGER.info(
                        f"Finished processing entity {identifier}"
                    )

                except MISPManagerError as e:
                    failed_entities.append(identifier)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity: {identifier}.\n{e}."
                    )
                    siemplify.LOGGER.exception(e)

            return EXECUTION_STATE_COMPLETED

        execution_scope = getattr(
            siemplify,
            "execution_scope",
            ExecutionScope.Alert,
        )

        status: int = EXECUTION_STATE_COMPLETED

        if execution_scope.value == ExecutionScope.Alert.value:
            siemplify.LOGGER.info("Processing in Alert scope.")
            status = _process_alert_entities(
                siemplify.current_alert,
                suitable_entities,
            )
        else:
            siemplify.LOGGER.info("Processing in Case scope.")
            for alert_obj in getattr(
                siemplify.case, "open_alerts", siemplify.case.alerts
            ):
                alert_entities: list = [
                    entity
                    for entity in alert_obj.entities
                    if entity.entity_type in SUITABLE_ENTITY_TYPES
                ]
                status = _process_alert_entities(alert_obj, alert_entities)
                if status == EXECUTION_STATE_TIMEDOUT:
                    break

        if json_results:
            siemplify.result.add_result_json(
                [{"Attribute": result.as_json()} for result in json_results]
            )

        if execution_scope.value == ExecutionScope.Alert.value:
            if successful_entities:
                output_message += (
                    "Successfully added the following attributes based on "
                    "entities to the event with "
                    f"{id_type} {event_id} in {INTEGRATION_NAME}: \n"
                    f" {', '.join(sorted(set(successful_entities)))} \n"
                )

            if failed_entities:
                output_message += (
                    "Action wasn’t able to add the following attributes based "
                    "on entities to the event "
                    f"with {id_type} {event_id} in {INTEGRATION_NAME}: \n"
                    f" {', '.join(sorted(set(failed_entities)))} \n"
                )

            if not successful_entities:
                output_message = (
                    "No attributes based on entities were added to the event "
                    f"with {id_type} {event_id} in {INTEGRATION_NAME}"
                )
                result_value = False
        else:
            if successful_entities:
                output_message += (
                    "Successfully added the following attributes based on "
                    "entities to the event with "
                    f"{id_type} {event_id} in {INTEGRATION_NAME} for all "
                    f"alert(s) in case {siemplify.case_id}: \n"
                    f" {', '.join(sorted(set(successful_entities)))} \n"
                )

            if failed_entities:
                output_message += (
                    "Action wasn’t able to add the following attributes based "
                    "on entities to the event "
                    f"with {id_type} {event_id} in {INTEGRATION_NAME} for all "
                    f"alert(s) in case {siemplify.case_id}: \n"
                    f" {', '.join(sorted(set(failed_entities)))} \n"
                )

            if not successful_entities:
                output_message = (
                    "No attributes based on entities were added to the event "
                    f"with {id_type} {event_id} in {INTEGRATION_NAME} for all "
                    f"alert(s) in case {siemplify.case_id}"
                )
                result_value = False

    except Exception as e:
        output_message = (
            f"Error executing action {ADD_ATTRIBUTE_SCRIPT_NAME}. Reason: "
        )
        output_message += (
            f"Event with {id_type} {event_id} was not found in {INTEGRATION_NAME}"
            if isinstance(e, MISPManagerEventIdNotFoundError)
            else str(e)
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n"
        f"  result_value: {result_value}\n"
        f"  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
