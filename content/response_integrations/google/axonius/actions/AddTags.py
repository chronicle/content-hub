from __future__ import annotations
import requests
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.AxoniusManager import AxoniusManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_IDENTIFIER, ADD_TAGS_SCRIPT_NAME
from ..core.exceptions import AxoniusAuthorizationError, AxoniusForbiddenError
from ..core.utils import get_username_entity_data, is_valid_email, load_csv_to_list

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
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {ADD_TAGS_SCRIPT_NAME}"
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
    tags = extract_action_param(
        siemplify, param_name="Tags", is_mandatory=True, print_value=True
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

    found_entities_to_process = {}  # maps entity.identifier -> axonius id

    successful_entities = []
    failed_entities = []

    try:
        manager = AxoniusManager(
            api_root=api_root,
            api_key=api_key,
            secret_key=secret_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        tags = load_csv_to_list(tags, "Tags")
        for entity in siemplify.target_entities:
            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type. Skipping."
                )
                continue
            entity.identifier = entity.identifier.strip()
            entity_identifier_casefold = entity.identifier.casefold()
            if entity.entity_type == EntityTypes.USER:
                if is_valid_email(entity.identifier):
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} will be used as email"
                    )
                    users["emails"][entity_identifier_casefold] = entity
                else:
                    users["usernames"][entity_identifier_casefold] = entity
            elif entity.entity_type == EntityTypes.ADDRESS:
                devices["ip_addresses"][entity.identifier] = entity
            elif entity.entity_type == EntityTypes.HOSTNAME:
                devices["hostnames"][entity_identifier_casefold] = entity
            elif entity.entity_type == EntityTypes.MACADDRESS:
                devices["mac_addresses"][entity.identifier] = entity

        # add tags to users
        if any(users.values()):
            user_entities_identifiers = list(users["usernames"].keys())
            email_entities_identifiers = list(users["emails"].keys())
            try:
                found_users = manager.get_users(
                    emails=email_entities_identifiers,
                    usernames=user_entities_identifiers,
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
                        found_entities_to_process[found_display_name] = (
                            user.internal_axon_id
                        )
                        users["usernames"].pop(found_display_name, None)

                    found_email = get_username_entity_data(
                        get_users_object=user,
                        attribute="emails",
                        user_entity_dict=users,
                        key="emails",
                    )
                    # axonius user's email or username correlates to siemplify email entity
                    if found_email:
                        found_entities_to_process[found_email] = user.internal_axon_id
                        users["emails"].pop(found_email, None)

                    found_email_username = get_username_entity_data(
                        get_users_object=user,
                        attribute="usernames",
                        user_entity_dict=users,
                        key="emails",
                    )
                    if found_email_username:
                        found_entities_to_process[found_email_username] = (
                            user.internal_axon_id
                        )
                        users["emails"].pop(found_email_username, None)

                    found_username = get_username_entity_data(
                        get_users_object=user,
                        attribute="usernames",
                        user_entity_dict=users,
                        key="usernames",
                    )
                    if found_username:
                        found_entities_to_process[found_username] = (
                            user.internal_axon_id
                        )
                        users["usernames"].pop(found_username, None)

                # mark missing entities as failed
                failed_entities.extend(
                    list(users["usernames"].keys()) + list(users["emails"].keys())
                )
                try:
                    # add tags to found users
                    if found_entities_to_process.keys():
                        siemplify.LOGGER.info(
                            f"Adding tags to entities {', '.join(found_entities_to_process.keys())}"
                        )
                        manager.add_tags_to_users(
                            internal_axonius_ids=list(
                                set(found_entities_to_process.values())
                            ),
                            tags=tags,
                        )
                        siemplify.LOGGER.info(f"Successfully added tags to users")
                        successful_entities.extend(
                            list(found_entities_to_process.keys())
                        )
                    else:
                        siemplify.LOGGER.info(
                            f"No users were found in {INTEGRATION_IDENTIFIER}"
                        )
                except Exception as error:
                    failed_entities.extend(list(found_entities_to_process.keys()))
                    siemplify.LOGGER.error(
                        f"Failed to add tags to entities: {', '.join(found_entities_to_process.keys())}"
                    )
                    siemplify.LOGGER.exception(error)

            except (
                requests.exceptions.ConnectionError,
                AxoniusAuthorizationError,
                AxoniusForbiddenError,
            ):
                raise
            except Exception as error:
                failed_entities.extend(list(found_entities_to_process.keys()))
                siemplify.LOGGER.error(f"Failed to find users for provided entities")
                siemplify.LOGGER.exception(error)
        else:
            siemplify.LOGGER.info("No tags will be added to users")

        # add tags to devices
        if any(devices.values()):
            found_entities_to_process = {}
            ips_entities_identifiers = list(devices["ip_addresses"].keys())
            mac_entities_identifiers = list(devices["mac_addresses"].keys())
            hostname_entities_identifiers = list(devices["hostnames"].keys())
            try:
                found_devices = manager.get_devices(
                    ip_addresses=ips_entities_identifiers,
                    mac_addresses=mac_entities_identifiers,
                    hostnames=hostname_entities_identifiers,
                )

                # find missing devices, match axonius ids in the response to entity identifiers
                for device in found_devices:
                    for ip in device.ips:
                        if ip in devices["ip_addresses"]:
                            found_entities_to_process[ip] = device.internal_axon_id
                            devices["ip_addresses"].pop(ip, None)
                    for mac in device.macs:
                        if mac in devices["mac_addresses"]:
                            found_entities_to_process[mac] = device.internal_axon_id
                            devices["mac_addresses"].pop(mac, None)
                    # axonius device's hostname and name correlates with siemplify hostname entity
                    if (
                        isinstance(device.hostname, str)
                        and device.hostname.casefold() in devices["hostnames"]
                    ):
                        found_entities_to_process[device.hostname] = (
                            device.internal_axon_id
                        )
                        devices["hostnames"].pop(device.hostname.casefold(), None)
                    if (
                        isinstance(device.name, str)
                        and device.name.casefold() in devices["hostnames"]
                    ):
                        found_entities_to_process[device.name] = device.internal_axon_id
                        devices["hostnames"].pop(device.name.casefold(), None)

                # mark missing entities as failed
                failed_entities.extend(
                    list(devices["ip_addresses"].keys())
                    + list(devices["mac_addresses"].keys())
                    + list(devices["hostnames"].keys())
                )
                try:
                    # add tags to found devices
                    if found_entities_to_process.keys():
                        siemplify.LOGGER.info(
                            f"Adding tags to entities {', '.join(found_entities_to_process.keys())}"
                        )
                        manager.add_tags_to_devices(
                            internal_axonius_ids=list(
                                set(found_entities_to_process.values())
                            ),
                            tags=tags,
                        )
                        siemplify.LOGGER.info(f"Successfully added tags to devices")
                        successful_entities.extend(
                            list(found_entities_to_process.keys())
                        )
                    else:
                        siemplify.LOGGER.info(
                            f"No devices were found in {INTEGRATION_IDENTIFIER}"
                        )
                except Exception as error:
                    failed_entities.extend(list(found_entities_to_process.keys()))
                    siemplify.LOGGER.error(
                        f"Failed to add tags to entities: {', '.join(found_entities_to_process.keys())}"
                    )
                    siemplify.LOGGER.exception(error)

            except (
                requests.exceptions.ConnectionError,
                AxoniusAuthorizationError,
                AxoniusForbiddenError,
            ):
                raise
            except Exception as error:
                failed_entities.extend(list(found_entities_to_process.keys()))
                siemplify.LOGGER.error(f"Failed to find devices for provided entities")
                siemplify.LOGGER.exception(error)
        else:
            siemplify.LOGGER.info("No tags will be added to devices")

        if successful_entities:
            output_message += "Successfully added tags to the following entities in {}:\n  {}\n\n".format(
                INTEGRATION_IDENTIFIER, "\n  ".join(successful_entities)
            )
            result_value = True
            if failed_entities:
                output_message += "Action wasn't able to add tags to the following entities in {}:\n  {}\n\n".format(
                    INTEGRATION_IDENTIFIER, "\n  ".join(failed_entities)
                )
        else:
            output_message += f"Tags weren't added to the provided entities."

    except Exception as error:
        output_message = (
            f'Error execution action "{ADD_TAGS_SCRIPT_NAME}". Reason: {error}'
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
