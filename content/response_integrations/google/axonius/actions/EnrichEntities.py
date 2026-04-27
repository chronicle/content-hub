from __future__ import annotations
from typing import List

import requests
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from ..core.AxoniusManager import AxoniusManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes, InsightType, InsightSeverity
from soar_sdk.SiemplifyUtils import (
    output_handler,
    unix_now,
    convert_unixtime_to_datetime,
    convert_dict_to_json_result_dict,
)
from ..core.consts import (
    INTEGRATION_IDENTIFIER,
    ENRICH_ENTITIES_SCRIPT_NAME,
    DEFAULT_MAX_NOTES_TO_RETURN,
    MIN_NOTES_TO_RETURN,
)
from ..core.exceptions import (
    AxoniusValidationError,
    AxoniusAuthorizationError,
    AxoniusForbiddenError,
)
from ..core.utils import get_username_entity_data, is_valid_email

# Fix misalignment of MAC entity type
EntityTypes.MACADDRESS = EntityTypes.MACADDRESS.upper()
SUPPORTED_ENTITIES = [
    EntityTypes.HOSTNAME,
    EntityTypes.ADDRESS,
    EntityTypes.MACADDRESS,
    EntityTypes.USER,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {ENRICH_ENTITIES_SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Key",
        is_mandatory=True,
        print_value=True,
    )
    secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Secret",
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        default_value=True,
        print_value=True,
    )
    # Action parameters
    create_endpoint_insight = extract_action_param(
        siemplify,
        param_name="Create Endpoint Insight",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
        default_value=True,
    )
    create_user_insight = extract_action_param(
        siemplify,
        param_name="Create User Insight",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
        default_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    output_message = ""

    devices = {
        "ip_addresses": {},  # maps entity.identifier -> entity
        "hostnames": {},
        "mac_addresses": {},
    }
    users = {"usernames": {}, "emails": {}}  # maps entity.identifier -> entity

    found_entities_to_process = {  # matches found device with axonius id and correlated siemplify entity
        # device identifier -> {
        #     "axon_id" : device axon id
        #     "siemplify_entity" : entity
        # }
    }

    already_processed_axon_ids = []
    successful_entities = []
    failed_entities = []

    endpoints_insights: List[str] = []
    users_insights: List[str] = []
    json_results = {}

    try:
        manager = AxoniusManager(
            api_root=api_root,
            api_key=api_key,
            secret_key=secret_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        max_notes_to_return = extract_action_param(
            siemplify,
            param_name="Max Notes To Return",
            input_type=int,
            is_mandatory=False,
            print_value=True,
            default_value=DEFAULT_MAX_NOTES_TO_RETURN,
        )
        if max_notes_to_return < MIN_NOTES_TO_RETURN:
            raise AxoniusValidationError(
                f'"Max Note To Return" parameter must be greater than {MIN_NOTES_TO_RETURN}'
            )

        for entity in siemplify.target_entities:
            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type. Skipping."
                )
                continue
            entity.identifier = entity.identifier.strip()
            entity_identifier_casefold = entity.identifier.casefold()
            if entity.entity_type == EntityTypes.USER:
                if is_valid_email(entity_identifier_casefold):
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} will be enriched as email"
                    )
                    users["emails"][entity_identifier_casefold] = entity
                else:
                    users["usernames"][entity_identifier_casefold] = entity
            elif entity.entity_type == EntityTypes.ADDRESS:
                devices["ip_addresses"][entity_identifier_casefold] = entity
            elif entity.entity_type == EntityTypes.HOSTNAME:
                devices["hostnames"][entity_identifier_casefold] = entity
            elif entity.entity_type == EntityTypes.MACADDRESS:
                devices["mac_addresses"][entity_identifier_casefold] = entity

        # process users
        if any(users.values()):
            user_entities_identifiers = list(users["usernames"].keys())
            email_entities_identifiers = list(users["emails"].keys())
            try:
                # search for axonius users
                found_users = manager.get_users(
                    emails=email_entities_identifiers,
                    usernames=user_entities_identifiers,
                )
                siemplify.LOGGER.info(
                    f"Found {len(found_users)} users in {INTEGRATION_IDENTIFIER}"
                )

                # find missing users, match axonius ids in the response to entity identifiers
                for user in found_users:
                    # axonius user's display name correlates to siemplify user entity
                    found_display_name = get_username_entity_data(
                        get_users_object=user,
                        attribute="display_names",
                        user_entity_dict=users,
                        key="usernames",
                    )
                    if found_display_name:
                        found_entities_to_process[found_display_name] = {
                            "axon_id": user.internal_axon_id,
                            "siemplify_entity": users["usernames"].pop(
                                found_display_name, None
                            ),
                        }

                    found_email = get_username_entity_data(
                        get_users_object=user,
                        attribute="emails",
                        user_entity_dict=users,
                        key="emails",
                    )
                    # axonius user's email or username correlates to siemplify email entity
                    if found_email:
                        found_entities_to_process[found_email] = {
                            "axon_id": user.internal_axon_id,
                            "siemplify_entity": users["emails"].pop(found_email, None),
                        }

                    found_email_username = get_username_entity_data(
                        get_users_object=user,
                        attribute="usernames",
                        user_entity_dict=users,
                        key="emails",
                    )
                    if found_email_username:
                        found_entities_to_process[found_email_username] = {
                            "axon_id": user.internal_axon_id,
                            "siemplify_entity": users["emails"].pop(
                                found_email_username, None
                            ),
                        }

                    found_username = get_username_entity_data(
                        get_users_object=user,
                        attribute="usernames",
                        user_entity_dict=users,
                        key="usernames",
                    )
                    if found_username:
                        found_entities_to_process[found_username] = {
                            "axon_id": user.internal_axon_id,
                            "siemplify_entity": users["usernames"].pop(
                                found_username, None
                            ),
                        }
                # mark missing entities as failed
                failed_entities.extend(
                    list(users["usernames"].keys()) + list(users["emails"].keys())
                )

                for (
                    entity_identifier,
                    entity_with_axon_id_payload,
                ) in found_entities_to_process.items():
                    if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                        siemplify.LOGGER.error(
                            f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                        )
                        status = EXECUTION_STATE_TIMEDOUT
                        break
                    axon_id = entity_with_axon_id_payload.get("axon_id")
                    entity = entity_with_axon_id_payload.get("siemplify_entity")
                    if (not axon_id) or (not entity):
                        siemplify.LOGGER.info(
                            f"Axonius ID or siemplify entity were not found"
                        )
                        continue
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching details of entity {entity.identifier} with axon id {axon_id}"
                        )
                        user_details = manager.get_user_details(
                            internal_axonius_id=axon_id
                        )
                        if user_details:
                            json_results[entity.identifier] = user_details.as_json(
                                max_notes_to_return=max_notes_to_return
                            )
                            siemplify.result.add_entity_link(
                                f"{entity.identifier}",
                                user_details.case_wall_report_link,
                            )
                            entity.additional_properties.update(
                                user_details.as_enrichment()
                            )
                            entity.is_enriched = True
                            # If same user is processed by different provided entities, insights and csv tables will not be duplicated
                            # with the same data
                            if axon_id not in already_processed_axon_ids:
                                already_processed_axon_ids.append(axon_id)
                                siemplify.result.add_entity_table(
                                    f"{entity.identifier}",
                                    construct_csv(
                                        user_details.as_enrichment_csv_table()
                                    ),
                                )
                                if max_notes_to_return:
                                    siemplify.result.add_data_table(
                                        f"{entity.identifier}: Notes",
                                        construct_csv(
                                            user_details.get_notes_as_csv()[
                                                -max_notes_to_return:
                                            ]
                                        ),
                                    )
                                if create_user_insight:
                                    users_insights.append(
                                        user_details.as_insight(entity.identifier)
                                    )
                            else:
                                already_processed_axon_ids.append(axon_id)
                            successful_entities.append(entity)
                        else:
                            failed_entities.append(entity.identifier)
                            siemplify.LOGGER.error(f"Failed to find user details")

                    except Exception as error:
                        failed_entities.append(entity.identifier)
                        siemplify.LOGGER.error(
                            f"Failed to enrich entity {entity.identifier}"
                        )
                        siemplify.LOGGER.exception(error)

            except (
                requests.exceptions.ConnectionError,
                AxoniusAuthorizationError,
                AxoniusForbiddenError,
            ):
                raise
            except Exception as error:
                failed_entities.extend(
                    user_entities_identifiers + email_entities_identifiers
                )
                siemplify.LOGGER.error(f"Failed to find users for provided entities")
                siemplify.LOGGER.exception(error)
        else:
            siemplify.LOGGER.info("No users will be enriched")

        # process devices
        if any(devices.values()):
            found_entities_to_process = {}
            ips_entities_identifiers = list(devices["ip_addresses"].keys())
            mac_entities_identifiers = list(devices["mac_addresses"].keys())
            hostname_entities_identifiers = list(devices["hostnames"].keys())
            try:
                # search for axonius devices
                found_devices = manager.get_devices(
                    ip_addresses=ips_entities_identifiers,
                    mac_addresses=mac_entities_identifiers,
                    hostnames=hostname_entities_identifiers,
                )
                siemplify.LOGGER.info(
                    f"Found {len(found_devices)} devices in {INTEGRATION_IDENTIFIER}"
                )

                # find missing devices, match axonius ids in the response to entity identifiers
                for device in found_devices:
                    for ip in device.ips:
                        if ip in devices["ip_addresses"]:
                            found_entities_to_process[ip] = {
                                "axon_id": device.internal_axon_id,
                                "siemplify_entity": devices["ip_addresses"].pop(
                                    ip, None
                                ),
                            }

                    for mac in device.macs:
                        if (
                            isinstance(mac, str)
                            and mac.casefold() in devices["mac_addresses"]
                        ):
                            found_entities_to_process[mac] = {
                                "axon_id": device.internal_axon_id,
                                "siemplify_entity": devices["mac_addresses"].pop(
                                    mac.casefold(), None
                                ),
                            }

                    # axonius device's hostname and name correlates with siemplify hostname entity
                    if (
                        isinstance(device.hostname, str)
                        and device.hostname.casefold() in devices["hostnames"]
                    ):
                        found_entities_to_process[device.hostname] = {
                            "axon_id": device.internal_axon_id,
                            "siemplify_entity": devices["hostnames"].pop(
                                device.hostname.casefold(), None
                            ),
                        }

                    if (
                        isinstance(device.name, str)
                        and device.name.casefold() in devices["hostnames"]
                    ):
                        found_entities_to_process[device.name] = {
                            "axon_id": device.internal_axon_id,
                            "siemplify_entity": devices["hostnames"].pop(
                                device.name.casefold(), None
                            ),
                        }

                # mark missing entities as failed
                failed_entities.extend(
                    list(devices["ip_addresses"].keys())
                    + list(devices["mac_addresses"].keys())
                    + list(devices["hostnames"].keys())
                )

                # process each entity separately
                for (
                    entity_identifier,
                    entity_with_axon_id_payload,
                ) in found_entities_to_process.items():
                    if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                        siemplify.LOGGER.error(
                            f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                        )
                        status = EXECUTION_STATE_TIMEDOUT
                        break
                    axon_id = entity_with_axon_id_payload.get("axon_id")
                    entity = entity_with_axon_id_payload.get("siemplify_entity")
                    if (not axon_id) or (not entity):
                        siemplify.LOGGER.info(
                            f"Axonius ID or siemplify entity were not found"
                        )
                        continue
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching details of entity {entity_identifier} with axon id {axon_id}"
                        )
                        device_details = manager.get_device_details(
                            internal_axonius_id=axon_id
                        )
                        if device_details:
                            json_results[entity_identifier] = device_details.as_json(
                                max_notes_to_return=max_notes_to_return
                            )
                            siemplify.result.add_entity_link(
                                f"{entity.identifier}",
                                device_details.case_wall_report_link,
                            )
                            entity.additional_properties.update(
                                device_details.as_enrichment()
                            )
                            entity.is_enriched = True
                            # If same user is processed by different provided entities, insights and csv tables will not be duplicated
                            # with the same data
                            if axon_id not in already_processed_axon_ids:
                                already_processed_axon_ids.append(axon_id)
                                siemplify.result.add_entity_table(
                                    f"{entity.identifier}",
                                    construct_csv(
                                        device_details.as_enrichment_csv_table()
                                    ),
                                )
                                if max_notes_to_return:
                                    siemplify.result.add_data_table(
                                        f"{entity.identifier}: Notes",
                                        construct_csv(
                                            device_details.get_notes_as_csv()[
                                                -max_notes_to_return:
                                            ]
                                        ),
                                    )
                                if create_user_insight:
                                    endpoints_insights.append(
                                        str(
                                            device_details.as_insight(entity.identifier)
                                        )
                                    )
                            else:
                                already_processed_axon_ids.append(axon_id)
                            successful_entities.append(entity)
                        else:
                            failed_entities.append(entity.identifier)
                            siemplify.LOGGER.error(f"Failed to find device details")

                    except Exception as error:
                        failed_entities.append(entity.identifier)
                        siemplify.LOGGER.error(
                            f"Failed to enrich entity {entity.identifier}"
                        )
                        siemplify.LOGGER.exception(error)

            except (
                requests.exceptions.ConnectionError,
                AxoniusAuthorizationError,
                AxoniusForbiddenError,
            ):
                raise
            except Exception as error:
                failed_entities.extend(
                    ips_entities_identifiers
                    + mac_entities_identifiers
                    + hostname_entities_identifiers
                )
                siemplify.LOGGER.error(f"Failed to find devices for provided entities")
                siemplify.LOGGER.exception(error)
        else:
            siemplify.LOGGER.info("No devices will be enriched")

        if successful_entities:
            output_message += "Successfully enriched the following entities using {}:\n  {}\n\n".format(
                INTEGRATION_IDENTIFIER,
                "\n  ".join(entity.identifier for entity in successful_entities),
            )
            result_value = True
            siemplify.update_entities(successful_entities)
            if json_results:
                siemplify.result.add_result_json(
                    convert_dict_to_json_result_dict(json_results)
                )
            if create_user_insight and users_insights:
                users_insight_title = (
                    f"Enriched {'Users' if len(users_insights) > 1 else 'User'}"
                )
                siemplify.create_case_insight(
                    triggered_by=INTEGRATION_IDENTIFIER,
                    title=users_insight_title,
                    content="".join(users_insights),
                    entity_identifier="",
                    severity=InsightSeverity.INFO,
                    insight_type=InsightType.General,
                )
            if create_endpoint_insight and endpoints_insights:
                endpoints_insight_title = f"Enriched {'Endpoints' if len(endpoints_insights) > 1 else 'Endpoint'}"
                siemplify.create_case_insight(
                    triggered_by=INTEGRATION_IDENTIFIER,
                    title=endpoints_insight_title,
                    content="".join(endpoints_insights),
                    entity_identifier="",
                    severity=InsightSeverity.INFO,
                    insight_type=InsightType.General,
                )
            if failed_entities:
                output_message += "Action wasn't able to enrich the following entities using {}:\n  {}\n\n".format(
                    INTEGRATION_IDENTIFIER, "\n  ".join(failed_entities)
                )
        else:
            output_message += f"No entities were enriched."

    except Exception as error:
        output_message = (
            f'Error execution action "{ENRICH_ENTITIES_SCRIPT_NAME}". Reason: {error}'
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
