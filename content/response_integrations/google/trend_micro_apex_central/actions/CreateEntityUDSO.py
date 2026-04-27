from __future__ import annotations
import datetime
from urllib.parse import urlparse

import validators
from TIPCommon import extract_configuration_param, extract_action_param

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, utc_now, convert_dict_to_json_result_dict
from ..core.TrendMicroApexCentralManager import TrendMicroApexCentralManager
from ..core.consts import (
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_IDENTIFIER,
    CREATE_ENTITY_UDSO_SCRIPT_NAME,
    DEFAULT_SCAN_ACTION,
    SHA1_HASH_LENGTH,
    ENTITY_TYPE_TO_UDSO_TYPE,
    MAX_UDSO_NOTES_CHARACTERS_LENGTH,
)
from ..core.exceptions import TrendMicroApexCentralValidationError

SUPPORTED_ENTITIES = [EntityTypes.URL, EntityTypes.ADDRESS, EntityTypes.FILEHASH]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        f"{INTEGRATION_IDENTIFIER} - {CREATE_ENTITY_UDSO_SCRIPT_NAME}"
    )
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    application_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Application ID",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Key",
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Action parameters
    scan_action = extract_action_param(
        siemplify,
        param_name="Action",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_SCAN_ACTION,
    )
    note = extract_action_param(
        siemplify, param_name="Note", is_mandatory=False, print_value=False
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = False
    output_message = ""

    entities_already_exist = []
    failed_entities = []
    successful_entities = []
    json_results = {}

    try:
        manager = TrendMicroApexCentralManager(
            api_root=api_root,
            application_id=application_id,
            api_key=api_key,
            verify_ssl=verify_ssl,
        )
        if note and len(note) > MAX_UDSO_NOTES_CHARACTERS_LENGTH:
            raise TrendMicroApexCentralValidationError(
                f"note can’t contain more than {MAX_UDSO_NOTES_CHARACTERS_LENGTH} characters"
            )

        expiration_in_days = extract_action_param(
            siemplify,
            param_name="Expire In (Days)",
            is_mandatory=False,
            print_value=False,
            input_type=int,
            default_value=None,
        )
        if expiration_in_days is not None and expiration_in_days <= 0:
            raise TrendMicroApexCentralValidationError(
                "Expiration range of UDSO must be a positive number"
            )

        expiration_date = (
            (utc_now() + datetime.timedelta(days=expiration_in_days)).isoformat()
            if expiration_in_days
            else None
        )
        already_existing_udso_entities = [
            udso.content.lower() for udso in manager.list_udso_entries()
        ]

        for entity in siemplify.target_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            add_udso = False
            entity.identifier = entity.identifier.strip()
            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type. Skipping.."
                )
                continue

            if entity.entity_type == EntityTypes.FILEHASH:
                if entity.identifier.lower() not in already_existing_udso_entities:
                    if len(entity.identifier) != SHA1_HASH_LENGTH:
                        siemplify.LOGGER.info(
                            f"File hash of {entity.identifier} is of unsupported hash type. Only SHA-1 hashes are supported. "
                            f"Skipping.."
                        )
                        continue
                    add_udso = True
                else:
                    entities_already_exist.append(entity.identifier)

            if entity.entity_type == EntityTypes.ADDRESS:
                if entity.identifier.lower() not in already_existing_udso_entities:
                    if validators.ipv4(
                        entity.identifier
                    ):  # endpoint supports only valid ipv4 addresses
                        add_udso = True
                else:
                    entities_already_exist.append(entity.identifier)

            if entity.entity_type == EntityTypes.URL:
                if entity.identifier.lower() not in already_existing_udso_entities:
                    if validators.url(
                        entity.identifier
                    ):  # the endpoint only supports valid URLs
                        # lowercase schema
                        try:
                            parsed_url = urlparse(entity.identifier)
                            entity.identifier = parsed_url.geturl().replace(
                                parsed_url.scheme, parsed_url.scheme.lower()
                            )
                        except Exception:
                            siemplify.LOGGER.info(
                                f"Failed to lowercase schema of {entity.identifier}"
                            )
                        add_udso = True
                else:
                    entities_already_exist.append(entity.identifier)

            if add_udso:
                try:
                    manager.add_udso_to_list(
                        entity_type=ENTITY_TYPE_TO_UDSO_TYPE[entity.entity_type],
                        entity_value=entity.identifier,
                        expiration_utc_date=expiration_date,
                        scan_option=scan_action,
                        notes=note,
                    )
                    successful_entities.append(entity.identifier.lower())
                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity.identifier}"
                    )
                except Exception as error:
                    failed_entities.append(entity.identifier)
                    siemplify.LOGGER.error(f"Failed to add UDSO of {entity.identifier}")
                    siemplify.LOGGER.exception(error)

        if entities_already_exist:
            output_message = "The following UDSO already exist in {}:\n  {}\n\n".format(
                INTEGRATION_DISPLAY_NAME, "\n  ".join(entities_already_exist)
            )

        if successful_entities:
            try:  # Retrieve json results for successfully added entities
                siemplify.LOGGER.info(
                    f"Retrieving list of UDSO entries to fetch JSON results of added entities"
                )
                listed_udso_entries = manager.list_udso_entries()
                for udso in listed_udso_entries:
                    if udso.content.lower() in successful_entities:
                        json_results[udso.content] = udso.to_json()
                if json_results:
                    siemplify.result.add_result_json(
                        convert_dict_to_json_result_dict(json_results)
                    )
            except Exception as error:
                siemplify.LOGGER.error(
                    f"Failed to list UDSO entities in order to retrieve json results for added entities"
                )
                siemplify.LOGGER.exception(error)

            output_message += "Successfully created UDSO based on the following entities in {}:\n  {}\n\n".format(
                INTEGRATION_DISPLAY_NAME, "\n  ".join(successful_entities)
            )
            result_value = True

            if failed_entities:
                output_message += "Action wasn't able to create UDSO based on the following entities in {}:\n  {}\n\n".format(
                    INTEGRATION_DISPLAY_NAME, "\n  ".join(failed_entities)
                )
        else:
            output_message += f"No UDSO were created in {INTEGRATION_DISPLAY_NAME}."

    except Exception as error:
        output_message = f'Error executing action "{CREATE_ENTITY_UDSO_SCRIPT_NAME}". Reason: {error}.'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
