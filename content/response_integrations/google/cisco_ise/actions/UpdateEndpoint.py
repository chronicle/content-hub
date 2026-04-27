from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CiscoISEManager import CiscoISEManager
from soar_sdk.SiemplifyDataModel import EntityTypes
import json
from TIPCommon import extract_configuration_param, extract_action_param


INTEGRATION_NAME = "CiscoISE"


def convert_string_to_bool(value):
    """
    Convert bool string to bool value -> The user has t add a value to update that has to be passed as bool.
    :param value: {string}
    :return: {bool}
    """
    if value:
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            # Validate false input too.
            return False
        else:
            raise Exception(
                f'Parameter value has to be "True" or "False" string, added "{value}"'
            )


@output_handler
def main():
    # Configuration.
    siemplify = SiemplifyAction()
    siemplify.script_name = "CiscoISE_UpdateEndpoint"
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    cim = CiscoISEManager(api_root, username, password, verify_ssl)

    # Variables.
    result_value = False
    updated_addresses = []
    errors = []
    errors_flag = False

    # Parameters.
    description = extract_action_param(
        siemplify, param_name="Description", print_value=True
    )
    group_id = extract_action_param(siemplify, param_name="Group ID", print_value=True)
    portal_user = extract_action_param(
        siemplify, param_name="Portal User", print_value=True
    )
    identity_store = extract_action_param(
        siemplify, param_name="Identity Store", print_value=True
    )
    identity_store_id = extract_action_param(
        siemplify, param_name="Identity Store ID", print_value=True
    )

    try:
        # Cistom attributes must be a dict.
        custom_attributes = extract_action_param(
            siemplify, param_name="Custom Attributes", print_value=True
        )
        if custom_attributes:
            custom_attributes = json.loads(custom_attributes)
    except Exception as err:
        siemplify.LOGGER.error(
            f"Error fetching custom attributes, input not in corrent format(Must be dict), ERROR: {err}"
        )
        siemplify.LOGGER.exception(err)
        raise Exception(
            f"Error fetching custom attributes, input not in corrent format(Must be dict), ERROR: {err}"
        )

    mdm_server_name = extract_action_param(
        siemplify, param_name="MDM Server Name", print_value=True
    )
    mdm_os = extract_action_param(siemplify, param_name="MDM OS", print_value=True)
    mdm_manufacturer = extract_action_param(
        siemplify, param_name="MDM Manufacturer", print_value=True
    )
    mdm_model = extract_action_param(
        siemplify, param_name="MDM Model", print_value=True
    )
    mdm_imei = extract_action_param(siemplify, param_name="MDM IMEI", print_value=True)
    mdm_phone_number = extract_action_param(
        siemplify, param_name="MDM Phone Number", print_value=True
    )

    # Bool Params.
    mdm_encrypted = extract_action_param(
        siemplify, param_name="MDM Encrypted", print_value=True, input_type=bool
    )
    mdm_pinlock = extract_action_param(
        siemplify, param_name="MDM Pinlock", print_value=True, input_type=bool
    )
    mdm_jail_broken = extract_action_param(
        siemplify, param_name="MDM Jail Broken", print_value=True, input_type=bool
    )
    mdm_reachable = extract_action_param(
        siemplify, param_name="MDM Reachable", print_value=True, input_type=bool
    )
    mdm_enrolled = extract_action_param(
        siemplify, param_name="MDM Enrolled", print_value=True, input_type=bool
    )
    mdm_compliance_status = extract_action_param(
        siemplify, param_name="MDM Compliance Status", print_value=True, input_type=bool
    )

    ip_addresses_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.ADDRESS
    ]

    for entity in ip_addresses_entities:
        # Fetch MAC address
        try:
            mac_address = cim.get_endpoint_mac_by_ip(entity.identifier)
            cim.update_endpoint(
                mac_address,
                description=description,
                group_id=group_id,
                portal_user=portal_user,
                identity_store=identity_store,
                identity_store_id=identity_store_id,
                custom_attributes=custom_attributes,
                mdm_server_name=mdm_server_name,
                mdm_reachable=mdm_reachable,
                mdm_enrolled=mdm_enrolled,
                mdm_compliance_status=mdm_compliance_status,
                mdm_os=mdm_os,
                mdm_manufacturer=mdm_manufacturer,
                mdm_model=mdm_model,
                mdm_encrypted=mdm_encrypted,
                mdm_pinlock=mdm_pinlock,
                mdm_jail_broken=mdm_jail_broken,
                mdm_imei=mdm_imei,
                mdm_phone_number=mdm_phone_number,
            )
            updated_addresses.append(entity.identifier)
        except Exception as err:
            siemplify.LOGGER.error(
                f'Error updating "{entity.identifier}", ERROR: {err}'
            )
            errors.append(f'Error updating "{entity.identifier}", ERROR: {err}')
            errors_flag = True
            siemplify.LOGGER.exception(err)

    if updated_addresses:
        output_message = (
            f"Following endpoints were updated: {','.join(updated_addresses)}"
        )
        result_value = True
    else:
        output_message = "No endpoints were updated."

    if errors_flag:
        output_message = "{0} \n \n ERRORS:{1}".format(
            output_message, " \n ".join(errors)
        )

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
