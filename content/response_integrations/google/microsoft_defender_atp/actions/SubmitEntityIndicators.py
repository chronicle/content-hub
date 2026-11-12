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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.extraction import extract_configuration_param, extract_action_param

from ..core.constants import (
    SHA256_LENGTH,
    MD5_LENGTH,
    SHA1_LENGTH,
    ACTION_PARAM_MAPPING,
    LOGIN_API_ROOT_DEFAULT,
    PROVIDER_NAME,
    SUBMIT_ENTITY_INDICATORS_SCRIPT_NAME,
)
from ..core.MicrosoftDefenderATPManager import (
    MicrosoftDefenderATPManager,
    MicrosoftDefenderATPError,
    MicrosoftDefenderATPForbiddenError,
)
from ..core.UtilsManager import is_valid_domain, get_entity_original_identifier

SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.FILEHASH, EntityTypes.URL]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SUBMIT_ENTITY_INDICATORS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Login API Root",
        default_value=LOGIN_API_ROOT_DEFAULT,
        is_mandatory=True,
    )

    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Api Root",
        input_type=str,
        is_mandatory=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client ID",
        input_type=str,
        is_mandatory=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client Secret",
        input_type=str,
        is_mandatory=True,
    )
    tenant_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Azure Active Directory ID",
        input_type=str,
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        default_value=False,
    )

    action = extract_action_param(
        siemplify, param_name="Action", input_type=str, is_mandatory=True
    )
    severity = extract_action_param(
        siemplify, param_name="Severity", input_type=str, is_mandatory=True
    )
    application = extract_action_param(
        siemplify, param_name="Application", input_type=str, is_mandatory=False
    )
    alert_title = extract_action_param(
        siemplify, param_name="Indicator Alert Title", input_type=str, is_mandatory=True
    )
    description = extract_action_param(
        siemplify, param_name="Description", input_type=str, is_mandatory=True
    )
    recommended_action = extract_action_param(
        siemplify, param_name="Recommended Action", input_type=str, is_mandatory=False
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_messages = []
    submitted_entities = []
    failed_entities = []
    existing_entities = []
    forbidden_entities = []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITIES
    ]

    try:
        microsoft_defender_atp = MicrosoftDefenderATPManager(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            resource=api_root,
            login_api_root=login_api_root,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
            entities_scope=True,
        )

        existing_indicators = [
            indicator.indicator_value.lower()
            for indicator in microsoft_defender_atp.get_entities(
                entities=[
                    get_entity_original_identifier(entity)
                    for entity in suitable_entities
                ]
            )
        ]

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity {entity.identifier}")
            entity_identifier = get_entity_original_identifier(entity)
            entity_type = None
            if entity.entity_type == EntityTypes.FILEHASH:
                if len(entity_identifier) == SHA256_LENGTH:
                    entity_type = "FileSha256"
                elif len(entity_identifier) == MD5_LENGTH:
                    entity_type = "FileMd5"
                elif len(entity_identifier) == SHA1_LENGTH:
                    entity_type = "FileSha1"
                else:
                    siemplify.LOGGER.error(
                        "Not supported hash type. Provide either MD5, SHA-256 or SHA-1."
                    )
                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity.identifier}"
                    )
                    continue
            elif entity.entity_type == EntityTypes.ADDRESS:
                entity_type = "IpAddress"
            elif entity.entity_type == EntityTypes.URL:
                if is_valid_domain(entity_identifier):
                    entity_type = "DomainName"
                else:
                    entity_type = "Url"

            if entity_identifier.lower() in existing_indicators:
                existing_entities.append(entity)
            else:
                try:
                    microsoft_defender_atp.submit_entity(
                        entity_identifier=entity_identifier,
                        entity_type=entity_type,
                        title=alert_title,
                        action=ACTION_PARAM_MAPPING.get(action),
                        application=application,
                        severity=severity,
                        description=description,
                        recommended_action=recommended_action,
                    )
                    submitted_entities.append(entity)

                except MicrosoftDefenderATPForbiddenError:
                    forbidden_entities.append(entity)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity: {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(
                        "Instance doesn't have enough permissions to submit the entity."
                    )
                except MicrosoftDefenderATPError as e:
                    failed_entities.append(entity)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity: {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)
            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if submitted_entities:
            output_messages.append(
                "Successfully submitted the following entities as indicators to Microsoft Defender "
                "ATP: {}".format(
                    MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(
                        [entity.identifier for entity in submitted_entities]
                    )
                )
            )

        if failed_entities:
            output_messages.append(
                "Action wasn't able to submit the following entities as indicators to Microsoft Defender "
                "ATP: {}".format(
                    MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(
                        [entity.identifier for entity in failed_entities]
                    )
                )
            )

        if forbidden_entities:
            output_messages.append(
                f"Instance doesn't have enough permissions to submit for the following entities: {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string([entity.identifier for entity in forbidden_entities])}"
            )

        if existing_entities:
            output_messages.append(
                "The following entities are already indicators in Microsoft Defender "
                "ATP: {}".format(
                    MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(
                        [entity.identifier for entity in existing_entities]
                    )
                )
            )

        if not submitted_entities and not existing_entities:
            result_value = False
            if forbidden_entities and not failed_entities:
                raise MicrosoftDefenderATPError(
                    "none of the indicators were created due to instance permissions, "
                    "please check the configuration."
                )
            elif not forbidden_entities:
                output_messages = [
                    "None of the provided entities were submitted as indicators to Microsoft "
                    "Defender ATP."
                ]

        output_message = "\n".join(output_messages)

    except MicrosoftDefenderATPError as e:
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
