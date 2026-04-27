from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.MISPManager import MISPManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.utils import get_entity_original_identifier
from ..core.exceptions import MISPMissingParamError, MISPManagerEventIdNotFoundError
from ..core.constants import (
    INTEGRATION_NAME,
    IP_TYPE,
    SOURCE_IP,
    NETWORK_CONNECTION_TABLE_NAME,
    CREATE_NETWORK_CONNECTION_MISP_OBJECT_SCRIPT_NAME,
)

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_NETWORK_CONNECTION_MISP_OBJECT_SCRIPT_NAME

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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    # INIT ACTION PARAMETERS:
    event_id = extract_action_param(siemplify, param_name="Event ID", print_value=True)

    dst_port = extract_action_param(siemplify, param_name="Dst-port", print_value=True)
    src_port = extract_action_param(siemplify, param_name="Src-port", print_value=True)

    src_hostname = extract_action_param(
        siemplify, param_name="Hostname-src", print_value=True
    )
    dst_hostname = extract_action_param(
        siemplify, param_name="Hostname-dst", print_value=True
    )

    src_ip = extract_action_param(siemplify, param_name="IP-Src", print_value=True)
    dst_ip = extract_action_param(siemplify, param_name="IP-Dst", print_value=True)

    l3_protocol = extract_action_param(
        siemplify, param_name="Layer3-protocol", print_value=True
    )
    l4_protocol = extract_action_param(
        siemplify, param_name="Layer4-protocol", print_value=True
    )
    l7_protocol = extract_action_param(
        siemplify, param_name="Layer7-protocol", print_value=True
    )

    use_entities = extract_action_param(
        siemplify,
        param_name="Use Entities",
        input_type=bool,
        print_value=True,
        default_value=False,
    )
    ip_type = extract_action_param(
        siemplify,
        param_name="IP Type",
        print_value=True,
        default_value=IP_TYPE[SOURCE_IP],
    )
    id_type = "ID" if event_id.isdigit() else "UUID"

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    success_created_objs, success_created_objs_ids, failed_objects = [], [], []

    misp_obj_params = {
        "event_id": event_id,
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "dst_port": dst_port,
        "src_port": src_port,
        "src_hostname": src_hostname,
        "dst_hostname": dst_hostname,
        "l3_protocol": l3_protocol,
        "l4_protocol": l4_protocol,
        "l7_protocol": l7_protocol,
    }

    try:
        if not use_entities and not (dst_port or src_port or src_ip or dst_ip):
            raise MISPMissingParamError(
                "One of the: 'Dst-port', 'Src-port', 'IP-Src', 'IP-Dst' should be provided or "
                "'Use Entities' parameter set to true"
            )

        manager = MISPManager(api_root, api_token, use_ssl, ca_certificate)
        manager.get_event_by_id_or_raise(event_id)
        ip_type_key_name = "src_ip" if ip_type == IP_TYPE[SOURCE_IP] else "dst_ip"
        all_params = []

        if use_entities:
            for entity_ip in [
                get_entity_original_identifier(entity)
                for entity in siemplify.target_entities
                if entity.entity_type in SUPPORTED_ENTITY_TYPES
            ]:
                all_params.append({"event_id": event_id, ip_type_key_name: entity_ip})
        else:
            all_params.append(misp_obj_params)

        for params in all_params:
            ip_address = params[ip_type_key_name]
            try:
                misp_obj = manager.add_network_connection_object(**params)
                success_created_objs.append(misp_obj)
                success_created_objs_ids.append(ip_address)
            except Exception as e:
                siemplify.LOGGER.error(e)
                siemplify.LOGGER.exception(e)
                failed_objects.append((ip_address, str(e)))

        if success_created_objs:
            siemplify.result.add_result_json(
                [misp_obj.to_json() for misp_obj in success_created_objs]
            )
            all_attributes = []
            for misp_obj in success_created_objs:
                all_attributes.extend(misp_obj.attributes)

            siemplify.result.add_data_table(
                NETWORK_CONNECTION_TABLE_NAME.format(event_id),
                construct_csv(
                    [attribute.to_base_csv() for attribute in all_attributes]
                ),
            )
        if use_entities:
            if success_created_objs:
                output_message = (
                    "Successfully created new network-connection objects for event with {} {} in {} "
                    "based on the following entities: \n{}\n".format(
                        id_type,
                        event_id,
                        INTEGRATION_NAME,
                        ", ".join(success_created_objs_ids),
                    )
                )

                if failed_objects:
                    output_message += (
                        "Action wasn’t able to create new network-connection objects for event with {}"
                        " {} in {} based on the following entities: \n{}".format(
                            id_type,
                            event_id,
                            INTEGRATION_NAME,
                            ", ".join([failed_id for (failed_id, e) in failed_objects]),
                        )
                    )
            else:
                result_value = False
                output_message = (
                    "Action wasn’t able to create new network-connection objects for event with {} {} in"
                    " {} based on the provided entities.".format(
                        id_type, event_id, INTEGRATION_NAME
                    )
                )
        else:
            if success_created_objs:
                output_message = f"Successfully created new network-connection object for event with {id_type} {event_id} in {INTEGRATION_NAME}."
            elif failed_objects:
                result_value = False
                failed_id, reason = failed_objects[0]
                output_message = (
                    "Action wasn’t able to created new network-connection object for event with {} {} "
                    "in {}. Reason: {}".format(
                        id_type, event_id, INTEGRATION_NAME, reason
                    )
                )

    except Exception as e:
        output_message = f"Error executing action '{CREATE_NETWORK_CONNECTION_MISP_OBJECT_SCRIPT_NAME}'. Reason: "
        output_message += (
            f"Event with {id_type} {event_id} was not found in {INTEGRATION_NAME}"
            if isinstance(e, MISPManagerEventIdNotFoundError)
            else str(e)
        )
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
